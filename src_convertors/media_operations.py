import re
import copy
import math
import os
import subprocess
import sys


class MediaCutter:
    """
    Contains methods for cutting the source media files into smaller
    pieces using ffmpeg and naming the pieces in a consistent way.
    The idea is that each media file is cut into overlapping segments,
    the length of the segment is specified in the settings. If the length
    of the segment is L, the media file is first split into segments of
    the length L with zero offset, the with an offset L/3 then with an
    offset 2L/3. Therefore, almost each timepoint gets into three overlapping
    chunks, which provides the possibility of choosing the best chunk for
    each sentence, i.e. the chunk where the relevant segment occupies
    the most central position.
    """

    rxFname = re.compile('^(.*?)([^/\\\\]*)\\.([^/\\\\.]*)$')

    def __init__(self, settings):
        self.settings = copy.deepcopy(settings)
        self.privacySegments = []    # segments (start_ms, end_ms) that should be beeped out

    def get_media_name(self, fname, ts1, ts2, minTime=None, maxTime=None):
        """
        Choose the appropriate fragment of the source
        video file and return its name and the new offsets.
        The name has the following structure:
        base_name-offset-number_of_chunk_for_this_offset.
        Offset of 0 means no offset, 1 means L/3, 2 means 2*L/3.
        The middle of the (minTime; maxTime) intevral should be as
        close to the middle of the selected fragment as possible.
        If no minTime and maxTime are supplied, they are considered
        equal to ts1 and ts2, respectively.
        """
        if minTime is None:
            minTime = ts1
        if maxTime is None:
            maxTime = ts2
        middle = float(minTime) + float(maxTime - minTime) / 2
        fileLen = float(self.settings['media_length'])
        segmentLen = fileLen / 3
        if middle <= fileLen / 2:
            frameNumber = 0
        else:
            frameNumber = (middle - fileLen / 2) // segmentLen
            relativeOffset = (middle - fileLen / 2) % segmentLen
            if relativeOffset > fileLen / 6:
                # The middle of the segment is closer to the middle of the next available frame
                frameNumber += 1

        filenameOffset = math.floor(frameNumber % 3)
        filenameNumber = math.floor(frameNumber // 3)
        m = re.search('^(.*)\\.([^.]+)$', fname)
        if m is None:
            fname = fname + '-' + str(filenameOffset) + '-' + str(filenameNumber)
        else:
            fname = m.group(1) + '-' + str(filenameOffset) + '-' + \
                    str(filenameNumber) + '.mp4'    # + m.group(2)
        ts1 -= frameNumber * segmentLen
        ts2 -= frameNumber * segmentLen
        return ts1, ts2, fname

    def split_file(self, fname, outDir, splitLength, startOffset=0, segmentLen=0,
                   usedFilenames=None):
        """
        Split the file into chunks of given length, starting from the
        given offset (actual offset in seconds equals startOffset * segmentLen).
        This function calls ffmpeg with relevant parameters.
        If usedFilenames list is set, skip fragments that do not appear on it.
        """
        durationProbe = 'ffprobe -v error -show_entries format=duration ' \
                        '-of default=noprint_wrappers=1:nokey=1 "' + fname + '"'
        output = subprocess.Popen(durationProbe,
                                  shell=True,
                                  stdout=subprocess.PIPE
                                  ).stdout.read().decode(sys.stdin.encoding)
        try:
            mediaLength = float(output)
            print('Media length in seconds: ' + str(mediaLength))
        except:
            print('Cannot determine media length.')
            return

        splitCount = int(math.ceil((mediaLength - startOffset) / float(splitLength)))
        if splitCount == 1:
            print('Media length is less then the target split length.')
            # return

        splitCmd = 'ffmpeg -y'  # + "' -vcodec copy "
        for n in range(0, splitCount):
            # " -vf scale=500:-1 -acodec copy -strict experimental " +
            splitStr = ''
            splitStart = startOffset + splitLength * n
            splitStr += ' -ss ' + str(splitStart) + ' -i "' + fname + '"' + \
                        ' -t ' + str(splitLength)
            curPrivacySegments = []
            for seg in self.privacySegments:
                if seg[0] / 1000 >= splitStart + splitLength:
                    break
                if seg[1] / 1000 <= splitStart:
                    continue
                segStart = max(splitStart, seg[0] / 1000) - splitStart
                segEnd = min(splitStart + splitLength, seg[1] / 1000) - splitStart
                seg = (str(segStart), str(segEnd),
                       str(segEnd - segStart), str(len(curPrivacySegments) + 1))
                curPrivacySegments.append(seg)
            beepOut = '; '.join('[out' + str(int(seg[3]) - 1) + ']volume=0:enable=\'between(t,' + seg[0] + ',' + seg[1] + ')\'[main' + seg[3] + '];'
                                'sine=d=' + seg[2] + ':f=880[sine' + seg[2] + '];[sine' + seg[2] + ']adelay=' + str(float(seg[0]) * 1000) + '[beep' + seg[3] + '];'
                                '[main' + seg[3] + '][beep' + seg[3] + ']amix=inputs=2[out' + seg[3] + ']'
                                for seg in curPrivacySegments)
            if len(beepOut) > 0:
                beepOut = ' -filter_complex "[1]' + re.sub('\\[out[0-9]+\\]$', '', beepOut[6:]) + '" '
            if fname.lower().endswith('.mp4'):
                splitStr += ' -c:v libx264 -b:v 700k -c:a aac -b:a 192k -ac 2' + beepOut
                newExt = '.mp4'
            elif fname.lower().endswith(('.avi', '.mts', '.mov', '.mp4')):
                splitStr += ' -s 400x300 -c:v libx264 -b:v 500k -c:a aac -b:a 192k -ac 2' + beepOut
                newExt = '.mp4'
            elif fname.lower().endswith(('.wav', '.wma', '.mp3')):
                # splitStr += " -ab 196k"
                # newExt = '.mp3'
                splitStr = ' -loop 1 -i ' + os.path.abspath('img/sound.png') +\
                           ' -ss ' + str(splitStart) + \
                           ' -i "' + fname + '" -t ' + str(splitLength) +\
                           ' -vcodec libx264 -tune stillimage -acodec aac' + \
                           ' -ab 192k -ac 2 -pix_fmt yuv420p -shortest ' + beepOut
                newExt = '.mp4'
            else:
                print('Unknown file type: ' + fname)
                return
            mFname = self.rxFname.search(fname)
            if mFname is None:
                print('Something wrong with the media file name:', fname)
                return
            fnameOut = mFname.group(2) + '-' + str(int(startOffset) // segmentLen) + '-' +\
                       str(n) + newExt
            if usedFilenames is not None and fnameOut not in usedFilenames:
                continue
            fnameOut = os.path.join(outDir, fnameOut)
            if os.path.exists(fnameOut):
                print(fnameOut, 'already exists, skipping.')
                continue
            splitStr += ' -strict experimental "' + fnameOut + '"'
            print('About to run: ' + splitCmd + splitStr)
            output = subprocess.Popen(splitCmd + splitStr, shell=True,
                                      stdout=subprocess.PIPE).stdout.read()

    def cut_media(self, fname, usedFilenames=None, privacySegments=None):
        """
        Cut media file into overlapping pieces whose length is specified
        in the settings. Write it to corpus/%corpus_name%/media.
        """
        if privacySegments is not None:
            self.privacySegments = privacySegments
        if 'output_media_dir' in self.settings and len(self.settings['output_media_dir']) > 0:
            outDir = os.path.abspath(self.settings['output_media_dir'])
        else:
            outDir = os.path.abspath(os.path.join(self.settings['corpus_dir'], 'media'))
        if not os.path.exists(outDir):
            os.makedirs(outDir)
        fileLen = self.settings['media_length']
        segmentLen = int(math.floor(fileLen / 3))
        for startOffset in range(3):
            self.split_file(fname, outDir, fileLen, startOffset * segmentLen, segmentLen, usedFilenames=usedFilenames)
        print(fname, 'was successfully splitted.')


if __name__ == '__main__':
    settings = {'corpus_dir': 'corpus/beserman_eaf', 'media_length': 60}
    mc = MediaCutter(settings)
    for path, dirs, files in os.walk(settings['corpus_dir']):
        for fname in files:
            if fname.lower().endswith('.mts'):
                fname = os.path.abspath(os.path.join(path, fname))
                print('Starting', fname)
                mc.cut_media(fname)

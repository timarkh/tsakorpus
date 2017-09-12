import re
import copy
import math
import os
import subprocess
import sys


class MediaCutter:
    """
    Contains methods for cutting the source files into smaller
    pieces and naming them.
    """

    rxFname = re.compile('^(.*?)([^/\\\\]*)\\.([^/\\\\.]*)$')

    def __init__(self, settings):
        self.settings = copy.deepcopy(settings)

    def get_media_name(self, fname, ts1, ts2):
        """
        Choose the appropriate fragment of the source
        video file and return its name and the new offsets.
        """
        fileLen = self.settings['media_length']
        segmentLen = math.floor(fileLen / 3)
        startOffset = ts1 - 1
        if ts2 - ts1 < segmentLen:
            startOffset -= segmentLen
        if startOffset < 0:
            startOffset = 0
        else:
            startOffset = int(math.floor(startOffset / segmentLen))  # in minutes
        filenameOffset = startOffset % 3
        filenameNumber = startOffset // 3
        m = re.search('^(.*)\\.([^.]+)$', fname)
        if m is None:
            fname = fname + '-' + str(filenameOffset) + '-' + str(filenameNumber)
        else:
            fname = m.group(1) + '-' + str(filenameOffset) + '-' + \
                    str(filenameNumber) + '.mp4'    # + m.group(2)
        ts1 -= startOffset * segmentLen
        ts2 -= startOffset * segmentLen
        return ts1, ts2, fname

    def split_file(self, fname, outDir, splitLength, startOffset=0, segmentLen=0):
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
            return

        splitCmd = 'ffmpeg -y'  # + "' -vcodec copy "
        for n in range(0, splitCount):
            # " -vf scale=500:-1 -acodec copy -strict experimental " +
            splitStr = ''
            splitStart = startOffset + splitLength * n
            splitStr += ' -ss ' + str(splitStart) + ' -i "' + fname + '"' + \
                        ' -t ' + str(splitLength)
            if fname.lower().endswith('.mp4'):
                splitStr += ' -vcodec copy -acodec copy'
                newExt = '.mp4'
            elif fname.lower().endswith('.avi'):
                splitStr += ' -vcodec libx264 -b 300k -acodec aac -ab 128k'
                newExt = '.mp4'
            elif fname.lower().endswith(('.wav', '.wma', '.mp3')):
                # splitStr += " -ab 196k"
                # newExt = '.mp3'
                splitStr = ' -loop 1 -i ' + os.path.abspath('img/sound.png') +\
                           ' -ss ' + str(splitStart) + \
                           ' -i "' + fname + '" -t ' + str(splitLength) + \
                           ' -vcodec libx264 -tune stillimage -acodec aac' + \
                           ' -ab 192k -pix_fmt yuv420p -shortest '
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
            fnameOut = os.path.join(outDir, fnameOut)
            splitStr += ' -strict experimental "' + fnameOut + '"'
            print('About to run: ' + splitCmd + splitStr)
            output = subprocess.Popen(splitCmd + splitStr, shell=True,
                                      stdout=subprocess.PIPE).stdout.read()

    def cut_media(self, fname):
        """
        Cut media file into overlapping pieces whose length is specified
        in the settings. Write it to corpus/%corpus_name%/media.
        """
        outDir = os.path.abspath(os.path.join(self.settings['corpus_dir'], 'media'))
        fileLen = self.settings['media_length']
        segmentLen = int(math.floor(fileLen / 3))
        for startOffset in range(3):
            self.split_file(fname, outDir, fileLen, startOffset * segmentLen, segmentLen)
        print(fname, 'was successfully splitted.')


if __name__ == '__main__':
    settings = {'corpus_dir': 'corpus/nganasan', 'media_length': 60}
    mc = MediaCutter(settings)
    for path, dirs, files in os.walk(settings['corpus_dir']):
        for fname in files:
            if fname.lower().endswith('.wav'):
                fname = os.path.abspath(os.path.join(path, fname))
                print('Starting', fname)
                mc.cut_media(fname)

import os
import re
import html
import json
import itertools
from lxml import etree
from txt2json import Txt2JSON
from media_operations import MediaCutter


class Eaf2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    ELAN aligned files, a csv with metadata and a list with parsed
    word forms.
    """

    mediaExtensions = {'.wav', '.mp3', '.mp4', '.avi', '.mov', '.mts'}
    rxEmpty = re.compile('^[ \t]*$')
    rxLetters = re.compile('\\w+')
    rxTier = re.compile('class = "IntervalTier"[ \t\r\n]*'
                        'name = "([^\r\n"]+)" *\n(.*?)\n'
                        '(?:(?:    |\t)item| *$)',
                        flags=re.DOTALL)
    rxIntvl = re.compile('intervals \\[([0-9]+)\\]: *\n'
                         '[ \t]*xmin = ([0-9.]+) *\n'
                         '[ \t]*xmax = ([0-9.]+) *\n'
                         '[ \t]*text = "([^\r\n"]*)"',
                         flags=re.DOTALL)
    bracketPairs = {
        ']': re.compile('\\[[^ \\]]*$'),
        ')': re.compile('\\([^ \\)]*$'),
        '>': re.compile('<[^ >]*$'),
        '}': re.compile('\\{[^ \\}]*$'),
    }

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.speakerMeta = self.load_speaker_meta()
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'textgrid'
        self.participants = {}  # main tier ID -> participant ID
        self.privacySegments = {}  # segments (start_ms, end_ms) that should be beeped out, one list per source file
        self.usedMediaFiles = set()  # filenames of media fragments referenced in the JSONs

    def load_speaker_meta(self):
        speakerMeta = {}
        if 'speaker_meta_filename' not in self.corpusSettings:
            return speakerMeta
        try:
            f = open(os.path.join(self.corpusSettings['corpus_dir'], self.corpusSettings['speaker_meta_filename']),
                     'r', encoding='utf-8-sig')
            speakerMeta = json.loads(f.read())
            f.close()
        except FileNotFoundError:
            print('The speaker metadata file not found.')
        return speakerMeta

    def fragmentize_src_alignment(self, sent):
        """
        Find corresponding media file fragment and transform a JSON
        dictionaries with the information about the alignment.
        """
        if 'src_alignment' not in sent:
            return
        sent['src_alignment'].sort(key=lambda a: a['off_start_src'])
        minTime = sent['src_alignment'][0]['off_start_src']
        maxTime = sent['src_alignment'][-1]['off_end_src']
        for alignment in sent['src_alignment']:
            segStart = alignment['off_start_src']
            segEnd = alignment['off_end_src']
            ts1frag, ts2frag, srcFileFrag = self.mc.get_media_name(alignment['src'],
                                                                   segStart,
                                                                   segEnd,
                                                                   minTime=minTime,
                                                                   maxTime=maxTime)
            self.usedMediaFiles.add(srcFileFrag)
            alignment['src'] = srcFileFrag
            alignment['off_start_src'] = ts1frag
            alignment['off_end_src'] = ts2frag

    def add_src_alignment(self, sent, ts1, ts2, srcFile):
        """
        Add the alignment of the sentence with the sound/video. If
        word-level time data is available, align words, otherwise
        align the whole sentence.
        """
        sentAlignments = []
        sentAlignments.append({'off_start_src': float(ts1),
                               'off_end_src': float(ts2),
                               'true_off_start_src': float(ts1),
                               'off_start_sent': 0,
                               'off_end_sent': len(sent['text']),
                               'mtype': 'audio',
                               'src_id': ts1 + '_' + ts2,
                               'src': srcFile})
        # for alignment in sentAlignments:
        #     self.fragmentize_src_alignment(alignment)
        sent['src_alignment'] = sentAlignments

    def add_privacy_segments(self, tierTxt, srcFile):
        """
        Remember segments that should be beeped out because they
        contain sensitive data.
        """
        if srcFile not in self.privacySegments:
            self.privacySegments[srcFile] = []
        for intn, xmin, xmax, txt in self.rxIntvl.findall(tierTxt):
            self.privacySegments[srcFile].append((float(xmin), float(xmax)))

    def process_tier(self, tierID, tierTxt, srcFile):
        """
        Extract intervals from the tier text and iterate over them, returning
        them as JSON sentences.
        """
        lang = ''
        # Find out the language of the tier
        if tierID in self.corpusSettings['tier_languages']:
            lang = self.corpusSettings['tier_languages'][tierID]
        else:
            for k, v in self.corpusSettings['tier_languages'].items():
                if not k.startswith('^'):
                    k = '^' + k
                if not k.endswith('$'):
                    k += '$'
                try:
                    rxTierID = re.compile(k)
                    if rxTierID.search(tierID) is not None:
                        lang = v
                        break
                except:
                    continue
        if len(lang) <= 0 or lang not in self.corpusSettings['languages']:
            # We do not want a tier with no language association
            return
        langID = self.corpusSettings['languages'].index(lang)

        for intn, xmin, xmax, txt in self.rxIntvl.findall(tierTxt):
            if self.rxEmpty.search(txt) is not None:
                continue
            curSent = {
                'text': txt.strip(),
                'words': None,
                'lang': langID,
                'meta': {'speaker': tierID}
            }
            # Add speaker metadata
            if tierID in self.speakerMeta:
                for k, v in self.speakerMeta[tierID].items():
                    curSent['meta'][k] = v

            # Tokenize the sentence
            curSent['words'] = self.tp.tokenizer.tokenize(txt)
            self.tp.splitter.add_next_word_id_sentence(curSent)
            self.tp.parser.analyze_sentence(curSent, lang=lang)
            self.add_src_alignment(curSent, xmin, xmax, srcFile)
            yield curSent

    def get_sentences(self, txt, srcFile):
        """
        Iterate over sentences in the TextGrid file.
        """
        if 'privacy_tier' not in self.corpusSettings or len(srcFile) <= 0:
            privTierID = ''
        else:
            privTierID = self.corpusSettings['privacy_tier']

        mainTiers = []
        for tierID, tierTxt in self.rxTier.findall(txt):
            for tierRegex in self.corpusSettings['main_tiers']:
                if not tierRegex.startswith('^'):
                    tierRegex = '^' + tierRegex
                if not tierRegex.endswith('$'):
                    tierRegex += '$'
                try:
                    if re.search(tierRegex, tierID) is not None:
                        mainTiers.append((tierID, tierTxt))
                        break
                except:
                    pass
            if tierID == privTierID:
                self.add_privacy_segments(tierTxt, srcFile)
        if len(mainTiers) <= 0:
            return
        for tierID, tierTxt in mainTiers:
            for sent in self.process_tier(tierID, tierTxt, srcFile):
                yield sent

    def add_sentence_meta(self, sentences, meta):
        """
        Add some of the document-level metadata to the sentences.
        """
        for s in sentences:
            if 'meta' not in s:
                continue
            if 'year1' in meta and 'year2' in meta and meta['year1'] == meta['year2']:
                s['meta']['year'] = meta['year1']

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        self.spanAnnoTiers = {}
        self.alignedSpanAnnoTiers = {}
        self.spanAnnoTLIs = {}
        with open(fnameSrc, 'r', encoding='utf-16-be') as fIn:
            txt = fIn.read()
        srcFile = self.rxStripDir.sub('', self.rxStripExt.sub('', fnameSrc))
        textJSON['sentences'] = [s for s in self.get_sentences(txt, srcFile)]
        self.add_privacy_segments(txt, srcFile)
        # First sorting: sort sentences by language, but keep them sorted by speaker
        # (which they are now, since each speaker has a separate set of tiers in ELAN).
        textJSON['sentences'].sort(key=lambda s: (s['lang']))
        if 'sentence_segmentation' in self.corpusSettings and self.corpusSettings['sentence_segmentation']:
            self.tp.splitter.resegment_sentences(textJSON['sentences'])
        for s in textJSON['sentences']:
            self.fragmentize_src_alignment(s)
        # Final sorting: inside each language, sort sentences by their time offsets.
        textJSON['sentences'].sort(key=lambda s: (s['lang'], s['src_alignment'][0]['true_off_start_src']))
        for i in range(len(textJSON['sentences']) - 1):
            # del textJSON['sentences'][i]['src_alignment'][0]['true_off_start_src']
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
            for word in textJSON['sentences'][i]['words']:
                nTokens += 1
                if word['wtype'] == 'word':
                    nWords += 1
                if 'ana' in word and len(word['ana']) > 0:
                    nAnalyzed += 1
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        if 'add_contextual_flags' in self.corpusSettings and self.corpusSettings['add_contextual_flags']:
            self.tp.splitter.add_contextual_flags(textJSON['sentences'])
        self.tp.splitter.add_speaker_marks(textJSON['sentences'])
        self.add_sentence_meta(textJSON['sentences'], curMeta)
        if 'capitalize_sentences' in self.corpusSettings and self.corpusSettings['capitalize_sentences']:
            self.tp.splitter.capitalize_sentences(textJSON['sentences'])
        self.tp.splitter.prepare_kw_word_fields(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed

    def process_corpus(self, cutMedia=True):
        """
        Take every eaf file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        """
        Txt2JSON.process_corpus(self)
        if not cutMedia:
            return
        mediaDir = os.path.join(self.corpusSettings['corpus_dir'], self.srcExt)
        if 'media_dir' in self.corpusSettings:
            mediaDir = self.corpusSettings['media_dir']
        for path, dirs, files in os.walk(mediaDir):
            # Process video files first
            files = [fname for fname in files if fname.lower().endswith(('.avi', '.mts', '.mov'))] + \
                    [fname for fname in files if fname.lower().endswith('.mp4')] + \
                    [fname for fname in files if not fname.lower().endswith(('.avi', '.mts', '.mov', '.mp4'))]
            for fname in files:
                fileExt = os.path.splitext(fname.lower())[1]
                if fileExt in self.mediaExtensions:
                    privacySegments = []
                    if fname in self.privacySegments:
                        privacySegments = self.privacySegments[fname]
                    fname = os.path.abspath(os.path.join(path, fname))
                    print('Cutting media file', fname)
                    self.mc.cut_media(fname,
                                      usedFilenames=self.usedMediaFiles,
                                      privacySegments=privacySegments)


if __name__ == '__main__':
    t2j = Eaf2JSON()
    t2j.process_corpus(cutMedia=True)

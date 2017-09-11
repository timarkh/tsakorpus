import os
import re
import html
from lxml import etree
from txt2json import Txt2JSON
from media_operations import MediaCutter


EAF_TIME_MULTIPLIER = 1000  # time stamps are in milliseconds


class Eaf2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    ELAN aligned files, a csv with metadata and a list with parsed
    word forms.
    """

    mediaExtensions = {'.wav', '.mp3', '.mp4', '.avi'}

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'eaf'
        self.tlis = {}      # time labels
        self.pID = 0        # id of last aligned segment
        self.glosses = set()

    def get_meta(self, fname):
        fname2check = fname
        curMeta = {'filename': fname}
        if not self.corpusSettings['meta_files_dir']:
            fname2check = self.rxStripDir.sub('', fname2check)
        if not self.corpusSettings['meta_files_ext']:
            fname2check = self.rxStripExt.sub('', fname2check)
        if not self.corpusSettings['meta_files_case_sensitive']:
            fname2check = fname2check.lower()
        if fname2check not in self.meta:
            print('File not in meta:', fname)
        else:
            curMeta.update(self.meta[fname2check])
        return curMeta

    def get_tlis(self, srcTree):
        """
        Retrieve and return all time labels from the XML tree.
        """
        tlis = {}
        iTli = 0
        for tli in srcTree.xpath('/ANNOTATION_DOCUMENT/TIME_ORDER/TIME_SLOT'):
            timeValue = ''
            if 'TIME_VALUE' in tli.attrib:
                timeValue = tli.attrib['TIME_VALUE']
            tlis[tli.attrib['TIME_SLOT_ID']] = {'n': iTli, 'time': timeValue}
            iTli += 1
        return tlis

    def fragmentize_src_alignment(self, alignment):
        """
        Find corresponding media file fragment and transform a JSON
        dictionary with the information about the alignment.
        """
        fileName, fileExt = os.path.splitext(alignment['src'].lower())
        if fileExt not in self.mediaExtensions:
            return
        ts1 = alignment['off_start_src']
        ts2 = alignment['off_end_src']
        if len(ts1) <= 0 or len(ts2) <= 0:
            return
        ts1frag, ts2frag, srcFileFrag = self.mc.get_media_name(alignment['src'],
                                                               float(ts1) / EAF_TIME_MULTIPLIER,
                                                               float(ts2) / EAF_TIME_MULTIPLIER)
        alignment['src'] = srcFileFrag
        alignment['off_start_src'] = str(ts1frag)
        alignment['off_end_src'] = str(ts2frag)

    def add_src_alignment(self, sent, tli1, tli2, srcFile):
        """
        Add the alignment of the sentence with the sound/video. If
        word-level time data is available, align words, otherwise
        align the whole sentence.
        """
        sentAlignments = []
        ts1 = self.tlis[tli1]['time']
        ts2 = self.tlis[tli2]['time']
        sentAlignments.append({'off_start_src': ts1,
                               'off_end_src': ts2,
                               'true_off_start_src': float(ts1) / EAF_TIME_MULTIPLIER,
                               'off_start_sent': 0,
                               'off_end_sent': len(sent['text']),
                               'mtype': 'audio',
                               'src_id': ts1 + '_' + ts2,
                               'src': srcFile})
        for alignment in sentAlignments:
            self.fragmentize_src_alignment(alignment)
        sent['src_alignment'] = sentAlignments

    def process_tier(self, tierNode, aID2pID, srcFile, alignedTier=False):
        """
        Extract segments from the tier node and iterate over them, returning
        them as JSON sentences. If alignedTier is False, store the start and end
        timestamps, as well as pIDs for alignment, in the dictionary aID2pID.
        If alignedTier is True, use the information from aID2pID for establishing
        time boundaries of the sentences and aligning it with the source tier. 
        """
        if ('LINGUISTIC_TYPE_REF' not in tierNode.attrib or
                tierNode.attrib['LINGUISTIC_TYPE_REF'] not in self.corpusSettings['tier_languages']):
            return
        lang = self.corpusSettings['tier_languages'][tierNode.attrib['LINGUISTIC_TYPE_REF']]
        if lang not in self.corpusSettings['languages']:
            return
        langID = self.corpusSettings['languages'].index(lang)
        if alignedTier:
            xpathExpr = 'ANNOTATION/REF_ANNOTATION'
        else:
            xpathExpr = 'ANNOTATION/ALIGNABLE_ANNOTATION'
        speaker = ''
        if 'PARTICIPANT' in tierNode.attrib:
            speaker = tierNode.attrib['PARTICIPANT']
        segments = tierNode.xpath(xpathExpr)

        for segment in segments:
            if not alignedTier:
                if ('TIME_SLOT_REF1' not in segment.attrib or
                        'TIME_SLOT_REF2' not in segment.attrib):
                    continue
                tli1 = segment.attrib['TIME_SLOT_REF1']
                tli2 = segment.attrib['TIME_SLOT_REF2']
            elif 'ANNOTATION_REF' in segment.attrib:
                aID = segment.attrib['ANNOTATION_REF']
                pID, tli1, tli2 = aID2pID[aID]
            else:
                continue
            text = segment.xpath('ANNOTATION_VALUE')[0].text
            if text is None:
                text = ''
            curSent = {'text': text, 'words': self.tp.tokenizer.tokenize(text), 'lang': langID,
                       'meta': {'speaker': speaker}}
            self.tp.splitter.add_next_word_id_sentence(curSent)
            self.tp.parser.analyze_sentence(curSent, lang=lang)
            if not alignedTier and 'ANNOTATION_ID' in segment.attrib:
                self.pID += 1
                aID = segment.attrib['ANNOTATION_ID']
                aID2pID[aID] = (self.pID, tli1, tli2)
                paraAlignment = {'off_start': 0, 'off_end': len(curSent['text']), 'para_id': self.pID}
                curSent['para_alignment'] = [paraAlignment]
            elif alignedTier:
                paraAlignment = {'off_start': 0, 'off_end': len(curSent['text']), 'para_id': pID}
                curSent['para_alignment'] = [paraAlignment]
            self.add_src_alignment(curSent, tli1, tli2, srcFile)
            yield curSent

    def get_sentences(self, srcTree, srcFile):
        """
        Iterate over sentences in the XML tree.
        """
        mainTierTypes = '(' + ' | '.join('/ANNOTATION_DOCUMENT/TIER[@LINGUISTIC_TYPE_REF=\'' + x + '\']'
                                         for x in self.corpusSettings['main_tiers']) + ')'
        mainTiers = srcTree.xpath(mainTierTypes)
        if len(mainTiers) <= 0:
            return
        alignedTierTypes = '(' + ' | '.join('/ANNOTATION_DOCUMENT/TIER[@LINGUISTIC_TYPE_REF=\'' + x + '\']'
                                            for x in self.corpusSettings['aligned_tiers']) + ')'
        alignedTiers = srcTree.xpath(alignedTierTypes)
        aID2pID = {}    # annotation ID -> (pID, tli1, tli2) correspondence
        for tier in mainTiers:
            for sent in self.process_tier(tier, aID2pID, srcFile, alignedTier=False):
                yield sent
        for tier in alignedTiers:
            for sent in self.process_tier(tier, aID2pID, srcFile, alignedTier=True):
                yield sent

    def add_speaker_marks(self, sentences):
        """
        Add the name/code of the speaker in the beginning of every
        sentence that starts the turn.
        """
        prevSpeaker = ''
        for i in range(len(sentences)):
            if 'meta' not in sentences[i] or 'speaker' not in sentences[i]['meta']:
                continue
            speaker = '[' + sentences[i]['meta']['speaker'] + ']'
            addOffset = len(speaker) + 2
            if sentences[i]['meta']['speaker'] != prevSpeaker:
                sentences[i]['text'] = '\n' + speaker + ' ' + sentences[i]['text']
                sentences[i]['words'].insert(0, {'off_start': -len(speaker) - 1,
                                                 'off_end': -1,
                                                 'wf': speaker,
                                                 'wtype': 'punc',
                                                 'next_word': 0})
                sentences[i]['words'].insert(0, {'off_start': -len(speaker) - 2,
                                                 'off_end': -len(speaker)-1,
                                                 'wf': '\n',
                                                 'wtype': 'punc',
                                                 'next_word': -1})
                for w in sentences[i]['words']:
                    w['off_start'] += addOffset
                    w['off_end'] += addOffset
                    w['next_word'] += 2
                if 'para_alignment' in sentences[i]:
                    for pa in sentences[i]['para_alignment']:
                        if pa['off_start'] > 0:
                            pa['off_start'] += addOffset
                        pa['off_end'] += addOffset
                if 'src_alignment' in sentences[i]:
                    for sa in sentences[i]['src_alignment']:
                        if sa['off_start_sent'] > 0:
                            sa['off_start_sent'] += addOffset
                        sa['off_end_sent'] += addOffset
            prevSpeaker = sentences[i]['meta']['speaker']
            if 'last' in sentences[i] and sentences[i]['last']:
                prevSpeaker = ''

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyze = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        srcFileNode = srcTree.xpath('/ANNOTATION_DOCUMENT/HEADER/MEDIA_DESCRIPTOR')
        if len(srcFileNode) > 0 and 'RELATIVE_MEDIA_URL' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', html.unescape(srcFileNode[0].attrib['RELATIVE_MEDIA_URL']))
        elif len(srcFileNode) > 0 and 'MEDIA_URL' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', html.unescape(srcFileNode[0].attrib['MEDIA_URL']))
        else:
            srcFile = ''
        textJSON['sentences'] = [s for s in self.get_sentences(srcTree, srcFile)]
        textJSON['sentences'].sort(key=lambda s: (s['lang'], s['src_alignment'][0]['true_off_start_src']))
        for i in range(len(textJSON['sentences']) - 1):
            # del textJSON['sentences'][i]['src_alignment'][0]['true_off_start_src']
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        self.add_speaker_marks(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyze

    def process_corpus(self, cutMedia=True):
        """
        Take every eaf file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        """
        Txt2JSON.process_corpus(self)
        if not cutMedia:
            return
        for path, dirs, files in os.walk(os.path.join(self.corpusSettings['corpus_dir'],
                                                      self.srcExt)):
            for fname in files:
                fileExt = os.path.splitext(fname.lower())[1]
                if fileExt in self.mediaExtensions:
                    fname = os.path.abspath(os.path.join(path, fname))
                    print('Cutting media file', fname)
                    self.mc.cut_media(fname)


if __name__ == '__main__':
    t2j = Eaf2JSON()
    t2j.process_corpus(cutMedia=False)

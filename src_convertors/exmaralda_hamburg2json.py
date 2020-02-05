import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON
from media_operations import MediaCutter


class Exmaralda_Hamburg2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from aligned
    Exmaralda files in the format used in documentation projects
    carried out in Hamburg.
    """

    rxBracketGloss = re.compile('\\.?\\[.*?\\]')
    rxSplitGlosses = re.compile('-|\\.(?=\\[)')
    rxWordPunc = re.compile('^( *)([^\\w]*)(.*?)([^\\w]*?)( *)$')
    txTierXpath = '/basic-transcription/basic-body/tier[@id=\'tx\']'
    mediaExtensions = {'.wav', '.mp3', '.mp4', '.avi'}

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'exb'  # extension of the source files to be converted
        self.tlis = {}       # time labels (id -> {'n': number, 'time': time value})
        self.pID = 0         # id of last aligned segment
        self.glosses = set()

    def get_tlis(self, srcTree):
        """
        Retrieve and return all time labels from the XML tree.
        """
        tlis = {}
        iTli = 0
        for tli in srcTree.xpath('/basic-transcription/basic-body/common-timeline')[0]:
            timeValue = ''
            if 'time' in tli.attrib:
                timeValue = tli.attrib['time']
            tlis[tli.attrib['id']] = {'n': iTli, 'time': timeValue}
            iTli += 1
        return tlis

    def find_sentence_index(self, sentenceBoundaries, tli):
        """
        Find the number of the sentence the event with the given
        time label (start or end) belongs to.
        """
        if tli not in self.tlis:
            return -1
        for i in range(len(sentenceBoundaries)):
            tliStart, tliEnd = sentenceBoundaries[i]
            if (tli == tliStart or
                    self.tlis[tliStart]['n'] <= self.tlis[tli]['n'] < self.tlis[tliEnd]['n']):
                return i
        return -1

    def get_sentence_boundaries(self, refTier):
        """
        Go over the reference tier (as XML node). For each event
        in the tier, extract start and end attributes. Return a list
        with (start time label, end time label) tuples.
        """
        boundaries = []
        for event in refTier:
            if 'start' not in event.attrib or 'end' not in event.attrib:
                continue
            sentStart, sentEnd = event.attrib['start'], event.attrib['end']
            if sentStart not in self.tlis or sentEnd not in self.tlis:
                continue
            boundaries.append((sentStart, sentEnd))
        return boundaries

    def get_word_tlis(self, srcTree):
        """
        Collect all pairs of time labels that delimit words.
        """
        txTiers = srcTree.xpath(Exmaralda_Hamburg2JSON.txTierXpath)
        tliTuples = set()
        for txTier in txTiers:
            for event in txTier:
                if 'start' not in event.attrib or 'end' not in event.attrib:
                    continue
                tliTuple = (event.attrib['start'], event.attrib['end'])
                tliTuples.add(tliTuple)
        return tliTuples

    def collect_annotation(self, srcTree):
        """
        Return a dictionary that contains all word-level annotation events,
        the keys are tuples (start time label, end time label).
        """
        wordTlis = self.get_word_tlis(srcTree)
        wordAnno = {}
        for tier in srcTree.xpath('/basic-transcription/basic-body/tier[@type=\'a\']'):
            if 'id' not in tier.attrib:
                continue
            # tierID = tier.attrib['id']
            tierID = tier.attrib['category']
            if tierID in self.corpusSettings['translation_tiers'] or tierID in ('tx', 'ts'):
                continue
            for event in tier:
                if ('start' not in event.attrib or 'end' not in event.attrib
                        or event.text is None):
                    continue
                tupleKey = (event.attrib['start'], event.attrib['end'])

                # If an annotation spans several tokens, add it to each of them:
                tupleKeys = [tupleKey]
                if tupleKey not in wordTlis:
                    for wordTli in wordTlis:
                        if ((wordTli[0] == tupleKey[0]
                                     or self.tlis[tupleKey[0]]['n'] <= self.tlis[wordTli[0]]['n'])
                                and (wordTli[1] == tupleKey[1]
                                     or self.tlis[tupleKey[1]]['n'] >= self.tlis[wordTli[1]]['n'])):
                            tupleKeys.append(wordTli)

                for tk in tupleKeys:
                    if tk not in wordAnno:
                        wordAnno[tk] = {}
                    wordAnno[tk][tierID] = event.text
        return wordAnno

    def add_ana_fields(self, ana, curWordAnno):
        """
        Add the information from the annotation tier events for the
        current word to the analysis. For each tier, the name of the
        tier is the used as the name of the field, and the text of
        the event is used as the value.
        """
        for tierName in curWordAnno:
            if tierName in ['tx', 'mb', 'mp', 'gr', 'ge']:
                continue
            if tierName == 'ps':
                ana['gr.pos'] = curWordAnno[tierName]
            else:
                ana[tierName] = curWordAnno[tierName]

    def get_words(self, srcTree):
        """
        Iterate over words found in the tx tier of the XML tree.
        """
        txTier = srcTree.xpath(Exmaralda_Hamburg2JSON.txTierXpath)
        wordAnno = self.collect_annotation(srcTree)
        for event in txTier[0]:
            if 'start' not in event.attrib or 'end' not in event.attrib:
                continue
            tupleKey = (event.attrib['start'], event.attrib['end'])
            if tupleKey not in wordAnno:
                continue
            wf = event.text
            if wf is None:
                continue
            curToken = {'wf': wf, 'wtype': 'word',
                        'tli_start': event.attrib['start'],
                        'tli_end': event.attrib['end']}
            if self.tp.tokenizer.rxOnlyPunc.search(wf.strip()) is not None:
                curToken['wtype'] = 'punct'
                yield curToken
                continue
            ana = {}
            curWordAnno = wordAnno[tupleKey]
            # mp: morph breaks with empty morphemes (corresponds to the mc tier: POS and morph categories)
            # mb: morph breaks without empty morphemes (corresponds to the gr/ge tiers: actual glosses)
            if 'mb' in curWordAnno:
                ana['parts'] = curWordAnno['mb']
            if 'ge' in curWordAnno:
                ana['gloss'] = curWordAnno['ge']
                self.glosses |= set(g for g in self.rxSplitGlosses.split(ana['gloss']) if g.upper() == g)
                # print(ana['gloss'], self.rxSplitGlosses.split(ana['gloss']))
            self.tp.parser.process_gloss_in_ana(ana)
            if 'gloss_index' in ana:
                stems, newIndexGloss = self.tp.parser.find_stems(ana['gloss_index'],
                                                                 self.corpusSettings['languages'][0])
                ana['lex'] = ' '.join(s[1] for s in stems)
                ana['trans_en'] = self.rxBracketGloss.sub('', ' '.join(s[0] for s in stems))
                self.add_ana_fields(ana, curWordAnno)
                useGlossList = False
                if 'glosses' in self.corpusSettings:
                    useGlossList = True
                self.tp.parser.gloss2gr(ana, self.corpusSettings['languages'][0], useGlossList=useGlossList)
                ana['gloss_index'] = self.rxBracketGloss.sub('', newIndexGloss)
            curToken['ana'] = [ana]
            yield curToken

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
                                                               float(ts1), float(ts2))
        alignment['src'] = srcFileFrag
        alignment['off_start_src'] = str(ts1frag)
        alignment['off_end_src'] = str(ts2frag)

    def add_src_alignment(self, sent, sentBoundaries, srcFile):
        """
        Add the alignment of the sentence with the sound/video. If
        word-level time data is available, align words, otherwise
        align the whole sentence.
        """
        wordAlignments = []
        for word in sent['words']:
            if 'tli_start' not in word or 'tli_end' not in word:
                continue
            if len(self.tlis[word['tli_start']]['time']) > 0:
                for wa in wordAlignments:
                    if len(wa['off_end_src']) <= 0:
                        wa['off_end_src'] = self.tlis[word['tli_start']]['time']
                        wa['src_id'] += word['tli_start']
                wordAlignments.append({'off_start_src': self.tlis[word['tli_start']]['time'],
                                       'off_end_src': '',
                                       'off_start_sent': word['off_start'],
                                       'off_end_sent': word['off_end'],
                                       'mtype': 'audio',
                                       'src': srcFile,
                                       'src_id': word['tli_start'] + '_'})
            if len(self.tlis[word['tli_end']]['time']) > 0:
                for wa in wordAlignments:
                    if len(wa['off_end_src']) <= 0:
                        wa['off_end_src'] = self.tlis[word['tli_end']]['time']
                        wa['off_end_sent'] = word['off_end']
                        wa['src_id'] += word['tli_end']
        for wa in wordAlignments:
            if len(wa['off_end_src']) <= 0:
                if len(self.tlis[sentBoundaries[1]]['time']) > 0:
                    wa['off_end_src'] = self.tlis[sentBoundaries[1]]['time']
                    wa['src_id'] += sentBoundaries[1]
                else:
                    wa['off_end_src'] = wa['off_start_src']
                    wa['src_id'] += wa['src_id'][:-1]
                    wa['off_end_sent'] = len(sent['text'])
        # if len(wordAlignments) <= 0 and len(self.tlis[sentBoundaries[0]]['time']) > 0:
        if len(self.tlis[sentBoundaries[0]]['time']) > 0:
            wordAlignments = []     # for the time being
            wordAlignments.append({'off_start_src': self.tlis[sentBoundaries[0]]['time'],
                                   'off_end_src': self.tlis[sentBoundaries[1]]['time'],
                                   'off_start_sent': 0,
                                   'off_end_sent': len(sent['text']),
                                   'mtype': 'audio',
                                   'src_id': sentBoundaries[0] + '_' + sentBoundaries[1],
                                   'src': srcFile})
        if len(wordAlignments) > 0:
            for alignment in wordAlignments:
                self.fragmentize_src_alignment(alignment)
            sent['src_alignment'] = wordAlignments

    def get_parallel_sentences(self, srcTree, sentBoundaries, srcFile):
        """
        Iterate over sentences in description tiers aligned with the
        sentence in the main tx tier. The sentence to align with is
        defined by the tuple sentBoundaries that contains the start
        and the end time label for the sentence.
        """
        self.pID += 1
        for iTier in range(len(self.corpusSettings['translation_tiers'])):
            tierName = self.corpusSettings['translation_tiers'][iTier]
            events = srcTree.xpath('/basic-transcription/basic-body/'
                                   'tier[@id=\'' + tierName + '\']/'
                                   'event[@start=\'' + sentBoundaries[0] +
                                   '\' and @end=\'' + sentBoundaries[1] + '\']')
            for event in events:
                text = ''
                for child in event:
                    if child.tail is not None:
                        text += child.tail
                if len(text) <= 0:
                    text = event.text
                if text is None or len(text) <= 0:
                    text = ''
                text = self.tp.cleaner.clean_text(text)
                if len(text) <= 0:
                    words = [{'wf': '—',
                              'wtype': 'punct',
                              'off_start': 0,
                              'off_end': 1}]
                    text = '—'
                else:
                    words = self.tp.tokenizer.tokenize(text)
                paraAlignment = {'off_start': 0, 'off_end': len(text), 'para_id': self.pID}
                paraSent = {'words': words, 'text': text, 'para_alignment': [paraAlignment],
                            'lang': len(self.corpusSettings['languages']) + iTier}
                self.add_src_alignment(paraSent, sentBoundaries, srcFile)
                yield paraSent

    def get_sentences(self, srcTree, srcFile):
        """
        Iterate over sentences in the XML tree.
        """
        refTiers = srcTree.xpath('/basic-transcription/basic-body/tier[@id=\'ref\']')
        if len(refTiers) <= 0:
            return
        refTier = refTiers[0]
        # TODO: Multiple layers
        sentBoundaries = self.get_sentence_boundaries(refTier)
        prevSentIndex = -1
        curSent = {'text': '', 'words': [], 'lang': 0}
        for word in self.get_words(srcTree):
            curSentIndex = self.find_sentence_index(sentBoundaries, word['tli_start'])
            if curSentIndex != prevSentIndex and len(curSent['text']) > 0:
                paraAlignment = {'off_start': 0, 'off_end': len(curSent['text']), 'para_id': self.pID}
                curSent['para_alignment'] = [paraAlignment]
                self.add_src_alignment(curSent, sentBoundaries[prevSentIndex], srcFile)
                yield curSent
                curSent = {'text': '', 'words': [], 'lang': 0}
                for paraSent in self.get_parallel_sentences(srcTree, sentBoundaries[curSentIndex],
                                                            srcFile):
                    yield paraSent
            prevSentIndex = curSentIndex
            if word['wtype'] == 'punct':
                word['off_start'] = len(curSent['text'])
                curSent['text'] += word['wf']
                word['off_end'] = len(curSent['text'])
                word['wf'] = word['wf'].strip()
                continue
            m = self.rxWordPunc.search(word['wf'])
            spacesL, punctL, wf, punctR, spacesR =\
                m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            curSent['text'] += spacesL
            if len(punctL) > 0:
                punc = {'wf': punctL, 'wtype': 'punct',
                        'off_start': len(curSent['text']),
                        'off_end': len(curSent['text']) + len(punctL)}
                curSent['text'] += punctL
                curSent['words'].append(punc)
            word['off_start'] = len(curSent['text'])
            curSent['text'] += wf
            word['off_end'] = len(curSent['text'])
            word['wf'] = wf
            curSent['words'].append(word)
            if len(punctR) > 0:
                punc = {'wf': punctR, 'wtype': 'punct',
                        'off_start': len(curSent['text']),
                        'off_end': len(curSent['text']) + len(punctR)}
                curSent['text'] += punctR
                curSent['words'].append(punc)
            curSent['text'] += spacesR
        if len(curSent['text']) > 0:
            paraAlignment = {'off_start': 0, 'off_end': len(curSent['text']), 'para_id': self.pID}
            curSent['para_alignment'] = [paraAlignment]
            self.add_src_alignment(curSent, sentBoundaries[curSentIndex], srcFile)
            yield curSent

    def convert_file(self, fnameSrc, fnameTarget):
        """
        Take one source Exmaralda file fnameSrc, parse the XML tree,
        extract timestamps, align sentences with words and their
        analyses and ultimately generate a parsed JSON file
        ready for indexing. Write the output to fnameTarget.
        Return number of tokens, number of words and number of
        words with at least one analysis in the document.
        """
        curMeta = self.get_meta(fnameSrc)
        # curMeta = {'title': fnameSrc, 'author': '', 'year1': '1900', 'year2': '2017'}
        if curMeta is None:
            return 0, 0, 0
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        srcFileNode = srcTree.xpath('/basic-transcription/head/meta-information/referenced-file')
        if len(srcFileNode) > 0 and 'url' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', srcFileNode[0].attrib['url'])
        else:
            srcFile = ''
        textJSON['sentences'] = [s for s in self.get_sentences(srcTree, srcFile)]
        textJSON['sentences'].sort(key=lambda s: s['lang'])
        for i in range(len(textJSON['sentences']) - 1):
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
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed

    def process_corpus(self, cutMedia=True):
        """
        Take every Exmaralda file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        Split all the corpus media files into overlapping chunks of
        small duration.
        This is the main function of the class.
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
    x2j = Exmaralda_Hamburg2JSON()
    x2j.process_corpus(cutMedia=False)


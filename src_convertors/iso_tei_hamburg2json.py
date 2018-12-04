import os
import re
import json
import copy
from lxml import etree
from txt2json import Txt2JSON
from media_operations import MediaCutter


class ISO_TEI_Hamburg2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from transcriptions
    aligned in Exmaralda in the format used in documentation projects
    carried out in Hamburg and then translated into a certain ISO TEI subset.
    """

    rxBracketGloss = re.compile('\\.?\\[.*?\\]')
    rxWordPunc = re.compile('^( *)([^\\w]*)(.*?)([^\\w]*?)( *)$')
    rxLetters = re.compile('\w+')
    rxFloat = re.compile('^[0-9]+(?:\.[0-9]+)?$')
    rxTrailingZeroes = re.compile('^0+(?=[1-9])|\.0+$')
    rxNonDigit = re.compile('[^0-9]+')
    mediaExtensions = {'.wav', '.mp3', '.mp4', '.avi'}
    sentenceEndPunct = {'declarative': '.', 'interrogative': '?'}
    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0',
                  'xml': 'http://www.w3.org/XML/1998/namespace'}
    pfx_xml = '{http://www.w3.org/XML/1998/namespace}'
    pfx_tei = '{http://www.tei-c.org/ns/1.0}'

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'xml'  # extension of the source files to be converted
        self.participants = {}   # participant ID -> dictionary of properties
        self.tlis = {}       # time labels (id -> {'n': number, 'time': time value})
        self.wordsByID = {}  # word ID -> word object
        self.morph2wordID = {}   # morph ID -> (word ID, position in the word)
        self.pID = 0         # id of last aligned segment
        self.seg2pID = {}    # ids of <seg> tags -> parallel IDs of corresponding sentences
        self.glosses = set()
        self.posRules = {}
        self.load_pos_rules(os.path.join(self.corpusSettings['corpus_dir'], 'conf/posRules.txt'))

    def load_pos_rules(self, fname):
        """
        Load mapping of the POS tags used in the source files to your corpus POS tags.
        """
        if len(fname) <= 0 or not os.path.isfile(fname):
            return
        rules = {}
        f = open(fname, 'r', encoding='utf-8-sig')
        for line in f:
            line = line.strip('\r\n')
            if len(line) > 0:
                rule = [i.strip() for i in line.split('\t')]
                if len(rule) != 2:
                    continue
                rules[rule[0]] = rule[1]
        f.close()
        self.posRules = rules

    def load_speaker_meta(self, srcTree):
        speakerMeta = {}
        if 'speaker_meta_filename' in self.corpusSettings:
            try:
                f = open(os.path.join(self.corpusSettings['corpus_dir'],
                                      self.corpusSettings['speaker_meta_filename']),
                         'r', encoding='utf-8-sig')
                speakerMeta = json.loads(f.read())
                f.close()
            except FileNotFoundError:
                print('The speaker metadata file not found.')
        else:
            for speaker in srcTree.xpath('/tei:TEI/tei:teiHeader/tei:profileDesc/tei:particDesc/tei:person',
                                         namespaces=self.namespaces):
                if 'id' not in speaker.attrib:
                    continue
                speakerID = speaker.attrib['id']
                if 'n' in speaker.attrib:
                    speakerCode = speaker.attrib['n']
                else:
                    speakerCode = speakerID
                speakerMeta[speakerID] = {'speakerCode': speakerCode}
                if 'sex' in speaker.attrib:
                    if speaker.attrib['sex'] in ['1', 'M']:
                        speakerMeta[speakerID]['gender'] = 'M'
                    elif speaker.attrib['sex'] in ['2', 'F']:
                        speakerMeta[speakerID]['gender'] = 'F'
                    else:
                        speakerMeta[speakerID]['gender'] = speaker.attrib['sex']
                if 'age' in speaker.attrib:
                    speakerMeta[speakerID]['age'] = speaker.attrib['age']
                if 'role' in speaker.attrib:
                    speakerMeta[speakerID]['role'] = speaker.attrib['role']
        return speakerMeta

    def get_tlis(self, srcTree):
        """
        Retrieve and return all time labels from the XML tree.
        """
        tlis = {}
        iTli = 0
        for tli in srcTree.xpath('/tei:TEI/tei:text/tei:timeline',
                                 namespaces=self.namespaces)[0]:
            timeValue = tli.attrib[self.pfx_xml + 'id']
            if 'interval' in tli.attrib:
                timeValue = tli.attrib['interval']
            elif tli.attrib[self.pfx_xml + 'id'] in ['T0', 'T_START']:
                timeValue = '0'
            timeValue = self.rxTrailingZeroes.sub('', timeValue)
            tlis[tli.attrib[self.pfx_xml + 'id']] = {'n': iTli, 'time': timeValue}
            iTli += 1
        return tlis

    def add_pos_ana(self, ana, pos):
        """
        Add the part of speech tag to single JSON analysis, taking into
        account the correspondences between source file tags and the target
        corpus tags. Change the analysis, do not return anything.
        """
        if pos in self.posRules:
            pos = self.posRules[pos]
        if 'gr.pos' not in ana:
            ana['gr.pos'] = pos
        elif type(ana['gr.pos']) == str and ana['gr.pos'] != pos:
            ana['gr.pos'] = [ana['gr.pos'], pos]
        elif pos not in ana['gr.pos']:
            ana['gr.pos'].append(pos)

    def collect_annotation(self, annoTree):
        """
        Return a dictionary that contains all word-level annotation events
        within an annotation block, the keys are word IDs.
        """
        wordAnno = {}
        for tier in annoTree.xpath('tei:spanGrp',
                                   namespaces=self.namespaces):
            if 'type' not in tier.attrib:
                continue
            tierID = tier.attrib['type']
            prevWordID = '-1'
            curWordNMorphs = 0
            for wSpan in tier:
                if 'from' not in wSpan.attrib or 'to' not in wSpan.attrib:
                    continue
                if wSpan.attrib['from'] != wSpan.attrib['to']:
                    continue
                spanID = wSpan.attrib['from']
                if spanID.startswith('seg'):
                    continue
                elif spanID.startswith('w'):
                    wordID = spanID
                elif spanID.startswith('m'):
                    wordID = self.morph2wordID[spanID][0]
                if wordID != prevWordID:
                    prevWordID = wordID
                    curWordNMorphs = 0
                if wordID not in wordAnno:
                    wordAnno[wordID] = {}
                if self.pfx_xml + 'id' in wSpan.attrib:
                    self.morph2wordID[wSpan.attrib[self.pfx_xml + 'id']] = (wordID, curWordNMorphs)
                    curWordNMorphs += 1
                    if wSpan.text is not None:
                        wordAnno[wordID][tierID] = wSpan.text
                    else:
                        wordAnno[wordID][tierID] = ''
                elif tierID not in ['mb', 'mp', 'ge', 'gr']:
                    # Word-based annotations: one flat span for each word
                    if tierID not in wordAnno[wordID]:
                        wordAnno[wordID][tierID] = ''
                    if len(wordAnno[wordID][tierID]) > 0:
                        wordAnno[wordID][tierID] += '-'
                    if wSpan.text is not None:
                        wordAnno[wordID][tierID] += wSpan.text
                else:
                    # Multiple morphemes inside one span in e.g. the mb tier
                    wordAnno[wordID][tierID] = ''
                    for mSpan in wSpan:
                        if self.pfx_xml + 'id' in mSpan.attrib:
                            mID = mSpan.attrib[self.pfx_xml + 'id']
                        elif ('from' in mSpan.attrib and 'to' in mSpan.attrib
                              and mSpan.attrib['from'] == mSpan.attrib['to']):
                            mID = mSpan.attrib['from']
                        else:
                            continue
                        self.morph2wordID[mID] = (wordID, curWordNMorphs)
                        curWordNMorphs += 1
                        if tierID not in wordAnno[wordID]:
                            wordAnno[wordID][tierID] = ''
                        if len(wordAnno[wordID][tierID]) > 0:
                            wordAnno[wordID][tierID] += '-'
                        if mSpan.text is not None:
                            wordAnno[wordID][tierID] += mSpan.text
                        else:
                            wordAnno[wordID][tierID] += '∅'
        return wordAnno

    def add_ana_fields(self, ana, curWordAnno):
        """
        Add the information from the annotation tier events for the
        current word to the analysis. For each tier, the name of the
        tier is the used as the name of the field, and the text of
        the event is used as the value.
        """
        for tierName in curWordAnno:
            if tierName in ['tx', 'mb', 'mp', 'gr', 'ge', 'ps']:
                continue
            elif len(curWordAnno[tierName]) > 0:
                ana[tierName] = curWordAnno[tierName]

    def process_words(self, annoTree):
        """
        Iterate over words in an annotation block and add their
        analyses to the corresponding word objects in the sentences.
        """
        wordAnno = self.collect_annotation(annoTree)
        for wordID in wordAnno:
            ana = {}
            curWordAnno = wordAnno[wordID]
            # mp: morph breaks with empty morphemes (corresponds to the mc tier: POS and morph categories)
            # mb: morph breaks without empty morphemes (corresponds to the gr/ge tiers: actual glosses)
            if 'mb' in curWordAnno:
                ana['parts'] = curWordAnno['mb']
            if 'ge' in curWordAnno:
                ana['gloss'] = curWordAnno['ge']
                self.glosses |= set(g for g in ana['gloss'].split('-') if g.upper() == g)
            if 'ps' in curWordAnno:
                self.add_pos_ana(ana, curWordAnno['ps'])
            self.tp.parser.process_gloss_in_ana(ana)
            if 'gloss_index' in ana:
                stems, newIndexGloss = self.tp.parser.find_stems(ana['gloss_index'],
                                                                 self.corpusSettings['languages'][0])
                ana['lex'] = ' '.join(s[1] for s in stems)
                ana['trans_en'] = self.rxBracketGloss.sub('', ' '.join(s[0] for s in stems))
                self.add_ana_fields(ana, curWordAnno)
                self.tp.parser.gloss2gr(ana, self.corpusSettings['languages'][0])
                ana['gloss_index'] = self.rxBracketGloss.sub('', newIndexGloss)
            self.wordsByID[wordID]['ana'] = [ana]

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
        Add the alignment of the sentence with the sound/video.
        """
        alignment = {'off_start_src': self.tlis[sentBoundaries[0]]['time'],
                     'off_end_src': self.tlis[sentBoundaries[1]]['time'],
                     'off_start_sent': 0,
                     'off_end_sent': len(sent['text']),
                     'mtype': 'audio',
                     'src_id': sentBoundaries[0] + '_' + sentBoundaries[1],
                     'src': srcFile}
        if (self.rxFloat.search(alignment['off_start_src']) is None
                or self.rxFloat.search(alignment['off_end_src']) is None):
            return
        self.fragmentize_src_alignment(alignment)
        sent['src_alignment'] = [alignment]

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
            events = srcTree.xpath('/tei:basic-transcription/tei:basic-body/'
                                   'tei:tier[@xml:id=\'' + tierName + '\']/'
                                   'tei:event[@tei:start=\'' + sentBoundaries[0] +
                                   '\' and @tei:end=\'' + sentBoundaries[1] + '\']',
                                   namespaces=self.namespaces)
            for event in events:
                text = ''
                for child in event:
                    if child.tail is not None:
                        text += child.tail
                if len(text) <= 0:
                    text = event.text
                if text is None or len(text) <= 0:
                    continue
                text = self.tp.cleaner.clean_text(text)
                words = self.tp.tokenizer.tokenize(text)
                paraAlignment = {'off_start': 0, 'off_end': len(text), 'para_id': self.pID}
                paraSent = {'words': words, 'text': text, 'para_alignment': [paraAlignment],
                            'lang': len(self.corpusSettings['languages']) + iTier}
                self.add_src_alignment(paraSent, sentBoundaries, srcFile)
                yield paraSent

    def get_segment_words(self, segment):
        """
        Extract all words and punctuation from a <seg> node.
        Return list of words and fill the self.wordsByID dictionary
        ({word ID -> word object in the list}).
        """
        wordList = []
        for wordNode in segment:
            if self.pfx_xml + 'id' not in wordNode.attrib:
                continue
            if wordNode.tag == self.pfx_tei + 'w':
                word = {'wf': wordNode.text.strip(), 'wtype': 'word'}
                wordList.append(word)
                self.wordsByID[wordNode.attrib[self.pfx_xml + 'id']] = word
            elif wordNode.tag == self.pfx_tei + 'pc':
                word = {'wf': wordNode.text.strip(), 'wtype': 'punc'}
                wordList.append(word)
                self.wordsByID[wordNode.attrib[self.pfx_xml + 'id']] = word
        return wordList

    def align_words_and_baseline(self, sent):
        """
        Fill in the offset fields for individual words in the sentence.
        """
        iSentPos = 0
        for iWord in range(len(sent['words'])):
            iWordPos = 0
            word = sent['words'][iWord]
            wf = word['wf']
            if len(wf) <= 0:
                continue
            while (iSentPos < len(sent['text'])
                   and sent['text'][iSentPos].lower() != wf[iWordPos].lower()):
                iSentPos += 1
            if iSentPos == len(sent['text']):
                word['off_start'] = len(sent['text']) - 1
                word['off_end'] = len(sent['text']) - 1
                print('Unexpected end of sentence:', sent['text'])
                return
            word['off_start'] = iSentPos
            word['off_end'] = iSentPos + len(wf)
            while iSentPos < len(sent['text']) and iWordPos < len(wf):
                if sent['text'][iSentPos].lower() == wf[iWordPos].lower():
                    iSentPos += 1
                    iWordPos += 1
                    continue
                if self.rxLetters.search(wf[iWordPos]) is None and self.rxLetters.search(sent['text'][iSentPos]) is not None:
                    iWordPos += 1
                    continue
                iSentPos += 1
            word['off_end'] = iSentPos

    def add_full_text(self, anno, curSentences, tierName='ts'):
        """
        Add full texts of the sentences from the tier requested
        (ts stands for the main text tier). Find relevant sentences
        based on the time anchors.
        Do not return anything.
        """
        seg2text = {}     # (from, to) -> sentence text
        for spanGr in anno.xpath('tei:spanGrp',
                                 namespaces=self.namespaces):
            if 'type' in spanGr.attrib and spanGr.attrib['type'] == tierName:
                for span in spanGr.xpath('tei:span',
                                         namespaces=self.namespaces):
                    if 'from' not in span.attrib or 'to' not in span.attrib:
                        continue
                    if span.attrib['from'] != span.attrib['to']:
                        self.log_message('"from" attribute != "to" attribute: '
                                         + span.attrib['from'] + '; ' + span.attrib['to'])
                    if span.attrib['from'] not in self.seg2pID:
                        self.log_message('Wrong "from" attribute: '
                                         + span.attrib['from'])
                    if span.attrib['to'] not in self.seg2pID:
                        self.log_message('Wrong "to" attribute: '
                                         + span.attrib['to'])
                    spanText = span.text
                    if spanText is None:
                        spanText = ''
                    seg2text[(self.seg2pID[span.attrib['from']],
                              self.seg2pID[span.attrib['to']])] = spanText.strip()
        for s in curSentences:
            if 'para_alignment' not in s or len(s['para_alignment']) <= 0:
                continue
            paraID = (s['para_alignment'][0]['para_id'], s['para_alignment'][0]['para_id'])
            if paraID in seg2text:
                s['text'] = seg2text[paraID]
            else:
                print(seg2text)
                print(paraID)
                print(s)

    def add_para_offsets(self, sentences):
        """
        Add character offsets to the parallel alignments of each of the sentences.
        Do not return anything.
        """
        for s in sentences:
            if 'para_alignment' not in s:
                continue
            for para in s['para_alignment']:
                para['off_start'] = 0
                para['off_end'] = len(s['text'])

    def get_sentences(self, srcTree, srcFile):
        """
        Iterate over sentences in the XML tree.
        """
        annotations = srcTree.xpath('/tei:TEI/tei:text/tei:body/tei:annotationBlock',
                                    namespaces=self.namespaces)
        if len(annotations) <= 0:
            return
        for anno in annotations:
            curSentences = []
            paraSentences = {}  # tier name -> parallel sentences (translations, alternative transcriptions, etc.)
            sentMeta = {}
            if 'start' not in anno.attrib or 'end' not in anno.attrib:
                self.log_message('No start or end attribute in annotationBlock '
                                 + anno.attrib[self.pfx_xml + 'id'])
                continue
            if 'who' in anno.attrib and anno.attrib['who'][1:] in self.participants:
                sentMeta = self.participants[anno.attrib['who'][1:]]
            prevAnchor = anno.attrib['start']
            endAnchor = anno.attrib['end']
            curSent = None
            for u in anno.xpath('tei:u', namespaces=self.namespaces):
                for seg_anchor in u:
                    if seg_anchor.tag == self.pfx_tei + 'anchor' and 'synch' in seg_anchor.attrib:
                        curAnchor = seg_anchor.attrib['synch']
                        if curSent is not None:
                            self.add_src_alignment(curSent, [prevAnchor, curAnchor], srcFile)
                        prevAnchor = curAnchor
                    elif (seg_anchor.tag == self.pfx_tei + 'seg'
                          and self.pfx_xml + 'id' in seg_anchor.attrib):
                        if curSent is not None:
                            curSentences.append(curSent)
                        self.pID += 1
                        segID = seg_anchor.attrib[self.pfx_xml + 'id']
                        self.seg2pID[segID] = self.pID
                        curSent = {'words': self.get_segment_words(seg_anchor),
                                   'text': '',
                                   'lang': 0,
                                   'para_alignment': [{'para_id': self.pID}]}
                        if len(sentMeta) > 0:
                            curSent['meta'] = copy.deepcopy(sentMeta)
                if curSent is not None:
                    curSentences.append(curSent)
            if curSent is not None:
                self.add_src_alignment(curSent, [curAnchor, endAnchor], srcFile)
            self.add_full_text(anno, curSentences)
            self.process_words(anno)
            self.add_para_offsets(curSentences)
            for tierName in self.corpusSettings['tier_languages']:
                lang = self.corpusSettings['tier_languages'][tierName]
                langID = self.corpusSettings['languages'].index(lang)
                if langID == 0:
                    continue
                paraSentences[tierName] = []
                for sent in curSentences:
                    paraSent = {'words': [],
                                'text': '',
                                'lang': langID,
                                'para_alignment': copy.deepcopy(sent['para_alignment'])}
                    if 'src_alignment' in sent:
                        paraSent['src_alignment'] = copy.deepcopy(sent['src_alignment'])
                    paraSentences[tierName].append(paraSent)
                self.add_full_text(anno, paraSentences[tierName], tierName)
            for sent in curSentences:
                if len(sent['text']) <= 0:
                    print('Zero length sentence:', sent)
                    continue
                self.align_words_and_baseline(sent)
                yield sent
            for tierName in paraSentences:
                for paraSent in paraSentences[tierName]:
                    if len(paraSent['text']) <= 0:
                        paraSent['words'] = [{'wf': '—',
                                              'wtype': 'punc',
                                              'off_start': 0,
                                              'off_end': 1}]
                        paraSent['text'] = '—'
                    else:
                        paraSent['words'] = self.tp.tokenizer.tokenize(paraSent['text'])
                    paraSent['para_alignment'][0]['off_end'] = len(paraSent['text'])
                    yield paraSent

    def convert_file(self, fnameSrc, fnameTarget):
        """
        Take one source Exmaralda file fnameSrc, parse the XML tree,
        extract timestamps, align sentences with words and their
        analyses and ultimately generate a parsed JSON file
        ready for indexing. Write the output to fnameTarget.
        Return number of tokens, number of words and number of
        words with at least one analysis in the document.
        """
        # curMeta = self.get_meta(fnameSrc)
        # Currently, no metadata are loaded:
        curMeta = {'title': fnameSrc, 'author': '', 'year1': '1900', 'year2': '2017'}

        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyze = 0, 0, 0
        self.seg2pID = {}
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        self.participants = self.load_speaker_meta(srcTree)
        srcFileNode = srcTree.xpath('/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:recordingStmt/tei:recording/tei:media',
                                    namespaces=self.namespaces)
        if len(srcFileNode) > 0 and self.pfx_tei + 'url' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', srcFileNode[0].attrib[self.pfx_tei + 'url'])
        else:
            srcFile = ''
        textJSON['sentences'] = [s for s in self.get_sentences(srcTree, srcFile)]
        textJSON['sentences'].sort(key=lambda s: s['lang'])
        for i in range(len(textJSON['sentences']) - 1):
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyze

    def process_corpus(self):
        """
        Take every Exmaralda file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        Split all the corpus media files into overlapping chunks of
        small duration.
        This is the main function of the class.
        """
        Txt2JSON.process_corpus(self)
        for path, dirs, files in os.walk(os.path.join(self.corpusSettings['corpus_dir'],
                                                      self.srcExt)):
            for fname in files:
                fileExt = os.path.splitext(fname.lower())[1]
                if fileExt in self.mediaExtensions:
                    fname = os.path.abspath(os.path.join(path, fname))
                    print('Cutting media file', fname)
                    self.mc.cut_media(fname)


if __name__ == '__main__':
    x2j = ISO_TEI_Hamburg2JSON()
    x2j.process_corpus()


import os
import re
import json
import copy
import datetime
from lxml import etree
from txt2json import Txt2JSON
from media_operations import MediaCutter


class ISO_TEI_Hamburg2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from transcriptions
    aligned in Exmaralda in the format used in documentation projects
    carried out in Hamburg and then translated into a certain ISO TEI subset.
    """

    rxBracketGloss = re.compile('[.-]?\\[.*?\\]')
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

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'xml'  # extension of the source files to be converted
        self.participants = {}   # participant ID -> dictionary of properties
        self.tlis = {}       # time labels (id -> {'n': number, 'time': time value})
        self.wordsByID = {}  # word ID -> word object
        self.morph2wordID = {}   # morph ID -> (word ID, position in the word)
        self.pID = 0         # id of last aligned segment
        self.seg2pID = {}    # ids of <seg> tags -> parallel IDs of corresponding sentences
        self.wordIDseq = []  # sequence of word/punctuation/incident IDs
                             # (needed to understand ranges such as "w13 to inc2")
        self.glosses = set()
        self.posRules = {}
        self.load_pos_rules(os.path.join(self.settingsDir, 'posRules.txt'))

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
                self.log_message('The speaker metadata file not found.')
        else:
            for speaker in srcTree.xpath('/tei:TEI/tei:teiHeader/tei:profileDesc/tei:particDesc/tei:person',
                                         namespaces=self.namespaces):
                if self.pfx_xml + 'id' not in speaker.attrib:
                    continue
                speakerID = speaker.attrib[self.pfx_xml + 'id']
                if 'n' in speaker.attrib:
                    speakerCode = speaker.attrib['n']
                else:
                    speakerCode = speakerID
                speakerMeta[speakerID] = {'speaker': speakerCode}
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

    def id_range2list(self, idFrom, idTo):
        """
        Turn a range of word/punctuation/incident (such as "w13 to inc2") IDs into a list
        of consecutive IDs.
        """
        if idFrom not in self.wordIDseq or idTo not in self.wordIDseq:
            return []
        return self.wordIDseq[self.wordIDseq.index(idFrom):self.wordIDseq.index(idTo) + 1]

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
                spanIDs = [wSpan.attrib['from']]
                wSpanTexts = [wSpan.text]
                if wSpan.attrib['from'] != wSpan.attrib['to']:
                    # continue
                    if (wSpan.attrib['from'].startswith(('w', 'pc', 'inc'))
                            and wSpan.attrib['to'].startswith(('w', 'pc', 'inc'))):
                        # Some tiers, such as information structure, allow spans that include
                        # multiple words. In this case, assign the value to each of the words
                        # in the span in case of annotation tiers. However, if the tier is
                        # SpeakerContribution_Event, try to split it into words so that each
                        # word gets a corresponding part of the value.
                        if tierID == 'SpeakerContribution_Event' and wSpan.text is not None:
                            wSpanParts = re.findall('[^ ]+ *', wSpan.text)
                            wSpanTexts = []
                        iSpanPart = 0
                        spanIDs = self.id_range2list(wSpan.attrib['from'], wSpan.attrib['to'])
                        for wID in spanIDs:
                            if tierID == 'SpeakerContribution_Event' and wSpan.text is not None:
                                if iSpanPart < len(wSpanParts):
                                    wSpanTexts.append(wSpanParts[iSpanPart])
                                else:
                                    wSpanTexts.append('')
                                iSpanPart += 1
                            else:
                                wSpanTexts.append(wSpan.text)
                        if wSpan.text is not None:
                            self.log_message('Warning: span[from] = ' + wSpan.attrib['from']
                                             + ', span[to] = ' + wSpan.attrib['to']
                                             + ', text = "' + wSpan.text + '".')
                        else:
                            self.log_message('Warning: span[from] = ' + wSpan.attrib['from']
                                             + ', span[to] = ' + wSpan.attrib['to']
                                             + ', text is empty.')
                    else:
                        continue
                for spanID in spanIDs:
                    wSpanText = wSpanTexts.pop(0)
                    if spanID.startswith('seg'):
                        continue
                    elif spanID.startswith('w'):
                        wordID = spanID
                    elif spanID.startswith('inc'):
                        wordID = spanID
                    elif spanID.startswith('m'):
                        wordID = self.morph2wordID[spanID][0]
                    else:
                        continue
                    if wordID != prevWordID:
                        prevWordID = wordID
                        curWordNMorphs = 0
                    if wordID not in wordAnno:
                        wordAnno[wordID] = {}
                    if self.pfx_xml + 'id' in wSpan.attrib:
                        self.morph2wordID[wSpan.attrib[self.pfx_xml + 'id']] = (wordID, curWordNMorphs)
                        curWordNMorphs += 1
                        if wSpanText is not None:
                            wordAnno[wordID][tierID] = wSpanText
                        else:
                            wordAnno[wordID][tierID] = ''
                    elif tierID not in ['mb', 'mp', 'ge', 'gr', 'gg']:
                        # Word-based annotations: one flat span for each word
                        if tierID not in wordAnno[wordID]:
                            wordAnno[wordID][tierID] = ''
                        if len(wordAnno[wordID][tierID]) > 0:
                            if (wSpanText is not None
                                    and wSpanText.startswith('[') and wSpanText.endswith(']')):
                                wordAnno[wordID][tierID] += '.'
                            else:
                                wordAnno[wordID][tierID] += '-'
                        if wSpanText is not None:
                            wordAnno[wordID][tierID] += wSpanText
                    else:
                        # Multiple morphemes inside one span in e.g. the mb tier
                        wordAnno[wordID][tierID] = ''
                        for mSpan in wSpan:
                            mText = mSpan.text
                            if self.pfx_xml + 'id' in mSpan.attrib:
                                mID = mSpan.attrib[self.pfx_xml + 'id']
                            elif ('from' in mSpan.attrib and 'to' in mSpan.attrib
                                  and mSpan.attrib['from'] == mSpan.attrib['to']):
                                mID = mSpan.attrib['from']
                            else:
                                # continue
                                mID = wordID + '_covert'    # categories not expressed overtly
                                if mText is None:
                                    self.log_message('Empty morpheme description cell: word ID ' +
                                                     wordID + ', tier ' + tierID + '.')
                                    continue
                                mText = '[' + mText + ']'
                                # if 'mb' not in wordAnno[wordID]:
                                #     wordAnno[wordID]['mb'] = '∅'
                                # elif mID not in self.morph2wordID:
                                #     wordAnno[wordID]['mb'] += '-∅'
                                # if 'mp' not in wordAnno[wordID]:
                                #     wordAnno[wordID]['mp'] = '∅'
                                # elif mID not in self.morph2wordID:
                                #     wordAnno[wordID]['mp'] += '-∅'
                            self.morph2wordID[mID] = (wordID, curWordNMorphs)
                            curWordNMorphs += 1
                            if tierID not in wordAnno[wordID]:
                                wordAnno[wordID][tierID] = ''
                            if len(wordAnno[wordID][tierID]) > 0:
                                if (mText is not None
                                        and mText.startswith('[') and mText.endswith(']')):
                                    wordAnno[wordID][tierID] += '.'
                                else:
                                    wordAnno[wordID][tierID] += '-'
                            if mText is not None:
                                wordAnno[wordID][tierID] += mText
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
            if tierName in ['tx', 'mb', 'mp', 'gr', 'ge', 'gg', 'ps', 'SpeakerContribution_Event']:
                continue
            elif len(curWordAnno[tierName]) > 0:
                ana[tierName] = curWordAnno[tierName]

    def process_words(self, annoTree):
        """
        Iterate over words in an annotation block and add their
        analyses to the corresponding word objects in the sentences.
        """
        useGlossList = False
        if 'glosses' in self.corpusSettings and len(self.corpusSettings['glosses']) > 0:
            useGlossList = True
        wordAnno = self.collect_annotation(annoTree)
        for wordID in wordAnno:
            ana = {}
            curWordAnno = wordAnno[wordID]
            # mp: morph breaks with empty morphemes (corresponds to the mc tier: POS and morph categories)
            # mb: morph breaks without empty morphemes (corresponds to the gr/ge tiers: actual glosses)
            if 'ge' in curWordAnno:
                ana['gloss'] = curWordAnno['ge']
                self.glosses |= set(g for g in ana['gloss'].split('-') if g.upper() == g)
            if 'mp' in curWordAnno:
                # mp contains normalized versions of morphemes. If this tier exists,
                # take normalized stem from it and make it a lemma. Then forget mp
                # and write glosses based on the mb tier, if it exists.
                ana['parts'] = curWordAnno['mp']
                self.tp.parser.process_gloss_in_ana(ana)
                if 'gloss_index' in ana:
                    stems, newIndexGloss = self.tp.parser.find_stems(ana['gloss_index'],
                                                                     self.corpusSettings['languages'][0])
                    ana['lex'] = ' '.join(s[1] for s in stems)
            if 'mb' in curWordAnno:
                ana['parts'] = curWordAnno['mb']
            if 'gr' in curWordAnno:
                ana['gloss_ru'] = curWordAnno['gr']
                self.tp.parser.process_gloss_in_ana(ana, 'ru')
            if 'gg' in curWordAnno:
                ana['gloss_de'] = curWordAnno['gg']
                self.tp.parser.process_gloss_in_ana(ana, 'de')
            if 'ps' in curWordAnno:
                self.add_pos_ana(ana, curWordAnno['ps'])
            self.tp.parser.process_gloss_in_ana(ana)
            if 'gloss_index' in ana:
                stems, newIndexGloss = self.tp.parser.find_stems(ana['gloss_index'],
                                                                 self.corpusSettings['languages'][0])
                if 'lex' not in ana:
                    ana['lex'] = ' '.join(s[1] for s in stems)
                ana['trans_en'] = self.rxBracketGloss.sub('', ' '.join(s[0] for s in stems))
                self.add_ana_fields(ana, curWordAnno)
                self.tp.parser.gloss2gr(ana, self.corpusSettings['languages'][0],
                                        useGlossList=useGlossList)
                ana['gloss_index'] = self.rxBracketGloss.sub('', newIndexGloss)
            for glossLang in ('ru', 'de'):
                if 'gloss_index_' + glossLang in ana:
                    stems, newIndexGloss = self.tp.parser.find_stems(ana['gloss_index_' + glossLang],
                                                                     self.corpusSettings['languages'][0])
                    ana['trans_' + glossLang] = self.rxBracketGloss.sub('', ' '.join(s[0] for s in stems))
                    del ana['gloss_index_' + glossLang]
                    del ana['gloss_' + glossLang]
                    if 'glosses_covert_' + glossLang in ana:
                        del ana['glosses_covert_' + glossLang]
            if ('replace_bracketed_glosses' in self.corpusSettings
                    and self.corpusSettings['replace_bracketed_glosses']
                    and 'gloss' in ana):
                ana['gloss'] = self.rxBracketGloss.sub('', ana['gloss'])
            self.wordsByID[wordID]['ana'] = [ana]
            self.wordsByID[wordID]['word_source'] = ''
            if 'SpeakerContribution_Event' in curWordAnno:
                self.wordsByID[wordID]['word_source'] = curWordAnno['SpeakerContribution_Event']

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
        prevTag = ''
        for wordNode in segment:
            if wordNode in (self.pfx_tei + 'w', self.pfx_tei + 'pc') and self.pfx_xml + 'id' not in wordNode.attrib:
                continue
            try:
                wordID = wordNode.attrib[self.pfx_xml + 'id']
            except KeyError:
                continue
            if wordNode.tag == self.pfx_tei + 'w':
                # if prevTag == self.pfx_tei + 'w' and len(wordList) > 0:
                #     # If there is no time anchor between two words,
                #     # treat it as a single token divided by a word-internal whitespace.
                #     # TODO: This is a temporary solution. Changes have to be made
                #     # to the source Exmaralda files to avoid splitting such words.
                #     wordList[-1]['wf'] += ' ' + wordNode.text.strip()
                #     self.wordsByID[wordNode.attrib[self.pfx_xml + 'id']] = wordList[-1]
                #     print('Warning: consecutive words with no acnhor between them (' + wordList[-1]['wf'] + ')')
                # else:
                word = {'wf': wordNode.text.strip(), 'wtype': 'word'}
                wordList.append(word)
                self.wordsByID[wordID] = word
                self.wordIDseq.append(wordID)
            elif wordNode.tag == self.pfx_tei + 'pc':
                word = {'wf': wordNode.text.strip(), 'wtype': 'punct'}
                wordList.append(word)
                self.wordsByID[wordID] = word
            elif wordNode.tag == self.pfx_tei + 'incident':
                # Treat "incidents" as punctuation
                # continue
                word = {'wf': '((' + wordNode[0].text.strip() + '))', 'wtype': 'punct', 'incident': True}
                wordList.append(word)
                self.wordsByID[wordID] = word
                self.wordIDseq.append(wordID)
            prevTag = wordNode.tag
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
            # if 'incident' in word:
            #     sent['text'] = sent['text'][:iSentPos] + ' ' + wf + ' ' + sent['text'][iSentPos:]
            while (iSentPos < len(sent['text'])
                   and sent['text'][iSentPos].lower() != wf[iWordPos].lower()):
                iSentPos += 1
            if iSentPos == len(sent['text']):
                if iWord == 0 and word['wtype'] == 'punct':
                    # Try repairing it by inserting that punctuation to the sentence text
                    sent['text'] = wf + sent['text']
                    iSentPos = 0
                    print('Unexpected end of sentence, attempting to repair sentence text. '
                          'Details:\nSentence (SpeakerContribution_Event):', sent['text'],
                          '\nWords (annotationBlock/u/seg):',
                          '+'.join(w['wf'] for w in sent['words']))
                else:
                    for iWordRest in range(iWord, len(sent['words'])):
                        sent['words'][iWordRest]['off_start'] = len(sent['text']) - 1
                        sent['words'][iWordRest]['off_end'] = len(sent['text']) - 1
                    word['off_end'] = len(sent['text']) - 1
                    print('Unexpected end of sentence, terminating alignment now. '
                          'Details:\nSentence (SpeakerContribution_Event):', sent['text'],
                          '\nWords (annotationBlock/u/seg):', '+'.join(w['wf'] for w in sent['words']))
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
        if len(sent['words']) > 0 and sent['words'][0]['off_start'] > 0:
            # Add the beginning of the sentence as punctuation.
            leadingPunct = {'wf': sent['text'][:sent['words'][0]['off_start']],
                            'wtype': 'punct',
                            'off_start': 0,
                            'off_end': sent['words'][0]['off_start']}
            sent['words'].insert(0, leadingPunct)

    def add_full_text(self, anno, curSentences, tierName=''):
        """
        Add full texts of the sentences from the tier requested
        (ts stands for the main text tier). Find relevant sentences
        based on the time anchors. If there is no such
        tier, restore the text of the sentence from the word_source
        properties of individual words. 
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
                        continue
                    if span.attrib['to'] not in self.seg2pID:
                        self.log_message('Wrong "to" attribute: '
                                         + span.attrib['to'])
                        continue
                    spanText = span.text
                    if spanText is None:
                        spanText = ''
                    seg2text[(self.seg2pID[span.attrib['from']],
                              self.seg2pID[span.attrib['from']])] = spanText.strip()
        for s in curSentences:
            if 'para_alignment' not in s or len(s['para_alignment']) <= 0:
                continue
            paraID = (s['para_alignment'][0]['para_id'], s['para_alignment'][0]['para_id'])
            if 'text' not in s:
                s['text'] = ''
            if paraID in seg2text:
                s['text'] += seg2text[paraID]
            else:
                for w in s['words']:
                    if 'word_source' in w:
                        s['text'] += w['word_source']
                        del w['word_source']
                s['text'] = s['text'].strip(' \t')
            if 'src_alignment' in s:
                for sa in s['src_alignment']:
                    sa['off_end_sent'] = len(s['text'])

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
            firstSentence = False
            if len(annotations) > 1:
                firstSentence = True
            curSentences = []
            paraSentences = {}  # tier name -> parallel sentences (translations, alternative transcriptions, etc.)
            sentMeta = {}
            if 'start' not in anno.attrib or 'end' not in anno.attrib:
                self.log_message('No start or end attribute in annotationBlock '
                                 + anno.attrib[self.pfx_xml + 'id'])
                continue
            if 'who' in anno.attrib and anno.attrib['who'] in self.participants:
                sentMeta = self.participants[anno.attrib['who']]
            curAnchor = prevAnchor = anno.attrib['start']
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
                        if firstSentence and 'who' in anno.attrib and anno.attrib['who'] in self.participants:
                            firstSentence = False
                            curSent['words'].insert(0, {'wtype': 'punct',
                                                        'wf': '[' + self.participants[anno.attrib['who']]['speaker'] + ']'})
                            curSent['words'].insert(0, {'wtype': 'punct', 'wf': '\n'})
                            curSent['text'] = '\n[' + self.participants[anno.attrib['who']]['speaker'] + '] '
                        if len(sentMeta) > 0:
                            curSent['meta'] = copy.deepcopy(sentMeta)
                if curSent is not None:
                    curSentences.append(curSent)
            if curSent is not None:
                self.add_src_alignment(curSent, [curAnchor, endAnchor], srcFile)
            self.process_words(anno)
            self.add_full_text(anno, curSentences)
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
                    self.log_message('Zero length sentence: ' + json.dumps(sent, ensure_ascii=False, indent=None))
                    continue
                self.align_words_and_baseline(sent)
                yield sent
            for tierName in paraSentences:
                for paraSent in paraSentences[tierName]:
                    if len(paraSent['text']) <= 0:
                        paraSent['words'] = [{'wf': '—',
                                              'wtype': 'punct',
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
        print(fnameSrc)
        curMeta = self.get_meta(fnameSrc)
        if len(curMeta) == 1:
            curMeta = {'filename': fnameSrc, 'title': fnameSrc, 'author': '',
                       'year_from': '1900', 'year_to': str(datetime.datetime.now().year)}

        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        self.seg2pID = {}
        self.morph2wordID = {}
        self.wordIDseq = []
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        self.participants = self.load_speaker_meta(srcTree)
        srcFileNode = srcTree.xpath('/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:recordingStmt/tei:recording/tei:media',
                                    namespaces=self.namespaces)
        if len(srcFileNode) > 0 and 'url' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', srcFileNode[0].attrib['url'])
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
        for s in textJSON['sentences']:
            for word in s['words']:
                nTokens += 1
                if word['wtype'] == 'word':
                    nWords += 1
                    if 'ana' in word and len(word['ana']) > 0:
                        nAnalyzed += 1
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
                    fname = os.path.abspath(os.path.join(path, fname))
                    print('Cutting media file', fname)
                    self.mc.cut_media(fname)


if __name__ == '__main__':
    x2j = ISO_TEI_Hamburg2JSON()
    x2j.process_corpus(cutMedia=False)


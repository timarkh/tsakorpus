import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON


class Exmaralda_Hamburg2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from aligned
    Exmaralda files in the format used in documentation projects
    carried out in Hamburg.
    """

    rxBracketGloss = re.compile('\\.?\\[.*?\\]')
    rxWordPunc = re.compile('^( *)([^\\w]*)(.*?)([^\\w]*?)( *)$')

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'exb'
        self.tlis = {}      # time labels
        self.pID = 0        # id of last aligned segment
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
        boundaries = []
        for event in refTier:
            if 'start' not in event.attrib or 'end' not in event.attrib:
                continue
            sentStart, sentEnd = event.attrib['start'], event.attrib['end']
            if sentStart not in self.tlis or sentEnd not in self.tlis:
                continue
            boundaries.append((sentStart, sentEnd))
        return boundaries

    def collect_annotation(self, srcTree):
        """
        Return a dictionary that contains all word-level annotation events,
        the keys are tuples (start time label, end time label).
        """
        wordAnno = {}
        for tier in srcTree.xpath('/basic-transcription/basic-body/tier[@type=\'a\']'):
            if 'id' not in tier.attrib:
                continue
            tierID = tier.attrib['id']
            for event in tier:
                if 'start' not in event.attrib or 'end' not in event.attrib:
                    continue
                tupleKey = (event.attrib['start'], event.attrib['end'])
                if tupleKey not in wordAnno:
                    wordAnno[tupleKey] = {}
                if event.text is not None:
                    wordAnno[tupleKey][tierID] = event.text
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
        txTier = srcTree.xpath('/basic-transcription/basic-body/tier[@id=\'tx\']')
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
            if 'mp' in curWordAnno:
                ana['parts'] = curWordAnno['mp']
            if 'ge' in curWordAnno:
                ana['gloss'] = curWordAnno['ge']
                self.glosses |= set(g for g in ana['gloss'].split('-') if g.upper() == g)
            self.tp.parser.process_gloss_in_ana(ana)
            if 'gloss_index' in ana:
                stems, newIndexGloss = self.tp.parser.find_stems(ana['gloss_index'],
                                                                 self.corpusSettings['languages'][0])
                ana['lex'] = ' '.join(s[1] for s in stems)
                ana['trans_en'] = self.rxBracketGloss.sub('', ' '.join(s[0] for s in stems))
                self.add_ana_fields(ana, curWordAnno)
                self.tp.parser.gloss2gr(ana, self.corpusSettings['languages'][0])
                ana['gloss_index'] = self.rxBracketGloss.sub('', newIndexGloss)
            curToken['ana'] = [ana]
            yield curToken

    def get_parallel_sentences(self, srcTree, sentBoundaries):
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
                    continue
                text = self.tp.cleaner.clean_text(text)
                words = self.tp.tokenizer.tokenize(text)
                paraAlignment = {'off_start': 0, 'off_end': len(text), 'para_id': self.pID}
                yield {'words': words, 'text': text, 'para_alignment': [paraAlignment],
                       'lang': len(self.corpusSettings['languages']) + iTier}

    def get_sentences(self, srcTree):
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
                yield curSent
                curSent = {'text': '', 'words': [], 'lang': 0}
                for paraSent in self.get_parallel_sentences(srcTree, sentBoundaries[curSentIndex]):
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
            yield curSent

    def convert_file(self, fnameSrc, fnameTarget):
        # curMeta = self.get_meta(fnameSrc)
        curMeta = {'title': fnameSrc, 'author': '', 'year1': '1900', 'year2': '2017'}
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyze = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        textJSON['sentences'] = [s for s in self.get_sentences(srcTree)]
        textJSON['sentences'].sort(key=lambda s: s['lang'])
        for i in range(len(textJSON['sentences']) - 1):
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyze


if __name__ == '__main__':
    x2j = Exmaralda_Hamburg2JSON()
    x2j.process_corpus()
    # glosses = set()
    # for g in x2j.glosses:
    #     if '[' not in g:
    #         glosses.add(g)
    #     else:
    #         m = re.search('^([^\\[\\]]*)\\[(.*?)\\]', g)
    #         if m is None:
    #             print(g)
    #             continue
    #         glosses.add(m.group(1))
    #         for gp in m.group(2).split('.'):
    #             glosses.add(gp)
    # print(', '.join('"' + g + '"' for g in sorted(glosses)))

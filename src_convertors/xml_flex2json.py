import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON


class Xml_Flex2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from manually
    glossed Fieldworks FLEX XML and a csv with metadata.
    """

    rxSplitParts = re.compile(u'(?:^|[-=])[^-=]+|<[^<>]+>')
    rxFindStem = re.compile(u'[-.=]?[{(‹][A-Z0-9.-:]+[})›][-.=]?|[-=.:][A-Z0-9]+$|^[=-]')

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'xml'
        self.pID = 0        # id of last aligned segment
        self.glosses = []
        self.grammRules = []
        self.posRules = {}
        self.load_rules()
        self.POSTags = set()    # All POS tags encountered in the XML
    
    def load_rules(self):
        """
        Load rules for converting the glosses into bags of grammatical
        tags.
        """
        self.load_glosses(os.path.join(self.corpusSettings['corpus_dir'], 'glossList.txt'))
        self.load_gram_rules(os.path.join(self.corpusSettings['corpus_dir'], 'gramRules.txt'))
        self.load_pos_rules(os.path.join(self.corpusSettings['corpus_dir'], 'posRules.txt'))
    
    def load_glosses(self, fname):
        """
        Load gloss list.
        """
        f = open(fname, 'r', encoding='utf-8-sig')
        glosses = set()
        for line in f:
            line = line.strip()
            if len(line) > 0:
                for i in ['-', '=', '.', '‹', '›', '{', '}', '']:
                    for j in ['-', '=', '.', '‹', '›', '{', '}', '']:
                        glosses.add(i + line + j)
        f.close()
        self.glosses = glosses

    @staticmethod
    def prepare_rule(rule):
        """
        Make a compiled regex out of a rule represented as a string.
        """
        def replReg(s):
            if "'" in s:
                return ''
            return ' re.search(\'' + s +\
                   '\', self.parts) is not None or ' +\
                   're.search(\'' + s +\
                   '\', self.gloss) is not None '
        ruleParts = rule.split('"')
        rule = ''
        for i in range(len(ruleParts)):
            if i % 2 == 0:
                rule += re.sub('([^\\[\\]~|& \t\']+)', ' \'\\1\' in (self.grdic.split() + self._glossList) ',
                               ruleParts[i]).replace('|', ' or ').replace('&', ' and ')\
                                            .replace('~', ' not ').replace('[', '(').replace(']', ')')
            else:
                rule += replReg(ruleParts[i])
        return rule

    def load_gram_rules(self, fname):
        """
        Load main set of rules for converting the glosses into bags
        of grammatical tags.
        """
        rules = []
        f = open(fname, 'r', encoding='utf-8-sig')
        for line in f:
            line = line.strip()
            if len(line) > 0:
                rule = [i.strip() for i in line.split('->')]
                if len(rule) != 2:
                    continue
                rule[1] = set(rule[1].split(','))
                rule[0] = self.prepare_rule(rule[0])
                rules.append(rule)
        f.close()
        self.grammRules = rules

    def load_pos_rules(self, fname):
        """
        Load mapping of the FLEX POS tags to your corpus POS tags.
        """
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

    def process_stem(self, stem, stemGloss, anaJSON, curGlossList):
        """
        Add the lemma and its translation.
        """
        if stem[0] in '-=':
            stem = stem[1:]
        anaJSON['lex'] = stem
        if len(stemGloss) > 0 and stemGloss[0] in '-=':
            stemGloss = stemGloss[1:]
        anaJSON['trans_en'] = stemGloss
        pureStem = self.regFindStem.sub('', anaJSON['lex'])
        pureTrans = self.regFindGlossRu.sub('', anaJSON['trans_en'])
        if pureTrans != anaJSON['trans_en']:
            anaJSON['gloss'] += \
                '[' + '[STEM]'.join(self.rxFindStem.findall(anaJSON['trans_en'])) + ']'
            curGlossList += [g.strip('-=:.‹›{}')
                             for g in self.regStemGlosses.findall(anaJSON['trans_en'])]
            anaJSON['trans_en'] = pureTrans
            anaJSON['lex'] = pureStem
        else:
            anaJSON['gloss'] += '[STEM]'
        # TODO: different gloss languages

    def ana_from_gls(self, glsNode, parts):
        """
        Make and return a JSON analysis out of the glossing in the gls node
        and the segmentation into morphs.
        """
        # TODO: Not ready yet!
        if glsNode.text is None or len(glsNode.text) <= 0 or len(parts) <= 0:
            return {}
        anaJSON = {'parts': '', 'gloss': ''}
        curGlossList = []
        parts = parts.replace('', '=')
        glosses = glsNode.text.strip()
        partsList = self.rxSplitParts.findall(parts)
        glossesList = self.rxSplitParts.findall(glosses)
        for i in range(min(len(partsList), len(glossesList))):
            if glossesList[i] in self.glossList \
                    or re.search('^[-=<>0-9A-Z.:,()\\[\\]]+$', glossesList[i]) is not None:
                anaJSON['gloss'] += glossesList[i]
                curGlossList.append(glossesList[i].strip('-=:.'))
            else:
                self.process_stem(partsList[i], glossesList[i], anaJSON, curGlossList)

    def ana_from_morphemes(self, mNode, parts):
        """
        Make and return a JSON analysis out of the glossing in the morphemes
        node.
        """
        # TODO: Not ready yet!
        anaJSON = {'parts': '', 'gloss': ''}
        curGlossList = []
        for morph in mNode:
            if morph.tag != 'morph':
                continue
            if 'type' not in morph.attrib:
                continue    # TODO: that other format
            morphType = morph.attrib['type']
            for element in morph:
                if element.tag == 'item' and 'type' in element.attrib:
                    if element.attrib['type'] in ['mb', 'txt']:
                        if element.text is None:
                            element.text = ' '
                        anaJSON['parts'] += element.text
                        lastPart = element.text
                    elif element.attrib['type'] == 'gls':
                        if ('lang' in element.attrib
                                and element.attrib['lang'] in self.corpusSettings['bad_analysis_languages']):
                            continue
                        if element.text is None:
                            element.text = ' '
                        gloss = element.text
                        if (morphType == 'stem'
                                or (morphType == 'unknown' and element.text not in self.glossList)):
                            self.process_stem(lastPart, element.text, anaJSON, curGlossList)
                        else:
                            if (morphType == 'prefix' and len(gloss) > 0
                                    and gloss[-1] not in '-=:.'):
                                gloss += '-'
                            elif (morphType == 'suffix' and len(gloss) > 0
                                    and gloss[0] not in '-=:.'):
                                gloss = '-' + gloss
                            elif (morphType == 'enclitic' and len(gloss) > 0
                                    and gloss[0] not in '-=:.'):
                                gloss = '=' + gloss
                            elif (morphType == 'proclitic' and len(gloss) > 0
                                    and gloss[-1] not in '-=:.'):
                                gloss += '='
                            self._glossWithoutStem += gloss
                            curGlossList.append(gloss.strip('-=:.'))
                        anaJSON['gloss'] += gloss
                    elif element.attrib['type'] == 'msa' and morphType == 'stem':
                        if element.text is None:
                            element.text = ' '
                        grdic = element.text.strip().replace('.', ' ')
                        self.POSTags.add(grdic)
                        if grdic in self.posRules:
                            grdic = self.posRules[grdic]
                        if len(self.grdic) > 0:
                            self.grdic += ' '
                        self.grdic += grdic

    def process_word_node(self, wordNode):
        """
        Extract one token from an XML node and return it
        as a JSON.
        """
        if (len(wordNode) == 1 and 'type' in wordNode[0].attrib
                and wordNode[0].attrib['type'] == 'punct'):
            return {'wtype': 'punct', 'wf': wordNode[0].text}
        wordJSON = {'wtype': 'word', 'wf': ''}
        wordPos = ''
        for el in wordNode:
            if el.tag not in ['item', 'morphemes']:
                continue
            elif 'type' in wordNode[0].attrib and wordNode[0].attrib['type'] == 'punctl':
                yield {'wtype': 'punctl', 'wf': wordNode[0].text}
                continue
            elif 'type' in wordNode[0].attrib and wordNode[0].attrib['type'] == 'punctr':
                yield {'wtype': 'punctr', 'wf': wordNode[0].text}
                continue
            if el.tag == 'morphemes':
                if 'ana' not in wordJSON:
                    wordJSON['ana'] = []
                wordJSON['ana'].append(self.ana_from_morphemes(el))
                continue
            if 'type' not in el.attrib:
                continue
            if el.attrib['type'] == 'txt':
                wordJSON['wf'] = el.text
            elif el.attrib['type'] == 'gls':
                # This means that the word form contains morph breaks
                if 'ana' not in wordJSON:
                    wordJSON['ana'] = []
                wordJSON['ana'].append(self.ana_from_gls(el, wordJSON['wf']))
                wordJSON['wf'] = re.sub('[-=<>∅]', '', wordJSON['wf'])
            elif el.attrib['type'] == 'pos':
                wordPos = el.text.strip()
                if wordPos in self.posRules:
                    wordPos = self.posRules[wordPos]
            # TODO: nt
        if wordPos != '' and 'ana' in wordJSON and len(wordJSON['ana']) > 0:
            for ana in wordJSON['ana']:
                ana['gr.pos'] = wordPos
        yield wordJSON

    @staticmethod
    def restore_sentence_text(words):
        """
        Restore sentence text as a string based on a list
        of JSON words it consists of. Indert start and end
        offset in each JSON word. Return the text of the
        sentence.
        """
        text = ''
        for word in words:
            if 'wf' not in word:
                continue
            word['off_start'] = len(text)
            if word['wtype'] == 'word':
                text += word['wf'] + ' '
                word['off_end'] = len(text) - 1
            elif word['wtype'] == 'punctl':
                text += word['wf']
                word['wtype'] = 'punct'
                word['off_end'] = len(text)
            elif word['wtype'] == 'punctr':
                if text.endswith(' '):
                    word['off_start'] -= 1
                    text = text[:-1]
                text += word['wf'] + ' '
                word['wtype'] = 'punct'
                word['off_end'] = len(text) - 1
            else:
                if word['wf'].startswith(('(', '[', '{', '<')):
                    text += word['wf']
                    word['off_end'] = len(text)
                elif word['wf'].startswith((')', ']', '}', '>')):
                    if text.endswith(' '):
                        word['off_start'] -= 1
                        text = text[:-1]
                    text += word['wf']
                    word['off_end'] = len(text)
                else:
                    text += word['wf'] + ' '
                    word['off_end'] = len(text) - 1
        return text.strip()

    def process_se_node(self, se):
        """
        Extract data from one sentence node. Iterate over
        sentences in this node (there can be multiple sentences
        if there are translations of the original sentence).
        """
        seNum = ''
        seTrans = {}
        seComment = ''
        self.pID += 1
        for element in se:
            if element.tag == 'item' and 'type' in element.attrib:
                if element.attrib['type'] in ['ref', 'segnum']:
                    seNum = element.text
                elif element.attrib['type'] in ['ft', 'lt', 'gls'] and\
                        'lang' in element.attrib and\
                        re.sub('-.*', '', element.attrib['lang']) in self.corpusSettings['language_codes']:
                    transLang = self.corpusSettings['language_codes'][re.sub('-.*', '', element.attrib['lang'])]
                    if element.text is not None:
                        seTrans[transLang] = element.text
                    elif transLang not in seTrans:
                        seTrans[transLang] = ''
                elif element.attrib['type'] == 'nt':
                    seComment = element.text
        words = [{'wtype': 'punct', 'wf': seNum + '.'}]
        words += [w for wn in se.xpath('words/word')
                  for w in self.process_word_node(wn)]
        seText = self.restore_sentence_text(words)
        paraAlignment = {'off_start': 0, 'off_end': len(seText), 'para_id': self.pID}
        yield {'lang': 0, 'words': words, 'text': seText, 'para_alignment': [paraAlignment]}
        
        for lang in seTrans:
            langID = self.corpusSettings['languages'].index(lang)
            transText = self.tp.cleaner.clean_text(seTrans[lang])
            words = self.tp.tokenizer.tokenize(transText)
            paraAlignment = {'off_start': 0, 'off_end': len(transText), 'para_id': self.pID}
            yield {'lang': langID, 'words': words, 'text': transText, 'para_alignment': [paraAlignment]}

    def convert_file(self, fnameSrc, fnameTarget):
        nTokens, nWords, nAnalyze = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        interlinears = srcTree.xpath('/document/interlinear-text')
        nDoc = 0
        for interlinear in interlinears:
            curFnameTarget = re.sub('(\\.[^.]*$)', '-' + str(nDoc) + '\\1', fnameTarget)
            nDoc += 1
            titleNode = interlinear.xpath('./title')
            curMeta = {}
            title = ''
            if len(titleNode) > 0:
                title = etree.tostring(titleNode[0], encoding='unicode')
                curMeta = self.get_meta(fnameSrc)
            if len(curMeta) <= 1:
                curMeta = {'title': title, 'filename': fnameSrc}
            textJSON = {'meta': curMeta, 'sentences': []}
            textJSON['sentences'] = [s for sNode in interlinear.xpath('./paragraphs/paragraph/phrases/phrase | ./paragraphs/paragraph/phrases/word')
                                     for s in self.process_se_node(sNode)]
            textJSON['sentences'].sort(key=lambda s: s['lang'])
            for i in range(len(textJSON['sentences']) - 1):
                if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                    textJSON['sentences'][i]['last'] = True
            self.tp.splitter.recalculate_offsets(textJSON['sentences'])
            self.tp.splitter.add_next_word_id(textJSON['sentences'])
            self.write_output(curFnameTarget, textJSON)
        return nTokens, nWords, nAnalyze


if __name__ == '__main__':
    x2j = Xml_Flex2JSON()
    x2j.process_corpus()

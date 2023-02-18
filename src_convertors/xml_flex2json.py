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
    rxFindGloss = re.compile(u'[-.=]?[{(][A-Z0-9a-z]+[})][-.=]?|[-=.:][A-Z0-9a-z]+$|^[=-]')

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'xml'
        self.pID = 0        # id of last aligned segment
        self.glosses = []
        self.grammRules = []
        self.posRules = {}
        self.load_rules()
        self.POSTags = set()    # All POS tags encountered in the XML
        self.rxStemGlosses = re.compile('^$')
        self.mainGlossLang = 'en'
        self.badAnalysisLangs = []
        if 'main_gloss_language' in self.corpusSettings:
            self.mainGlossLang = self.corpusSettings['main_gloss_language']
        if 'bad_analysis_languages' in self.corpusSettings:
            self.badAnalysisLangs = self.corpusSettings['bad_analysis_languages']
    
    def load_rules(self):
        """
        Load rules for converting the glosses into bags of grammatical
        tags.
        """
        self.load_glosses(os.path.join(self.settingsDir, 'glossList.txt'))
        self.load_gramm_rules(os.path.join(self.settingsDir, 'gramRules.txt'))
        self.load_pos_rules(os.path.join(self.settingsDir, 'posRules.txt'))
    
    def load_glosses(self, fname):
        """
        Load gloss list.
        """
        if len(fname) <= 0 or not os.path.isfile(fname):
            return
        f = open(fname, 'r', encoding='utf-8-sig')
        glosses = set()
        for line in f:
            line = line.strip()
            if len(line) > 0:
                for i in ['-', '=', '.', '‹', '›', '{', '}', '']:
                    for j in ['-', '=', '.', '‹', '›', '{', '}', '']:
                        glosses.add(i + line + j)
        f.close()
        self.rxStemGlosses = re.compile('\\b' + '|'.join(re.escape(gl) for gl in glosses) + '\\b')
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
                   '\', ana[\'parts\']) is not None or ' +\
                   're.search(\'' + s +\
                   '\', ana[\'gloss\']) is not None '
        ruleParts = rule.split('"')
        rule = ''
        for i in range(len(ruleParts)):
            if i % 2 == 0:
                rule += re.sub('([^\\[\\]~|& \t\']+)', ' \'\\1\' in tagsAndGlosses ',
                               ruleParts[i]).replace('|', ' or ').replace('&', ' and ')\
                                            .replace('~', ' not ').replace('[', '(').replace(']', ')')
            else:
                rule += replReg(ruleParts[i])
        return rule

    def load_gramm_rules(self, fname):
        """
        Load main set of rules for converting the glosses into bags
        of grammatical tags.
        """
        if len(fname) <= 0 or not os.path.isfile(fname):
            return
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

    def add_pos_ana(self, ana, pos):
        """
        Add the part of speech tag to single JSON analysis, taking into
        account the correspondences between FLEX tags and the target
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

    def add_pos_word(self, word, pos):
        """
        Add the part of speech tag to the JSON word, taking into
        account the correspondences between FLEX tags and the target
        corpus tags. Change the word, do not return anything.
        """
        if 'ana' not in word or len(word['ana']) <= 0:
            word['ana'] = [{}]
        for ana in word['ana']:
            self.add_pos_ana(ana, pos)

    def restore_gramm(self, word):
        """
        Restore grammatical tags from the glosses using the rules
        provided in gramRules.txt. Change the word, do not return
        anuthing.
        """
        if 'wtype' not in word or word['wtype'] != 'word' or 'ana' not in word:
            return
        # print(json.dumps(word, ensure_ascii=False))
        mainLangCategories = None
        if self.corpusSettings['languages'][0] in self.categories:
            mainLangCategories = self.categories[self.corpusSettings['languages'][0]]
        for ana in word['ana']:
            addedGrammTags = set()
            tagsAndGlosses = set()
            for field in ana:
                if field.startswith('gr.'):
                    if type(ana[field]) == str:
                        tagsAndGlosses.add(ana[field])
                    elif type(ana[field]) == list:
                        tagsAndGlosses |= set(ana[field])
            if 'gloss' in ana:
                tagsAndGlosses |= set(gl.strip('-=:.<>') for gl in self.rxSplitParts.findall(ana['gloss']))
            if len(self.grammRules) > 0:
                for rule in self.grammRules:
                    if eval(rule[0]):
                        addedGrammTags |= rule[1]
            elif 'gloss' in ana:
                glosses = set(self.rxSplitParts.findall(ana['gloss']))
                for gl in glosses:
                    if gl.upper() == gl:
                        gl = gl.lower()
                    addedGrammTags.add(gl)
            # print(list(addedGrammTags), list(tagsAndGlosses))
            for tag in addedGrammTags:
                if tag in mainLangCategories:
                    anaCatName = 'gr.' + mainLangCategories[tag]
                    if anaCatName not in ana:
                        ana[anaCatName] = tag
                    elif type(ana[anaCatName]) == str:
                        ana[anaCatName] = [ana[anaCatName], tag]
                    else:
                        ana[anaCatName].append(tag)

    def process_stem(self, stem, stemGloss, glossLang, anaJSON, curGlossList):
        """
        Add the lemma and its translation.
        """
        if stem[0] in '-=':
            stem = stem[1:]
        anaJSON['lex'] = stem
        transField = 'trans_' + glossLang
        if len(stemGloss) > 0 and stemGloss[0] in '-=':
            stemGloss = stemGloss[1:]
        anaJSON[transField] = stemGloss
        pureStem = self.rxFindStem.sub('', anaJSON['lex'])
        pureTrans = self.rxFindGloss.sub('', anaJSON[transField])
        if glossLang == self.mainGlossLang:
            anaJSON['gloss'] += anaJSON[transField].replace(' ', '.').replace('-', '_')
            anaJSON['gloss_index'] += 'STEM{' + pureStem + '}-'
        else:
            if 'gloss_' + glossLang not in anaJSON:
                anaJSON['gloss_' + glossLang] = ''
            if 'gloss_index_' + glossLang not in anaJSON:
                anaJSON['gloss_index_' + glossLang] = ''
            anaJSON['gloss_' + glossLang] += anaJSON[transField].replace(' ', '.').replace('-', '_')
            anaJSON['gloss_index_' + glossLang] += 'STEM{' + pureStem + '}-'
        if pureTrans != anaJSON[transField]:
            # anaJSON['gloss'] += \
            #     '[' + '[STEM]'.join(self.rxFindStem.findall(anaJSON[transField])) + ']'
            if len(self.glosses) > 0:
                curGlossList += [g.strip('-=:.‹›{}')
                                 for g in self.rxStemGlosses.findall(anaJSON[transField])]
            anaJSON[transField] = pureTrans
            anaJSON['lex'] = pureStem
        # else:

    def ana_from_gls(self, glsNode, parts):
        """
        Make and return a JSON analysis out of the glossing in the gls node
        and the segmentation into morphs.
        """
        # TODO: Not ready yet!
        if glsNode.text is None or len(glsNode.text) <= 0 or len(parts) <= 0:
            return {}
        glossLang = 'en'
        if 'lang' in glsNode.attrib:
            glossLang = re.sub('-.*', '', glsNode.attrib['lang'])
        anaJSON = {'parts': '', 'gloss': '', 'gloss_index': ''}
        curGlossList = []
        parts = parts.replace('', '=').replace('‹', '<').replace('‹', '<')
        glosses = glsNode.text.strip()
        partsList = self.rxSplitParts.findall(parts)
        glossesList = self.rxSplitParts.findall(glosses)
        for i in range(min(len(partsList), len(glossesList))):
            if glossesList[i] in self.glosses \
                    or re.search('^[-=<>0-9A-Z.:,()\\[\\]]+$', glossesList[i]) is not None:
                anaJSON['gloss'] += glossesList[i]
                anaJSON['gloss_index'] += glossesList[i].strip('-=:.<>') + '{' + partsList[i].strip('-=:.<>') + '}-'
                anaJSON['parts'] += partsList[i]
                curGlossList.append(glossesList[i].strip('-=:.<>'))
            else:
                anaJSON['parts'] += partsList[i]
                self.process_stem(partsList[i], glossesList[i], glossLang, anaJSON, curGlossList)
        return anaJSON

    def ana_from_morphemes(self, mNode):
        """
        Make and return a JSON analysis out of the glossing in the morphemes
        node.
        """
        anaJSON = {'parts': '', 'gloss': '', 'gloss_index': ''}
        curGlossList = []
        lastPart = ''
        for morph in mNode:
            if morph.tag != 'morph':
                continue
            if 'type' not in morph.attrib:
                morphType = 'unknown'
            else:
                morphType = morph.attrib['type']
            for element in morph:
                if element.tag == 'item' and 'type' in element.attrib:
                    if element.attrib['type'] in ['mb', 'txt']:
                        if element.text is None:
                            element.text = ' '
                        anaJSON['parts'] += element.text
                        lastPart = element.text
                    elif element.attrib['type'] == 'gls':
                        glossLang = 'en'
                        if 'lang' in element.attrib:
                            if element.attrib['lang'] in self.badAnalysisLangs:
                                continue
                            glossLang = re.sub('-.*', '', element.attrib['lang'])
                        if element.text is None:
                            element.text = ' '
                        gloss = element.text
                        glossIndex = element.text.strip('-=:.<>') + '{' + lastPart.strip('-=:.<>') + '}-'
                        if (morphType == 'stem'
                                or (morphType == 'unknown' and element.text not in self.glosses))\
                                or (morphType in ('enclitic', 'proclitic') and len(mNode) == 1):
                            self.process_stem(lastPart, element.text, glossLang, anaJSON, curGlossList)
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
                            curGlossList.append(gloss.strip('-=:.'))
                            if glossLang == self.mainGlossLang:
                                anaJSON['gloss'] += gloss
                                anaJSON['gloss_index'] += glossIndex
                            else:
                                if 'gloss_' + glossLang not in anaJSON:
                                    anaJSON['gloss_' + glossLang] = ''
                                if 'gloss_index_' + glossLang not in anaJSON:
                                    anaJSON['gloss_index_' + glossLang] = ''
                                anaJSON['gloss_' + glossLang] += gloss
                                anaJSON['gloss_index_' + glossLang] += glossIndex
                    elif element.attrib['type'] == 'msa' and morphType == 'stem':
                        if element.text is None:
                            element.text = ' '
                        pos = element.text.strip().replace('.', ' ')
                        self.POSTags.add(pos)
                        self.add_pos_ana(anaJSON, pos)
        return anaJSON

    def process_word_node(self, wordNode):
        """
        Extract one token from an XML node and return it
        as a JSON.
        """
        if (len(wordNode) == 1 and 'type' in wordNode[0].attrib
                and wordNode[0].attrib['type'] == 'punct'):
            yield {'wtype': 'punct', 'wf': wordNode[0].text}
            return
        wordJSON = {'wtype': 'word', 'wf': ''}
        wordPos = ''
        hasMorphemes = (len(wordNode.xpath('morphemes')) > 0)
        for el in wordNode:
            if el.tag not in ['item', 'morphemes'] or el.text is None:
                continue
            elif (hasMorphemes and el.tag == 'item'
                    and 'type' in el.attrib and el.attrib['type'] == 'gls'):
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
            # TODO: nt
        if wordPos != '':
            self.add_pos_word(wordJSON, wordPos)
        self.restore_gramm(wordJSON)
        yield wordJSON

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
                elif element.attrib['type'] in ['ft', 'lt', 'lit', 'gls'] and\
                        'lang' in element.attrib and\
                        re.sub('-.*', '', element.attrib['lang']) in self.corpusSettings['language_codes']:
                    transLang = self.corpusSettings['language_codes'][re.sub('-.*', '', element.attrib['lang'])]
                    if element.text is not None:
                        seTrans[transLang] = element.text
                    elif transLang not in seTrans:
                        seTrans[transLang] = ''
                elif element.attrib['type'] == 'nt':
                    seComment = element.text
        if not seNum.endswith('.') and len(seNum) > 0:
            seNum += '.'
        words = []
        if len(seNum) > 0:
            words.append({'wtype': 'punct', 'wf': seNum})
        words += [w for wn in se.xpath('words/word')
                  for w in self.process_word_node(wn)]
        seText = self.tp.restore_sentence_text(words)
        paraAlignment = {'off_start': 0, 'off_end': len(seText), 'para_id': self.pID}
        yield {'lang': 0, 'words': words, 'text': seText, 'para_alignment': [paraAlignment]}
        
        for lang in seTrans:
            langID = self.corpusSettings['languages'].index(lang)
            transText = self.tp.cleaner.clean_text(seTrans[lang])
            words = self.tp.tokenizer.tokenize(transText)
            paraAlignment = {'off_start': 0, 'off_end': len(transText), 'para_id': self.pID}
            yield {'lang': langID, 'words': words, 'text': transText, 'para_alignment': [paraAlignment]}

    def convert_file(self, fnameSrc, fnameTarget):
        nTokens, nWords, nAnalyzed = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        interlinears = srcTree.xpath('/document/interlinear-text')
        nDoc = 0
        for interlinear in interlinears:
            curFnameTarget = re.sub('(\\.[^.]*$)', '-' + str(nDoc) + '\\1', fnameTarget)
            nDoc += 1
            titleNode = interlinear.xpath('./title | ./item[@type="title"]')
            curMeta = {}
            title = ''
            if len(titleNode) > 0:
                title = titleNode[0].text
                curMeta = self.get_meta(fnameSrc)
            if len(curMeta) <= 1:
                curMeta = {'title': title, 'filename': fnameSrc}
            textJSON = {'meta': curMeta, 'sentences': []}
            textJSON['sentences'] = [s for sNode in interlinear.xpath('./paragraphs/paragraph/phrases/phrase | '
                                                                      './paragraphs/paragraph/phrases/word')
                                     for s in self.process_se_node(sNode)]
            textJSON['sentences'].sort(key=lambda s: s['lang'])
            for i in range(len(textJSON['sentences']) - 1):
                if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                    textJSON['sentences'][i]['last'] = True

            # Count words and tokens
            for i in range(len(textJSON['sentences']) - 1):
                if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                    textJSON['sentences'][i]['last'] = True
                for word in textJSON['sentences'][i]['words']:
                    nTokens += 1
                    if word['wtype'] == 'word':
                        nWords += 1
                    if 'ana' in word and len(word['ana']) > 0:
                        nAnalyzed += 1

            # Clean up and write the output
            self.tp.splitter.recalculate_offsets(textJSON['sentences'])
            self.tp.splitter.add_next_word_id(textJSON['sentences'])
            self.write_output(curFnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed


if __name__ == '__main__':
    x2j = Xml_Flex2JSON()
    x2j.process_corpus()

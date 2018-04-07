import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON


class Xml_Rnc2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from aligned
    parallel xml files in the format of Russian National Corpus
    and a csv with metadata.
    """

    rxSeTags = re.compile('<se [^<>]*> *| *</se>')
    rxSeParts = re.compile(' +~~~ +')
    rxSeWords = re.compile('<w>.*?</w>|(?<=>)[^<>]*(?=<)')
    rxWTags = re.compile('</?w(?: [^<>]*)?>')
    rxSpaces = re.compile('^ *$')

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'xml'
        self.pID = 0        # id of last aligned segment

    def process_se_tokens(self, tokens, lang):
        """
        Return a JSON sentence made of tokens, each of which is
        either a word (string that contains <w>) or punctuation
        (string without tags).
        """
        words = []
        seText = ''
        for token in tokens:
            if self.rxSpaces.search(token) is not None:
                seText += token
                continue
            tokenJSON = {}
            if not token.startswith('<w>'):
                tokenStripped = token.lstrip(' ')
                spacesL = len(token) - len(tokenStripped)
                tokenStripped = tokenStripped.rstrip(' ')
                spacesR = len(token) - spacesL - len(tokenStripped)
                tokenJSON['wf'] = tokenStripped
                tokenJSON['off_start'] = len(seText) + spacesL
                seText += token
                tokenJSON['off_end'] = len(seText) - spacesR
                tokenJSON['wtype'] = 'punct'
            elif '<ana' not in token:
                tokenStripped = self.rxWTags.sub('', token)
                tokenJSON['wf'] = tokenStripped
                tokenJSON['off_start'] = len(seText)
                seText += tokenStripped
                tokenJSON['off_end'] = len(seText)
                tokenJSON['ana'] = []
                tokenJSON['wtype'] = 'word'
            else:
                mAna = self.tp.parser.rxWordsRNC.search(token)
                if mAna is None:
                    continue
                word = mAna.group(2).strip('"\'')
                if len(word) <= 0:
                    continue
                tokenJSON['ana'] = self.tp.parser.transform_ana_rnc(mAna.group(1), lang=lang)
                tokenJSON['wf'] = word
                tokenJSON['off_start'] = len(seText)
                seText += word
                tokenJSON['off_end'] = len(seText)
                tokenJSON['wtype'] = 'word'
            words.append(tokenJSON)
        paraAlignment = {'off_start': 0, 'off_end': len(seText), 'para_id': self.pID}
        sentence = {'words': words, 'text': seText, 'para_alignment': [paraAlignment]}
        return sentence

    def process_se_node(self, se, lang):
        """
        Extract data from the <se> (sentence) node that contains
        one ore more sentences in one language. The input is an
        XML string, not an element.
        """
        bProcessXML = ('<w>' in se)
        seParts = self.rxSeParts.split(se)
        for part in seParts:
            if not bProcessXML:
                part = self.tp.cleaner.clean_text(part)
                words = self.tp.tokenizer.tokenize(part)
                paraAlignment = {'off_start': 0, 'off_end': len(part), 'para_id': self.pID}
                curSent = {'words': words, 'text': part, 'para_alignment': [paraAlignment]}
                if len(curSent['words']) > 0:
                    self.tp.splitter.add_next_word_id_sentence(curSent)
                    self.tp.parser.analyze_sentence(curSent, lang=lang)
                yield curSent
            else:
                yield self.process_se_tokens(self.rxSeWords.findall('>' + part.strip() + '<'), lang)

    def process_para_node(self, paraNode):
        """
        Extract data from a <para> node that contains a bunch of parallel
        fragments in several languages.
        """
        self.pID += 1
        for se in paraNode.xpath('se'):
            if se.get('lang') in self.corpusSettings['language_codes']:
                lang = self.corpusSettings['language_codes'][se.attrib['lang']]
                langCode = self.corpusSettings['languages'].index(lang)
                seStr = etree.tostring(se, encoding='unicode')
                seStr = self.rxSeTags.sub('', seStr)
                if self.rxSpaces.search(seStr) is not None:
                    continue
                for seJSON in self.process_se_node(seStr, lang):
                    if seJSON is None or 'words' in seJSON and len(seJSON['words']) <= 0:
                        continue
                    seJSON['lang'] = langCode
                    yield seJSON

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        textJSON['sentences'] = [s for paraNode in srcTree.xpath('/html/body/para')
                                 for s in self.process_para_node(paraNode)]
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


if __name__ == '__main__':
    x2j = Xml_Rnc2JSON()
    x2j.process_corpus()

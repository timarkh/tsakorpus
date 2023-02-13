import os
import re
import json
import copy
from lxml import etree
from xml_rnc2json import Xml_Rnc2JSON


class Tmx2JSON(Xml_Rnc2JSON):
    """
    Contains methods to make JSONs ready for indexing from aligned
    parallel tmx files in the format used e.g. in Tyumen learner coprora
    and a csv with metadata.
    """

    def __init__(self, settingsDir='conf_conversion'):
        Xml_Rnc2JSON.__init__(self, settingsDir=settingsDir)
        self.rxSegTags = re.compile('<seg[^<>]*> *| *</seg>', flags=re.DOTALL)
        self.srcExt = 'tmx'

    def process_se_node(self, se, lang):
        """
        Extract data from the <tuv> (sentence) node that contains
        one or more sentences in one language. The input is an
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
        Extract data from a <tu> node that contains a bunch of parallel
        fragments in several languages. There may be several translation
        variants for each language.
        """
        self.pID += 1
        transVariants = {}
        for tuv in paraNode.xpath('tuv'):
            if 'lang' in tuv.attrib and '{http://www.w3.org/XML/1998/namespace}lang' not in tuv.attrib:
                tuv.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = tuv.attrib['lang']
            if tuv.attrib.get('{http://www.w3.org/XML/1998/namespace}lang') not in self.corpusSettings['language_codes']:
                continue
            lang = self.corpusSettings['language_codes'][tuv.attrib['{http://www.w3.org/XML/1998/namespace}lang']]
            langCode = self.corpusSettings['languages'].index(lang)
            if langCode not in transVariants:
                transVariants[langCode] = 0
            else:
                transVariants[langCode] += 1
            transVariant = transVariants[langCode]
            sentMeta = {}
            for attr in tuv.attrib:
                if attr in self.corpusSettings['sentence_meta_fields']:
                    sentMeta[attr] = tuv.attrib[attr]
            segNode = tuv.xpath('seg')
            tuvStr = ''
            if segNode is not None and len(segNode) > 0:
                tuvStr = etree.tostring(segNode[0], encoding='unicode')
            tuvStr = self.rxSegTags.sub('', tuvStr)
            if self.rxSpaces.search(tuvStr) is not None:
                continue
            for seJSON in self.process_se_node(tuvStr, lang):
                if seJSON is None or 'words' in seJSON and len(seJSON['words']) <= 0:
                    continue
                seJSON['lang'] = langCode
                seJSON['transVar'] = transVariant
                seJSON['meta'] = copy.deepcopy(sentMeta)
                yield seJSON

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        textJSON['sentences'] = [s for paraNode in srcTree.xpath('/tmx/body/tu')
                                 for s in self.process_para_node(paraNode)]
        textJSON['sentences'].sort(key=lambda s: (s['lang'], s['transVar']))
        for i in range(len(textJSON['sentences']) - 1):
            if (textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']
                    or textJSON['sentences'][i]['transVar'] !=
                        textJSON['sentences'][i + 1]['transVar']):
                textJSON['sentences'][i]['last'] = True
                for word in textJSON['sentences'][i]['words']:
                    nTokens += 1
                    if word['wtype'] == 'word':
                        nWords += 1
                        if 'ana' in word and len(word['ana']) > 0:
                            nAnalyzed += 1
        if ('multiple_translation_variants' in self.corpusSettings
                and not self.corpusSettings['multiple_translation_variants']):
            # Multiple translation variants by default, but if
            # there is only one for each language, remove the redundant
            # key
            for i in range(len(textJSON['sentences'])):
                del textJSON['sentences'][i]['transVar']
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed


if __name__ == '__main__':
    x2j = Tmx2JSON()
    x2j.process_corpus()

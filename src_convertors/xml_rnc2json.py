import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON


class Xml_Rnc2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    XML files in the format of Russian National Corpus, which
    can either have all metadata in headers inside each file,
    or come with a metadata CSV. The texts can be either annotated
    according to the RNC format or unannotated. In the latter case,
    an additional file with annotated tokens may be used to add
    token-level annotation, e.g. morphology.
    Currently, simple XML files ("main corpus") and XML files
    with aligned parallel texts are supported. Type of corpus
    is determined by the value of the "corpus_type" parameter
    in conversion_settings.json (main/parallel).
    """

    rxSeTags = re.compile('<se(?: [^<>]*)?> *| *</se>')
    rxSeParts = re.compile(' +~~~ +')
    rxSeWords = re.compile('<w>.*?</w>|(?<=>)[^<>]*(?=<)', flags=re.DOTALL)
    rxWTags = re.compile('</?w(?: [^<>]*)?>')
    rxSpaces = re.compile('^ *\Z', flags=re.DOTALL)
    rxNewlines = re.compile('^ *\n+\Z', flags=re.DOTALL)
    rxDate = re.compile('^([12][0-9]{3})\\.[0-9]{2}\\.[0-9]{2}$')
    rxYear = re.compile('^[12][0-9]{3}')
    dictSpanClasses = {'h1': 'txt_h1', 'h2': 'txt_h2', 'h3': 'txt_h3',
                       'h4': 'txt_h4', 'h5': 'txt_h5', 'h6': 'txt_h6',
                       'i': 'i', 'b': 'b', 'em': 'em'}

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'xml'
        self.pID = 0        # id of last aligned segment

    def process_se_tokens(self, tokens, lang, p_class=None):
        """
        Return a JSON sentence made of tokens, each of which is
        either a word (string that contains <w>) or punctuation
        (string without tags).
        """
        words = []
        seText = ''
        for iToken in range(len(tokens)):
            token = tokens[iToken]
            if self.rxSpaces.search(token) is not None:
                seText += token
                continue
            elif self.rxNewlines.search(token) is not None:
                if iToken < len(tokens) - 1:
                    seText += ' '
                continue    # there may be newlines between words
            tokenJSON = {}
            if not token.startswith('<w>'):
                tokenStripped = token.lstrip(' ')
                spacesL = len(token) - len(tokenStripped)
                tokenStripped = tokenStripped.rstrip(' ')
                spacesR = len(token) - spacesL - len(tokenStripped)
                tokenJSON['wf'] = tokenStripped
                tokenJSON['off_start'] = len(seText) + spacesL
                seText += token.replace('\n', '')
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
                if 'clean_words_rnc' in self.corpusSettings and self.corpusSettings['clean_words_rnc']:
                    word = self.tp.cleaner.clean_text(word)
                    wordClean, word = self.tp.cleaner.clean_token_rnc(word)
                else:
                    wordClean = word
                tokenJSON['ana'] = self.tp.parser.transform_ana_rnc(mAna.group(1), lang=lang)
                tokenJSON['wf'] = wordClean
                tokenJSON['off_start'] = len(seText)
                seText += word
                tokenJSON['off_end'] = len(seText)
                tokenJSON['wtype'] = 'word'
            words.append(tokenJSON)
        sentence = {'words': words, 'text': seText}
        if 'corpus_type' in self.corpusSettings and self.corpusSettings['corpus_type'] == 'parallel':
            paraAlignment = {'off_start': 0, 'off_end': len(seText), 'para_id': self.pID}
            sentence['para_alignment'] = [paraAlignment]
        self.add_class(sentence, p_class)
        return sentence

    def add_class(self, sentence, span_class):
        """
        Add style-related class that can appear as an attribute
        in paragraph nodes.
        Modify the sentence, do not return anything.
        """
        if span_class is None or 'text' not in sentence or len(sentence['text']) <= 0:
            return
        sentence['style_spans'] = [{'off_start': 0,
                                    'off_end': len(sentence['text']),
                                    'span_class': span_class}]

    def process_se_node(self, se, lang, p_class=None):
        """
        Extract data from the <se> (sentence) node that contains
        one or more sentences in one language. The input is an
        XML string, not an element.
        """
        bProcessXML = (('analyze_text' in self.corpusSettings and not self.corpusSettings['analyze_text'])
                       or '<w>' in se)
        # bProcessXML means that token-level annotation (e.g. morphology)
        # has already been done.
        seParts = self.rxSeParts.split(se)
        for part in seParts:
            if not bProcessXML:
                part = self.tp.cleaner.clean_text(part)
                words = self.tp.tokenizer.tokenize(part)
                curSent = {'words': words, 'text': part}
                if 'corpus_type' in self.corpusSettings and self.corpusSettings['corpus_type'] == 'parallel':
                    paraAlignment = {'off_start': 0, 'off_end': len(part), 'para_id': self.pID}
                    curSent['para_alignment'] = [paraAlignment]
                if len(curSent['words']) > 0:
                    self.add_class(curSent, p_class)
                    self.tp.splitter.add_next_word_id_sentence(curSent)
                    self.tp.parser.analyze_sentence(curSent, lang=lang)
                yield curSent
            else:
                yield self.process_se_tokens(self.rxSeWords.findall('>' + part.strip() + '<'),
                                             lang, p_class=p_class)

    def process_p_node(self, pNode):
        """
        Extract data from a <p> node that contains a single paragraph of text
        written in the main (and probably only) language of the corpus.
        """
        pClass = None
        if 'class' in pNode.attrib:
            if pNode.attrib['class'] in self.dictSpanClasses:
                pClass = self.dictSpanClasses[pNode.attrib['class']]
        for se in pNode.xpath('se'):
            lang = self.corpusSettings['languages'][0]
            seStr = etree.tostring(se, encoding='unicode')
            seStr = self.rxSeTags.sub('', seStr)
            if self.rxSpaces.search(seStr) is not None:
                continue
            for seJSON in self.process_se_node(seStr, lang, p_class=pClass):
                if seJSON is None or 'words' in seJSON and len(seJSON['words']) <= 0:
                    continue
                seJSON['lang'] = 0
                yield seJSON

    def process_para_node(self, paraNode):
        """
        Extract data from a <para> node that contains a bunch of parallel
        fragments in several languages.
        """
        self.pID += 1
        pClass = None
        if 'class' in paraNode.attrib:
            if paraNode.attrib['class'] in self.dictSpanClasses:
                pClass = paraNode.attrib['class']
        for se in paraNode.xpath('se'):
            if se.get('lang') in self.corpusSettings['language_codes']:
                lang = self.corpusSettings['language_codes'][se.attrib['lang']]
                langCode = self.corpusSettings['languages'].index(lang)
                seStr = etree.tostring(se, encoding='unicode')
                seStr = self.rxSeTags.sub('', seStr)
                if self.rxSpaces.search(seStr) is not None:
                    continue
                for seJSON in self.process_se_node(seStr, lang, p_class=pClass):
                    if seJSON is None or 'words' in seJSON and len(seJSON['words']) <= 0:
                        continue
                    seJSON['lang'] = langCode
                    yield seJSON

    def get_meta_from_header(self, srcTree, fname):
        """
        Retrieve the metadata from the header of the XML document.
        Return it as a dictionary.
        """
        meta = {'filename': fname}
        for metaNode in srcTree.xpath('/html/head/meta'):
            if 'name' not in metaNode.attrib or 'content' not in metaNode.attrib:
                continue
            metaName = metaNode.attrib['name']
            metaValue = metaNode.attrib['content'].strip()
            # Hard-coded hacks for Russian National Corpus (not needed elsewhere):
            if metaName == 'header':
                meta['title'] = metaValue
            if metaName == 'created':
                metaName = 'year_from'
            elif metaName == 'publ_year':
                metaName = 'year_publ'
                mYear = self.rxYear.search(metaValue)
                if mYear is None:
                    continue
                else:
                    metaValue = metaValue[:4]
            elif metaName == 'birthday':
                metaName = 'year_birth'
                mYear = self.rxYear.search(metaValue)
                if mYear is None:
                    continue
                else:
                    metaValue = metaValue[:4]
            if metaName in self.corpusSettings['meta_fields']:
                if metaName not in meta:
                    meta[metaName] = metaValue
                elif type(meta[metaName]) == str:
                    meta[metaName] = [meta[metaName], metaValue]
                else:
                    meta[metaName].append(metaValue)
        if 'year_from' in meta:
            if type(meta['year_from']) == str:
                mDate = self.rxDate.search(meta['year_from'])
                if mDate is not None:
                    meta['issue'] = meta['year_from']
                    meta['year_to'] = meta['year_from'] = mDate.group(1)
                else:
                    meta['year_to'] = meta['year_from']
            else:
                try:
                    meta['year_to'] = max(int(y) for y in meta['year_from'])
                    meta['year_from'] = min(int(y) for y in meta['year_from'])
                except:
                    del meta['year_from']
                    del meta['year_to']
        return meta

    def convert_file(self, fnameSrc, fnameTarget):
        textJSON = {'meta': {}, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        try:
            srcTree = etree.parse(fnameSrc)
        except:
            self.log_message('Error when opening ' + fnameSrc)
            return 0, 0, 0
        if 'meta_in_header' not in self.corpusSettings or not self.corpusSettings['meta_in_header']:
            textJSON['meta'] = self.get_meta(fnameSrc)
        else:
            textJSON['meta'] = self.get_meta_from_header(srcTree, fnameSrc)
        if 'corpus_type' in self.corpusSettings and self.corpusSettings['corpus_type'] == 'parallel':
            textJSON['sentences'] = [s for paraNode in srcTree.xpath('/html/body/para|/html/body/p/para')
                                     for s in self.process_para_node(paraNode)]
            textJSON['sentences'].sort(key=lambda s: s['lang'])
        else:
            textJSON['sentences'] = []
            for pNode in srcTree.xpath('/html/body/p'):
                curSentences = [s for s in self.process_p_node(pNode)]
                if len(curSentences) > 0:
                    # Add a newline to the end of each paragraph
                    curSentences[-1]['text'] += '\n'
                    curSentences[-1]['words'].append({'wtype': 'punct',
                                                      'wf': '\n',
                                                      'off_start': len(curSentences[-1]['text']) - 1,
                                                      'off_end': len(curSentences[-1]['text'])})
                    textJSON['sentences'] += curSentences
            if len(textJSON['sentences']) > 0:
                textJSON['sentences'][-1]['last'] = True
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
        self.tp.splitter.add_contextual_flags(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed


if __name__ == '__main__':
    x2j = Xml_Rnc2JSON()
    x2j.process_corpus()

import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON


class TxtQuestionnaires2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from 
    raw text files that contain aligned single examples (typically
    answers to a questionnaire), one example per line,
    a csv with metadata and lists with parsed word forms.
    Each example is stored as one sentence, even if contains
    several sentences in fact.
    """

    rxSpaces = re.compile('^ *$')

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'txt'
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

    def process_se(self, se, lang):
        """
        Make a JSON sentence from raw text.
        """
        bParse = lang in self.corpusSettings['parsed_wordlist_filename']
        part = self.tp.cleaner.clean_text(se)
        words = self.tp.tokenizer.tokenize(part)
        paraAlignment = {'off_start': 0, 'off_end': len(part), 'para_id': self.pID}
        sentJSON = {'words': words, 'text': part, 'para_alignment': [paraAlignment]}
        self.tp.splitter.recalculate_offsets_sentence(sentJSON)
        self.tp.splitter.add_next_word_id_sentence(sentJSON)
        if not bParse:
            return sentJSON
        else:
            nTokens, nWords, nAnalyzed = self.tp.parser.analyze_sentence(sentJSON, lang)
            return sentJSON

    def process_para(self, para):
        """
        Extract data from a line of the source file that contains a bunch of parallel
        fragments in several languages.
        """
        self.pID += 1
        langCode = -1
        for seStr in para.strip('\r\n').split('\t'):
            langCode += 1
            if langCode >= len(self.corpusSettings['languages']):
                continue
            lang = self.corpusSettings['languages'][langCode]
            if self.rxSpaces.search(seStr) is not None:
                continue
            seJSON = self.process_se(seStr, lang)
            if seJSON is None or 'words' in seJSON and len(seJSON['words']) <= 0:
                continue
            seJSON['lang'] = langCode
            yield seJSON

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyze = 0, 0, 0
        fSrc = open(fnameSrc, 'r', encoding='utf-8-sig')
        textJSON['sentences'] = [s for para in fSrc
                                 for s in self.process_para(para) if len(para) > 2]
        textJSON['sentences'].sort(key=lambda s: s['lang'])
        for i in range(len(textJSON['sentences']) - 1):
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyze


if __name__ == '__main__':
    x2j = TxtQuestionnaires2JSON()
    x2j.process_corpus()

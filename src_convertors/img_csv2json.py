import os
import re
import copy
import json
from txt2json import Txt2JSON


class ImgCsv2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from 
    raw csv files that contain single sentences, one example per line,
    together with their sentence-level metadata and reference
    to an image, a csv with metadata and lists with parsed word forms.
    Each example is stored as one sentence, even if contains
    several sentences in fact.
    """

    rxSpaces = re.compile('^ *$')

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'csv'
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
        sentence = {'words': words, 'text': seText}
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

    def process_line(self, line):
        """
        Extract data from a line of the source file that contains a string and
        its sentence-level metadata.
        """
        fields = line.strip('\r\n').split('\t')
        fields = {self.corpusSettings['sentence_meta'][i]: fields[i] for i in range(len(fields))}
        if 'language' not in fields:
            self.log_message('No language, assuming ' + self.corpusSettings['languages'][0] + '.')
            fields['language'] = self.corpusSettings['languages'][0]
        elif fields['language'] not in self.corpusSettings['languages']:
            self.log_message('Wrong language: ' + fields['language'])
            return
        langCode = self.corpusSettings['languages'].index(fields['language'])
        fields['text'] = fields['text'].replace('\\n', '\n')
        if self.rxSpaces.search(fields['text']) is not None:
            return
        sentMeta = copy.deepcopy(fields)
        del sentMeta['text']
        del sentMeta['language']
        if 'img' in sentMeta and not sentMeta['img'].lower().endswith(('.jpg', '.png', '.gif')):
            sentMeta['img'] += '.jpg'
        # for seJson in self.process_text(fields['text'], fields['language']):
        sentences, nTokens, nWords, nAnalyze = self.tp.process_string('‣ ' + fields['text'] + '\n')
        for iSe in range(len(sentences)):
            seJson = sentences[iSe]
            if seJson is None or ('words' in seJson and len(seJson['words']) <= 0):
                continue
            if iSe == len(sentences) - 1 or all(sentences[iNextSe] is None
                                                or 'words' in sentences[iNextSe] and len(sentences[iNextSe]['words']) <= 0
                                                for iNextSe in range(iSe + 1, len(sentences))):
                seJson['text'] += '\n'
            seJson['lang'] = langCode
            seJson['meta'] = sentMeta
            yield seJson

    def convert_file(self, fnameSrc, fnameTarget):
        nTokens, nWords, nAnalyze = 0, 0, 0
        textJSON = {'meta': {}, 'sentences': []}
        fSrc = open(fnameSrc, 'r', encoding='utf-8-sig')
        sentences = [s for line in fSrc
                     for s in self.process_line(line) if len(line) > 3]
        sentences.sort(key=lambda s: s['meta']['img'])
        prevImg = ''
        for s in sentences:
            curImg = s['meta']['img']
            if curImg != prevImg:
                if len(prevImg) > 0:
                    self.write_output(re.sub('\\.(json|json\\.gz)$',
                                             '_' + self.rxStripExt.sub('', prevImg) + '.\\1', fnameTarget), textJSON)
                curMeta = self.get_meta(curImg)
                textJSON = {'meta': curMeta, 'sentences': []}
                prevImg = curImg
            textJSON['sentences'].append(s)
        if len(prevImg) > 0:
            self.write_output(re.sub('\\.(json|json\\.gz)$',
                                     '_' + self.rxStripExt.sub('', prevImg) + '.\\1', fnameTarget), textJSON)
        return nTokens, nWords, nAnalyze


if __name__ == '__main__':
    x2j = ImgCsv2JSON()
    x2j.process_corpus()

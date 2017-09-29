import json
import os
import gzip
import re
import subprocess
from shutil import copyfile
import copy


class JSON2CG:
    """
    Contains methods for translating Tsakorpus JSON files into the
    Constraint Grammar format for subsequent disambiguation and
    backwards.
    """
    SETTINGS_DIR = '../conf'
    rxCGWords = re.compile('"<[^<>]*>"\n(?:\t[^\n]*\n)*', flags=re.DOTALL)
    rxCGAna = re.compile('<ana_([0-9]+)>', flags=re.DOTALL)

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.languages = self.settings['languages']
        if len(self.languages) <= 0:
            self.languages = [self.name]
        self.format = self.settings['input_format']
        self.corpus_dir = os.path.join('corpus', self.name)
        self.load_settings()

    def load_settings(self):
        """
        Load settings from the corpus-specific settings file
        (they may override the general settings loaded earlier).
        Clean the error log file, if any.
        """
        fCorpus = open(os.path.join(self.corpus_dir, 'conf', 'corpus.json'), 'r',
                       encoding='utf-8-sig')
        self.settings.update(json.loads(fCorpus.read()))
        fCorpus.close()

    def translate2cg_words(self, words):
        """
        Translate a list of JSON words taken from one sentence into the
        CG format. Return the translated words as a string.
        """
        wordsCG = ''
        for i in range(len(words)):
            word = words[i]
            wf = ''
            if 'wf' in word:
                wf = word['wf'].replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace('\n', '\\n')
            if 'wtype' not in word or word['wtype'] != 'word':
                wordsCG += '"<' + wf + '>"\n\t"' + wf + '" punct\n'
                continue
            wordsCG += '"<' + wf + '>"\n'
            if 'ana' not in word:
                continue
            for iAna in range(len(word['ana'])):
                ana = word['ana'][iAna]
                lex = ''
                if 'lex' in ana:
                    lex = ana['lex'].replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                gr = ''
                for k, v in ana.items():
                    if k.startswith('gr.'):
                        if type(v) == list:
                            gr += ' '.join(v) + ' '
                        else:
                            gr += v + ' '
                gr = gr.strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                wordsCG += '\t"' + lex + '" <ana_' + str(iAna) + '>'
                if len(gr) > 0:
                    wordsCG += ' ' + gr
                wordsCG += '\n'
        return wordsCG

    def translate2cg_document(self, d):
        """
        Translate a dictionary with a single JSON document into the CG format.
        Return the translated document as a dictionary {language_name: string}.
        """
        docCG = {l: '' for l in self.languages}
        if 'sentences' not in d:
            return docCG
        sentences = d['sentences']
        for s in sentences:
            if len(self.languages) == 1:
                language = self.languages[0]
            elif 'lang' not in s:
                print('No language code in the document.')
                return {l: '' for l in self.languages}
            else:
                langID = s['lang']
                if langID >= len(self.languages) or langID < 0:
                    print('Invalid language code in the document.')
                    return {l: '' for l in self.languages}
                language = self.languages[langID]
            if 'words' not in s:
                docCG[language] += '"<SENT_BOUNDARY>"\n'
                continue
            docCG[language] += self.translate2cg_words(s['words'])
            docCG[language] += '"<SENT_BOUNDARY>"\n'
        return docCG

    def write_cg(self, docCG, fname):
        """
        Write a dictionary {language_name: CG text of the document} to the files,
        one for each language.
        """
        dirOut = os.path.join(self.corpus_dir, 'cg')
        for language in docCG:
            language = re.sub('[/\\?.()*"\']', '', language)
            dirOutLang = os.path.join(dirOut, language)
            if not os.path.exists(dirOutLang):
                os.makedirs(dirOutLang)
            fnameOut = os.path.join(dirOutLang, re.sub('\\.json(?:\\.gz)?$', '.txt', fname))
            fOut = open(fnameOut, 'w', encoding='utf-8')
            fOut.write(docCG[language])
            fOut.close()

    def translate2cg(self):
        """
        Translate all files from the corpus/%corpus_name%/json directory to
        the CG format. The files are split into language sections and put to
        the corpus/%corpus_name%/cg/%language_name% directory.
        """
        iDoc = 0
        jsonDir = os.path.join(self.corpus_dir, 'json')
        for fname in os.listdir(jsonDir):
            fnameIn = os.path.join(jsonDir, fname)
            if self.format == 'json':
                fIn = open(fnameIn, 'r', encoding='utf-8-sig')
            elif self.format == 'json-gzip':
                fIn = gzip.open(fnameIn, 'rt', encoding='utf-8-sig')
            else:
                return
            doc = json.load(fIn)
            fIn.close()
            docCG = self.translate2cg_document(doc)
            self.write_cg(docCG, fname)
            iDoc += 1
        print('Translation to CG finished,', iDoc, 'documents translated.')

    def disambiguate_cg(self):
        """
        Call the CG processor to disambiguate files previously translated
        into the CG format. Each language directory is disambiguated with
        the help of a separate .cg3 file specified in the settings file.
        Store the disambiguated files in corpus/%corpus_name%/cg_disamb/%language_name%.
        """
        for language in self.settings['languages']:
            language4dir = re.sub('[/\\?.()*"\']', '', language)
            langDirIn = os.path.join(self.corpus_dir, 'cg', language4dir)
            langDirOut = os.path.join(self.corpus_dir, 'cg_disamb', language4dir)
            if not os.path.exists(langDirOut):
                os.makedirs(langDirOut)
            if self.settings['cg_disambiguate'] and language in self.settings['cg_filename']:
                fullGrammarFname = os.path.abspath(os.path.join(self.corpus_dir,
                                                                self.settings['cg_filename'][language]))
            else:
                continue
            for fname in os.listdir(langDirIn):
                fullFnameIn = os.path.abspath(os.path.join(langDirIn, fname))
                fullFnameOut = os.path.abspath(os.path.join(langDirOut, fname))
                cgCmd = 'cg3 -g "' + fullGrammarFname + '" -I "' + fullFnameIn + '" -O "' + fullFnameOut + '"'
                output = subprocess.Popen(cgCmd, shell=True,
                                          stdout=subprocess.PIPE).stdout.read()
        print('CG disambiguation finished.')

    def disambiguate_sentence(self, s, sDisambCG):
        """
        Disambiguate a single JSON sentence using a string from
        a previously disambiguated CG file.
        Return the disambiguated sentence as JSON.
        """
        CGWords = self.rxCGWords.findall(sDisambCG)
        if len(CGWords) != len(s['words']):
            return copy.deepcopy(s)
        sDisambJSON = {}
        for k, v in s.items():
            if k != 'words':
                sDisambJSON[k] = copy.deepcopy(v)
        sDisambJSON['words'] = []
        for iWord in range(len(CGWords)):
            wordSrc = s['words'][iWord]
            if 'ana' not in wordSrc or len(wordSrc['ana']) <= 0:
                sDisambJSON['words'].append(copy.deepcopy(wordSrc))
                continue
            wordDisamb = {}
            for k, v in wordSrc.items():
                if k != 'ana':
                    wordDisamb[k] = copy.deepcopy(v)
            wordDisamb['ana'] = [copy.deepcopy(wordSrc['ana'][int(iAna)])
                                 for iAna in self.rxCGAna.findall(CGWords[iWord])]
            sDisambJSON['words'].append(wordDisamb)
        return sDisambJSON

    def disambiguate_json(self, docSrc, disambLangParts):
        """
        Disambiguate one JSON document using strings from previously
        disambiguated CG files, one for each of the languages.
        Return the disambiguated version of the document.
        """
        docDisamb = {}
        for k, v in docSrc.items():
            if k != 'sentences':
                docDisamb[k] = copy.deepcopy(v)
                continue
        if 'sentences' not in docSrc:
            return docDisamb
        docDisamb['sentences'] = []

        disambLangParts = {k: re.split('<SENT_BOUNDARY>\n*', v, flags=re.DOTALL)
                           for k, v in disambLangParts.items()}

        sentNums = {l: -1 for l in self.languages}   # sentence counter for each of the languages
        for s in docSrc['sentences']:
            if 'words' not in s or ('lang' not in s and len(self.languages) > 1):
                docDisamb['sentences'].append(s)
                continue
            elif 'lang' not in s:
                langID = 0
            else:
                langID = s['lang']
            if langID < 0 or langID >= len(self.languages):
                docDisamb['sentences'].append(s)
                continue
            language = self.languages[langID]
            sentNums[language] += 1
            if (language not in disambLangParts or len(disambLangParts[language]) <= 0
                    or sentNums[language] >= len(disambLangParts[language])):
                docDisamb['sentences'].append(s)
                continue
            docDisamb['sentences'].append(self.disambiguate_sentence(s, disambLangParts[language][sentNums[language]]))
        return docDisamb

    def disambiguate_json_corpus(self):
        """
        Read the JSON documents of the corpus and their disambiguated CG
        variants. Remove analyses in JSON that have been removed in the
        CG version. Store the disambiguated JSON files in the
        corpus/%corpus_name%/json_disamb directory.
        If there is no disambiguated version for some file or for some
        of the languages, just copy the source JSON file to the new
        directory.
        """
        iDoc = 0
        jsonDirIn = os.path.join(self.corpus_dir, 'json')
        jsonDirOut = os.path.join(self.corpus_dir, 'json_disamb')
        if not os.path.exists(jsonDirOut):
            os.makedirs(jsonDirOut)
        for fname in os.listdir(jsonDirIn):
            fnameJsonIn = os.path.join(jsonDirIn, fname)
            fnameJsonOut = os.path.join(jsonDirOut, fname)
            if fnameJsonIn == fnameJsonOut:   # this should not happen, but just in case
                print('Something went wrong: input file name = output file name.')
                continue
            fnameCgIn = re.sub('\\.json(?:\\.gz)?$', '.txt', fname)
            languageParts = {}      # {language: disambiguated text}
            for language in self.settings['languages']:
                language4dir = re.sub('[/\\?.()*"\']', '', language)
                cgDirIn = os.path.join(self.corpus_dir, 'cg_disamb', language4dir)
                fnameCgInLanguage = os.path.join(cgDirIn, fnameCgIn)
                if not os.path.exists(fnameCgInLanguage):
                    continue
                fCgInLanguage = open(fnameCgInLanguage, 'r', encoding='utf-8-sig')
                languageParts[language] = fCgInLanguage.read()
                fCgInLanguage.close()
            if len(languageParts) <= 0:
                copyfile(fnameJsonIn, fnameJsonOut)
                continue
            if self.format == 'json':
                fJsonIn = open(fnameJsonIn, 'r', encoding='utf-8-sig')
            elif self.format == 'json-gzip':
                fJsonIn = gzip.open(fnameJsonIn, 'rt', encoding='utf-8-sig')
            else:
                return
            docJSON = json.load(fJsonIn)
            fJsonIn.close()
            docJSONDisamb = self.disambiguate_json(docJSON, languageParts)
            if self.format == 'json':
                fJsonOut = open(fnameJsonOut, 'w', encoding='utf-8')
            elif self.format == 'json-gzip':
                fJsonOut = gzip.open(fnameJsonOut, 'w', encoding='utf-8')
            else:
                copyfile(fnameJsonIn, fnameJsonOut)
                continue
            json.dump(docJSONDisamb, fp=fJsonOut,
                      ensure_ascii=False, indent=self.settings['json_indent'])
            iDoc += 1
        print('Disambiguation finished,', iDoc, 'documents disambiguated.')

    def process_corpus(self):
        """
        Translate all corpus JSON files into the CG format, disambiguate
        them and use the disambiguated CG filed for disambiguating the JSONs.
        """
        self.translate2cg()
        self.disambiguate_cg()
        self.disambiguate_json_corpus()


if __name__ == '__main__':
    translator = JSON2CG()
    translator.process_corpus()

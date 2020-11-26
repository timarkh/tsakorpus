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
    rxCGWords = re.compile('"<[^<>]*>"\n(?:\t[^\n]*\n)*', flags=re.DOTALL)
    rxCGAna = re.compile('<ana_([0-9]+)> *([^\r\n]*)', flags=re.DOTALL)

    def __init__(self, settingsDir='conf_conversion', corpusDir='corpus', corpusName=''):
        if not os.path.exists(settingsDir) and os.path.exists('conf'):
            # Backward compatibility: check the old name of configuration folder
            settingsDir = 'conf'
        self.settingsDir = settingsDir
        self.corpusDir = corpusDir
        self.settings = {'corpus_dir': corpusDir}
        self.name = corpusName
        # if os.path.exists(self.settingsDir):
        #     try:
        #         f = open(os.path.join(self.settingsDir, 'conversion_settings.json'),
        #                  'r', encoding='utf-8')
        #     except IOError:
        #         # Obsolete settings file name; I keep it here for backward compatibility
        #         f = open(os.path.join(self.settingsDir, 'corpus.json'),
        #                  'r', encoding='utf-8')
        #     self.settings = json.loads(f.read())
        #     f.close()
        #     self.name = self.settings['corpus_name']
        # if len(self.name) > 0:
        #     self.corpusDir = os.path.join(self.corpusDir, self.name)
        #     self.settingsDir = os.path.join(self.corpusDir, settingsDir)
        #     if (not os.path.exists(self.settingsDir)
        #             and os.path.exists(os.path.join(self.corpusDir, 'conf'))):
        #         # Backward compatibility: check the old name of configuration folder
        #         self.settingsDir = os.path.join(self.corpusDir, 'conf')
        self.load_settings()
        self.format = 'json'
        if self.settings['gzip']:
            self.format = 'json-gzip'
        self.languages = self.settings['languages']
        if len(self.languages) <= 0:
            self.languages = [self.name]

        fCategories = open(os.path.join(self.settingsDir, 'categories.json'), 'r',
                           encoding='utf-8-sig')
        self.categories = json.loads(fCategories.read())
        fCategories.close()

        self.nonDisambAnalyses = 0      # number of analyses for analyzed tokens before disambiguation
        self.disambAnalyses = 0         # number of analyses after disambiguation
        self.nWords = 0                 # total number of words in the corpus
        self.nAnalyzedWords = 0         # number of words with at least one analysis

    def load_settings(self):
        """
        Load settings from the corpus-specific settings file
        (they may override the general settings loaded earlier).
        Clean the error log file, if any.
        """
        try:
            fCorpus = open(os.path.join(self.settingsDir, 'conversion_settings.json'), 'r',
                           encoding='utf-8-sig')
        except IOError:
            # Obsolete settings file name; I keep it here for backward compatibility
            fCorpus = open(os.path.join(self.settingsDir, 'corpus.json'), 'r',
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
                if language not in self.settings['cg_filename']:
                    continue
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
        for language in docCG:
            if language not in self.settings['cg_filename']:
                continue
            dirOut = os.path.join(self.corpusDir, 'cg')
            language = re.sub('[/\\?.()*"\']', '', language)
            dirOutLang = os.path.join(dirOut, language)
            mDir = re.search('^(.+)[/\\\\]', fname)
            if mDir is not None:
                dirOut = os.path.join(dirOutLang, mDir.group(1))
            else:
                dirOut = dirOutLang
            if not os.path.exists(dirOut):
                os.makedirs(dirOut)
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
        jsonDir = os.path.join(self.corpusDir, 'json')
        for root, dirs, files in os.walk(jsonDir):
            for fname in files:
                fnameRel = fname
                if len(root) > len(jsonDir) + 1:
                    fnameRel = os.path.join(root[len(jsonDir) + 1:], fname)
                fnameIn = os.path.join(root, fname)
                try:
                    if self.format == 'json' and fname.endswith('.json'):
                        fIn = open(fnameIn, 'r', encoding='utf-8-sig')
                    elif self.format == 'json-gzip' and fname.endswith('.json.gz'):
                        fIn = gzip.open(fnameIn, 'rt', encoding='utf-8-sig')
                    else:
                        continue
                    doc = json.load(fIn)
                    fIn.close()
                    docCG = self.translate2cg_document(doc)
                    self.write_cg(docCG, fnameRel)
                except MemoryError:
                    print('Memory error when loading', fnameIn)
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
            langDirIn = os.path.join(self.corpusDir, 'cg', language4dir)
            langDirOut = os.path.join(self.corpusDir, 'cg_disamb', language4dir)
            if not os.path.exists(langDirOut):
                os.makedirs(langDirOut)
            if self.settings['cg_disambiguate'] and language in self.settings['cg_filename']:
                fullGrammarFname = os.path.abspath(os.path.join(self.corpusDir,
                                                                self.settings['cg_filename'][language]))
            else:
                continue
            for root, dirs, files in os.walk(langDirIn):
                for fname in files:
                    fullFnameIn = os.path.abspath(os.path.join(root, fname))
                    fullFnameOut = os.path.abspath(os.path.join(os.path.join(langDirOut, root[len(langDirIn) + 1:]), fname))
                    if fullFnameIn == fullFnameOut:
                        print('Something went wrong: fullFnameIn == fullFnameOut.')
                        continue
                    mDir = re.search('^(.+)[/\\\\]', fullFnameOut)
                    if mDir is not None and not os.path.exists(mDir.group(1)):
                        os.makedirs(mDir.group(1))
                    proc = subprocess.Popen('cg3 -g "' + fullGrammarFname + '"',
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            shell=True)
                    fIn = open(fullFnameIn, 'r', encoding='utf-8-sig')
                    text = fIn.read()
                    fIn.close()
                    text, err = proc.communicate(text.encode('utf-8'))
                    proc.wait()
                    fOut = open(fullFnameOut, 'w', encoding='utf-8')
                    fOut.write(text.decode('utf-8').replace('\r', '\n').replace('\n\n', '\n'))
                    fOut.close()
        print('CG disambiguation finished.')

    def modify_ana(self, anaOld, disambTags, lang):
        """
        Check if grammatical tags in the old analysis coincide with those
        in the disambiguated analysis. Modify the former if needed.
        Do not change the old analysis, return the disambiguated analysis.
        """
        if lang == '':
            if 'languages' in self.settings and len(self.settings['languages']) > 0:
                lang = self.settings['languages'][0]
            else:
                lang = self.settings['corpus_name']
        ana = copy.deepcopy(anaOld)
        disambTags = set([tag for tag in disambTags.strip().split(' ') if len(tag) > 0])
        oldTags = set()
        keys2delete = []
        for k, v in ana.items():
            if k.startswith('gr.'):
                if type(v) == list:
                    for iValue in range(len(v) - 1, -1, -1):
                        curValue = v[-iValue]
                        vCheck = curValue.strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                        if vCheck in disambTags:
                            oldTags.add(vCheck)
                        else:
                            # print('Removed value ' + curValue + ' from analysis.')
                            del v[-iValue]
                    if len(v) == 0:
                        # print('Removed key ' + k + ' from analysis.')
                        keys2delete.append(k)
                else:
                    vCheck = v.strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                    if vCheck in disambTags:
                        oldTags.add(vCheck)
                    else:
                        # print('Removed key ' + k + ' from analysis (value: ' + v + ')')
                        keys2delete.append(k)
        for k in keys2delete:
            del ana[k]
        for v in disambTags - oldTags:
            # Add tags added during disambiguation
            v = v.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
            if lang not in self.categories or v not in self.categories[lang]:
                print('Added tag ' + v + ' not found in categories.json.')
            else:
                # print('Added tag ' + v + '.')
                k = 'gr.' + self.categories[lang][v]
                if k in ana:
                    if type(ana[k]) == list:
                        ana[k].append(v)
                    else:
                        ana[k] = [ana[k], v]
                else:
                    ana[k] = v
        return ana

    def disambiguate_sentence(self, s, sDisambCG):
        """
        Disambiguate a single JSON sentence using a string from
        a previously disambiguated CG file.
        Return the disambiguated sentence as JSON.
        """
        CGWords = self.rxCGWords.findall(sDisambCG)
        if len(CGWords) != len(s['words']):
            return copy.deepcopy(s)
        lang = self.languages[0]
        if 'lang' in s and 0 <= s['lang'] < len(self.languages):
            lang = self.languages[s['lang']]
        sDisambJSON = {}
        for k, v in s.items():
            if k != 'words':
                sDisambJSON[k] = copy.deepcopy(v)
        sDisambJSON['words'] = []
        for iWord in range(len(CGWords)):
            self.nWords += 1
            wordSrc = s['words'][iWord]
            if 'ana' not in wordSrc or len(wordSrc['ana']) <= 0:
                sDisambJSON['words'].append(copy.deepcopy(wordSrc))
                continue
            self.nAnalyzedWords += 1
            self.nonDisambAnalyses += len(wordSrc['ana'])
            wordDisamb = {}
            for k, v in wordSrc.items():
                if k != 'ana':
                    wordDisamb[k] = copy.deepcopy(v)
            wordDisamb['ana'] = []
            for iAna, disambTags in self.rxCGAna.findall(CGWords[iWord]):
                wordDisamb['ana'].append(self.modify_ana(wordSrc['ana'][int(iAna)], disambTags, lang))
            self.disambAnalyses += len(wordDisamb['ana'])
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
        self.nWords = self.nAnalyzedWords = self.nonDisambAnalyses = self.disambAnalyses = 0
        iDoc = 0
        jsonDirIn = os.path.join(self.corpusDir, 'json')
        jsonDirOut = os.path.join(self.corpusDir, 'json_disamb')
        if not os.path.exists(jsonDirOut):
            os.makedirs(jsonDirOut)
        for root, dirs, files in os.walk(jsonDirIn):
            for fname in files:
                fnameJsonIn = os.path.abspath(os.path.join(root, fname))
                fnameJsonOut = os.path.abspath(os.path.join(os.path.join(jsonDirOut, root[len(jsonDirIn) + 1:]), fname))
                if fnameJsonIn == fnameJsonOut:   # this should not happen, but just in case
                    print('Something went wrong: input file name = output file name.')
                    continue
                mDir = re.search('^(.+)[/\\\\]', fnameJsonOut)
                if mDir is not None and not os.path.exists(mDir.group(1)):
                    os.makedirs(mDir.group(1))
                fnameCgIn = re.sub('\\.json(?:\\.gz)?$', '.txt', os.path.join(root, fname)[len(jsonDirIn) + 1:])
                languageParts = {}      # {language: disambiguated text}
                for language in self.settings['languages']:
                    if language not in self.settings['cg_filename']:
                        continue
                    language4dir = re.sub('[/\\?.()*"\']', '', language)
                    cgDirIn = os.path.join(self.corpusDir, 'cg_disamb', language4dir)
                    # print(fnameCgIn)
                    fnameCgInLanguage = os.path.join(cgDirIn, fnameCgIn)
                    if not os.path.exists(fnameCgInLanguage):
                        continue
                    fCgInLanguage = open(fnameCgInLanguage, 'r', encoding='utf-8-sig')
                    languageParts[language] = fCgInLanguage.read()
                    fCgInLanguage.close()
                if len(languageParts) <= 0:
                    copyfile(fnameJsonIn, fnameJsonOut)
                    continue
                try:
                    if self.format == 'json' and fnameJsonIn.endswith('.json'):
                        fJsonIn = open(fnameJsonIn, 'r', encoding='utf-8-sig')
                    elif self.format == 'json-gzip' and fnameJsonIn.endswith('.json.gz'):
                        fJsonIn = gzip.open(fnameJsonIn, 'rt', encoding='utf-8-sig')
                    else:
                        continue
                    docJSON = json.load(fJsonIn)
                    fJsonIn.close()
                    docJSONDisamb = self.disambiguate_json(docJSON, languageParts)
                    if self.format == 'json':
                        fJsonOut = open(fnameJsonOut, 'w', encoding='utf-8')
                    elif self.format == 'json-gzip':
                        fJsonOut = gzip.open(fnameJsonOut, 'wt', encoding='utf-8')
                    else:
                        copyfile(fnameJsonIn, fnameJsonOut)
                        continue
                    json.dump(docJSONDisamb, fp=fJsonOut,
                              ensure_ascii=False, indent=self.settings['json_indent'])
                except MemoryError:
                    print('Memory error when loading', fnameJsonIn)
                iDoc += 1
        print('Disambiguation finished,', iDoc, 'documents disambiguated,',
              self.nWords, 'words total,', self.nAnalyzedWords, 'words analyzed,',
              (self.nonDisambAnalyses + 1) / (self.nAnalyzedWords + 1),
              'analyses per analyzed word before disambiguation,',
              (self.disambAnalyses + 1) / (self.nAnalyzedWords + 1),
              'analyses per analyzed word after disambiguation.')

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
    # translator.disambiguate_json_corpus()

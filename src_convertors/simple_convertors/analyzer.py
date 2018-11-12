import re
import copy
import os


class DumbMorphParser:
    """
    Contains methods that add context-independent word-level
    morhological information from a parsed word list to a
    collection of JSON sentences. No actual parsing takes
    place here.
    """

    rxWordsRNC = re.compile('<w>(<ana.*?/(?:ana)?>)([^<>]+)</w>', flags=re.DOTALL)
    rxAnalysesRNC = re.compile('<ana *([^<>]+)(?:></ana>|/>)\\s*')
    rxAnaFieldRNC = re.compile('([^ <>"=]+) *= *"([^<>"]+)')
    rxSplitGramTags = re.compile('[, /=]')
    rxHyphenParts = re.compile('[^\\-]+|-+')
    rxGlossParts = re.compile('[^ \\-=<>]+')
    rxGlossIndexPart = re.compile('^(.*)\\{(.*?)\\}')

    def __init__(self, settings, categories, errorLog=''):
        self.settings = copy.deepcopy(settings)
        self.categories = copy.deepcopy(categories)
        self.rxAllGlosses = self.prepare_gloss_regex()
        self.analyses = {}
        self.errorLog = errorLog
        if 'multivalued_ana_features' in self.settings:
            self.settings['multivalued_ana_features'] = set(self.settings['multivalued_ana_features'])
        else:
            self.settings['multivalued_ana_features'] = set()
        if 'gramtags_exclude' in self.settings:
            self.settings['gramtags_exclude'] = set(self.settings['gramtags_exclude'])
        else:
            self.settings['gramtags_exclude'] = set()
        if ('parsed_wordlist_filename' in self.settings
                and len(self.settings['parsed_wordlist_filename']) > 0):
            if type(self.settings['parsed_wordlist_filename']) == str:
                self.load_analyses(os.path.join(self.settings['corpus_dir'],
                                                self.settings['parsed_wordlist_filename']))
            else:
                for language in self.settings['parsed_wordlist_filename']:
                    self.load_analyses(os.path.join(self.settings['corpus_dir'],
                                                    self.settings['parsed_wordlist_filename'][language]),
                                       language)

    def log_message(self, message):
        """
        If the filename of the error log is not empty, append
        the message to the file.
        """
        if self.errorLog is None or len(self.errorLog) <= 0:
            return
        try:
            fLog = open(self.errorLog, 'a', encoding='utf-8')
            fLog.write(message + '\n')
            fLog.close()
        except:
            return

    def load_analyses(self, fname, lang=''):
        """
        Load parsed word list from a file.
        """
        if lang == '':
            if 'languages' in self.settings and len(self.settings['languages']) > 0:
                lang = self.settings['languages'][0]
            else:
                lang = self.settings['corpus_name']
        self.analyses[lang] = {}
        try:
            f = open(fname, 'r', encoding='utf-8-sig')
            text = f.read()
            f.close()
            if self.settings['parsed_wordlist_format'] == 'xml_rnc':
                self.load_analyses_xml_rnc(text, lang=lang)
        except FileNotFoundError:
            fLog = open(self.errorLog, 'a', encoding='utf-8')
            fLog.write('File not found: ' + fname + '\n')
            fLog.close()

    def transform_gramm_str(self, grStr, lang=''):
        """
        Transform a string with gramtags into a JSON object.
        """
        grJSON = {}
        grTags = self.rxSplitGramTags.split(grStr)
        for tag in grTags:
            if len(tag.strip()) <= 0:
                continue
            if tag in self.settings['gramtags_exclude']:
                continue
            if tag not in self.categories[lang]:
                print('No category for a gramtag:', tag, ', language:', lang)
                continue
            cat = 'gr.' + self.categories[lang][tag]
            if cat not in grJSON:
                grJSON[cat] = tag
            else:
                if type(grJSON[cat]) != list:
                    grJSON[cat] = [grJSON[cat]]
                if tag not in grJSON[cat]:
                    grJSON[cat].append(tag)
        return grJSON

    def prepare_gloss_regex(self):
        """
        Return a regex that finds all glosses.
        """
        regexes = {}
        for lang in self.settings['languages']:
            if lang not in self.categories:
                self.categories[lang] = {}
            if 'glosses' in self.settings and lang in self.settings['glosses']:
                sRegex = '|'.join(re.escape(g) for g in sorted(self.settings['glosses'][lang], key=len))
                sRegex = '\\b(' + sRegex + ')\\b'
                regexes[lang] = re.compile(sRegex)
            else:
                sRegex = '|'.join(re.escape(g) for g in sorted(self.categories[lang], key=len))
                sRegex = '\\b(' + sRegex + ')\\b'
                regexes[lang] = re.compile(sRegex, flags=re.I)
        return regexes

    def gloss2gr(self, ana, lang):
        """
        For an analysis that has glosses, but no tags for inflectional
        categories, add these categories.
        """
        # TODO: Add rules for translating the glosses into tags.
        if 'gloss_index' not in ana:
            return
        glosses = self.rxAllGlosses[lang].findall(ana['gloss_index'])
        for gloss in glosses:
            if gloss.lower() in self.categories[lang]:
                field = 'gr.' + self.categories[lang][gloss.lower()]
                if field not in ana:
                    ana[field] = gloss.lower()
                else:
                    if type(ana[field]) == str:
                        ana[field] = [ana[field]]
                    if gloss.lower() not in ana[field]:
                        ana[field].append(gloss.lower())

    def find_stems(self, glossIndex, lang):
        """
        Return all glosses that are not in the categories list, and
        therefore are the glosses for the stem.
        """
        stems = []
        newIndexGloss = ''
        for glossPart in glossIndex.split('-'):
            if len(glossPart) <= 0:
                continue
            m = self.rxGlossIndexPart.search(glossPart)
            if m is None:
                newIndexGloss += glossPart + '-'
                continue
            gloss, part = m.group(1), m.group(2)
            if self.rxAllGlosses[lang].match(gloss) is None:
                stems.append((gloss, part))
                newIndexGloss += 'STEM{' + part + '}-'
            else:
                newIndexGloss += glossPart + '-'
        return stems, newIndexGloss

    def process_gloss_in_ana(self, ana):
        """
        If there are fields 'gloss' and 'parts' in the JSON
        analysis, add field 'gloss_index' that contains the
        glossed word in such a form that it could be queried
        with the gloss query language.
        Modify the source analysis, do not return anything.
        """
        if 'gloss' not in ana or 'parts' not in ana:
            return
        wordParts = self.rxGlossParts.findall(ana['parts'].replace('{', '(').replace('{', ')'))
        glosses = self.rxGlossParts.findall(ana['gloss'])
        if len(wordParts) <= 0 or len(glosses) == 0 or len(wordParts) != len(glosses):
            self.log_message('Wrong gloss or partitioning: ' + ana['parts'] + ' != ' + ana['gloss'])
            return
        glossIndex = '-'.join(p[1] + '{' + p[0] + '}'
                              for p in zip(wordParts, glosses)) + '-'
        ana['gloss_index'] = glossIndex

    def transform_ana_rnc(self, ana, lang=''):
        """
        Transform analyses for a single word, written in the XML
        format used in Russian National Corpus, into a JSON object.
        """
        setAna = set(self.rxAnalysesRNC.findall(ana.replace('\t', '')))
        analyses = []
        for ana in setAna:
            fields = self.rxAnaFieldRNC.findall(ana)
            if len(fields) <= 0:
                continue
            anaJSON = {}
            for k, v in fields:
                if k == 'gr':
                    anaJSON.update(self.transform_gramm_str(v, lang=lang))
                elif k in self.settings['multivalued_ana_features']:
                    anaJSON[k] = [tag.strip() for tag in v.split()]
                else:
                    anaJSON[k] = v
            self.process_gloss_in_ana(anaJSON)
            analyses.append(anaJSON)
        return analyses

    def load_analyses_xml_rnc(self, text, lang=''):
        """
        Load analyses from a string in the XML format used
        in Russian National Corpus.
        """
        if lang == '':
            if 'languages' in self.settings and len(self.settings['languages']) > 0:
                lang = self.settings['languages'][0]
            else:
                lang = self.settings['corpus_name']
            # there can be several languages if the corpus is parallel
        analyses = self.rxWordsRNC.findall(text)
        if lang not in self.analyses:
            self.analyses[lang] = {}
        iAna = 1
        print('Loading analyses...')
        for ana in analyses:
            if iAna % 20000 == 0:
                print('Loading analysis #' + str(iAna))
            word = ana[1].strip('$&^#%*·;·‒–—―•…‘’‚“‛”„‟"\'')
            if len(word) <= 0:
                continue
            if iAna <= 50000:   # We assume the analyses are ordered by word frequency
                ana = self.transform_ana_rnc(ana[0], lang=lang)
            else:
                ana = ana[0]    # Avoid huge memory consumption at the expense of time
            if word not in self.analyses[lang]:
                self.analyses[lang][word] = ana
            iAna += 1
        print('Analyses for', len(self.analyses[lang]), 'different words loaded.')

    def normalize(self, word):
        """
        Normalize a word before searching for it in the list of analyses.
        """
        return word.strip().lower()

    def analyze_word(self, wf, lang=''):
        if lang not in self.analyses:
            return []
        if wf not in self.analyses[lang] and (wf.startswith('-') or wf.endswith('-')):
            wf = wf.strip('-')
        if wf in self.analyses[lang]:
            ana = self.analyses[lang][wf]
            if type(ana) == str and self.settings['parsed_wordlist_format'] == 'xml_rnc':
                analyses = self.transform_ana_rnc(ana, lang=lang)
            else:
                analyses = copy.deepcopy(self.analyses[lang][wf])
        else:
            analyses = []
        return analyses

    def analyze_hyphened_word(self, words, iWord, lang=''):
        """
        Try to analyze a word that contains a hyphen but could
        not be analyzed as a whole. Split the word in several,
        if needed.
        """
        word = words[iWord]
        parts = self.rxHyphenParts.findall(word['wf'])
        partAnalyses = []
        for iPart in range(len(parts)):
            if parts[iPart].startswith('-'):
                partAnalyses.append(None)
                continue
            wfPart = self.normalize(parts[iPart])
            if iPart > 0:
                wfPart = '-' + wfPart
            if iPart < len(parts) - 1:
                wfPart += '-'
            partAna = self.analyze_word(wfPart, lang)
            partAnalyses.append(partAna)
        if any(pa is not None and len(pa) > 0 for pa in partAnalyses):
            offStart = word['off_start']
            newWords = [copy.deepcopy(word) for i in range(len(partAnalyses))]
            for i in range(len(newWords)):
                newWords[i]['wf'] = parts[i]
                newWords[i]['off_start'] = offStart
                offStart += len(newWords[i]['wf'])
                newWords[i]['off_end'] = offStart
                if i < len(newWords) - 1:
                    newWords[i]['next_word'] = iWord + i + 1
                else:
                    newWords[i]['next_word'] += len(newWords) - 1
                if newWords[i]['wf'].startswith('-'):
                    newWords[i]['wtype'] = 'punct'
                else:
                    newWords[i]['ana'] = partAnalyses[i]
            words.pop(iWord)
            for i in range(len(words)):
                if words[i]['next_word'] > iWord:
                    words[i]['next_word'] += len(newWords) - 1
            for i in range(len(newWords)):
                words.insert(iWord + i, newWords[i])
            # print(words)
            return len(newWords) - 1
        return 0

    def analyze_sentence(self, s, lang=''):
        """
        Analyze each word in one sentence using preloaded analyses.
        Return statistics.
        """
        nTokens, nWords, nAnalyzed = 0, 0, 0
        if lang == '':
            if 'languages' in self.settings and len(self.settings['languages']) > 0:
                lang = self.settings['languages'][0]
            else:
                lang = self.settings['corpus_name']
        if 'words' not in s:
            return 0, 0, 0
        iWord = -1
        while iWord < len(s['words']) - 1:
            iWord += 1
            nTokens += 1
            word = s['words'][iWord]
            if word['wtype'] != 'word':
                continue
            nWords += 1
            wf = self.normalize(word['wf'])
            analyses = self.analyze_word(wf, lang)
            if len(analyses) > 0:
                word['ana'] = analyses
                nAnalyzed += 1
            elif '-' in word['wf']:
                iWord += self.analyze_hyphened_word(s['words'], iWord, lang)
        return nTokens, nWords, nAnalyzed

    def analyze(self, sentences, lang=''):
        """
        Analyze each word in each sentence using preloaded analyses.
        Return statistics.
        """
        nTokens, nWords, nAnalyzed = 0, 0, 0
        if lang == '':
            if 'languages' in self.settings and len(self.settings['languages']) > 0:
                lang = self.settings['languages'][0]
            else:
                lang = self.settings['corpus_name']
        for s in sentences:
            nTokensCur, nWordsCur, nAnalyzedCur = self.analyze_sentence(s, lang)
            nTokens += nTokensCur
            nWords += nWordsCur
            nAnalyzed += nAnalyzedCur
        return nTokens, nWords, nAnalyzed

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
    rxSplitGramTags = re.compile('[,， /=]')
    rxHyphenParts = re.compile('[^\\-]+|-+')
    rxGlossParts = re.compile('\\.\\[[^\\[\\]]+\\]|[^ \\-=<>\\[\\]]*[^ \\-=<>\\[\\].]')
    rxGlossIndexPart = re.compile('^(.*)\\{(.*?)\\}')
    rxBracketGloss = re.compile('[.-]?\\[.*?\\]')

    def __init__(self, settings, categories, errorLog=''):
        self.settings = copy.deepcopy(settings)
        self.categories = copy.deepcopy(categories)
        self.rxAllGlosses = self.prepare_gloss_regex()
        self.analyses = {}
        self.errorLog = errorLog
        self.grammRules = []
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
        self.load_rules()

    def load_rules(self):
        """
        Load rules for converting the glosses into bags of grammatical
        tags.
        """
        self.grammRules = []
        if os.path.exists(os.path.join(self.settings['corpus_dir'], 'conf_conversion')):
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf_conversion/grammRules.txt'))
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf_conversion/gramRules.txt'))  # Backward compatibility
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf_conversion/grammRules.csv'), separator='\t')
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf_conversion/gramRules.csv'), separator='\t')  # Backward compatibility
        else:  # Backward compatibility
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf/grammRules.txt'))
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf/gramRules.txt'))  # Backward compatibility
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf/grammRules.csv'), separator='\t')
            self.load_gramm_rules(os.path.join(self.settings['corpus_dir'],
                                               'conf/gramRules.csv'), separator='\t')  # Backward compatibility

    @staticmethod
    def prepare_rule(rule):
        """
        Make a compiled regex out of a rule represented as a string.
        """

        def replReg(s):
            if "'" in s:
                return ''
            return ' re.search(\'' + s + \
                   '\', ana[\'parts\']) is not None or ' + \
                   're.search(\'' + s + \
                   '\', ana[\'gloss\']) is not None '

        ruleParts = rule.split('"')
        rule = ''
        for i in range(len(ruleParts)):
            if i % 2 == 0:
                rule += re.sub('([^\\[\\]~|& \t\']+)', ' \'\\1\' in tagsAndGlosses ',
                               ruleParts[i]).replace('|', ' or ').replace('&', ' and ') \
                    .replace('~', ' not ').replace('[', '(').replace(']', ')')
            else:
                rule += replReg(ruleParts[i])
        return rule

    def load_gramm_rules(self, fname, separator='->'):
        """
        Load main set of rules for converting the glosses into bags
        of grammatical tags.
        """
        if len(fname) <= 0 or not os.path.isfile(fname):
            return
        rules = []
        f = open(fname, 'r', encoding='utf-8-sig')
        for line in f:
            line = re.sub('#.*', '', line).strip()
            if len(line) > 0:
                rule = [i.strip() for i in line.split(separator)]
                if len(rule) != 2:
                    continue
                rule[1] = set(rule[1].split(','))
                rule[0] = self.prepare_rule(rule[0])
                rules.append(rule)
        f.close()
        self.grammRules += rules

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
                sRegex = '|'.join(re.escape(g) for g in sorted(self.settings['glosses'][lang],
                                                               key=lambda x: -len(x)))
                sRegex = '\\b(' + sRegex + ')\\b'
                regexes[lang] = re.compile(sRegex)
            else:
                sRegex = '|'.join(re.escape(g) for g in sorted(self.categories[lang],
                                                               key=len))
                sRegex = '\\b(' + sRegex + ')\\b'
                regexes[lang] = re.compile(sRegex, flags=re.I)
        return regexes

    def gloss2gr(self, ana, lang, useGlossList=False):
        """
        For an analysis that has glosses, but no tags for inflectional
        categories, add these categories.
        If useGlossList, use the list of glosses to distinguish between
        glosses and stem translations. In the opposite case, consider
        everyjting other than "STEM" a gloss.
        """
        # TODO: Add rules for translating the glosses into tags.
        if 'gloss_index' not in ana:
            return
        if useGlossList:
            glosses = self.rxAllGlosses[lang].findall(ana['gloss_index'])
        else:
            glosses = [self.rxGlossIndexPart.search(g).group(1)
                       for g in self.rxGlossParts.findall(ana['gloss_index'])]
        if 'glosses_covert' in ana:
            glosses += ana['glosses_covert']
            del ana['glosses_covert']
        addedGrammTags = set()
        tagsAndGlosses = set()
        for field in ana:
            if field.startswith('gr.'):
                if type(ana[field]) == str:
                    tagsAndGlosses.add(ana[field])
                elif type(ana[field]) == list:
                    tagsAndGlosses |= set(ana[field])
        tagsAndGlosses |= set(gl.strip('-=:.<>') for gl in glosses)
        if len(self.grammRules) > 0:
            for rule in self.grammRules:
                if eval(rule[0]):
                    addedGrammTags |= rule[1]
        else:
            for gl in glosses:
                if gl.upper() == gl:
                    gl = gl.lower()
                addedGrammTags.add(gl)
        # print(list(addedGrammTags), list(tagsAndGlosses))
        for tag in addedGrammTags:
            if tag in self.categories[lang]:
                anaCatName = 'gr.' + self.categories[lang][tag]
                if anaCatName not in ana:
                    ana[anaCatName] = tag
                else:
                    if type(ana[anaCatName]) == str:
                        ana[anaCatName] = [ana[anaCatName], tag]
                    elif tag not in ana[field]:
                        ana[anaCatName].append(tag)

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

    def process_gloss_in_ana(self, ana, gloss_lang=''):
        """
        If there are fields 'gloss' and 'parts' in the JSON
        analysis, add field 'gloss_index' that contains the
        glossed word in such a form that it could be queried
        with the gloss query language.
        If gloss_lang is not empty, look in fields "gloss_%gloss_lang%"
        etc. instead of just "gloss". This may be needed if
        there are glosses in more than one metalanguage.
        Modify the source analysis, do not return anything.
        """
        if len(gloss_lang) > 0:
            gloss_lang = '_' + gloss_lang
        if 'gloss' + gloss_lang not in ana or 'parts' not in ana:
            return
        wordParts = self.rxGlossParts.findall(ana['parts'].replace('{', '(').replace('{', ')').replace(' ', '.'))
        glosses = self.rxGlossParts.findall(ana['gloss' + gloss_lang])
        glossesOvert = [g for g in glosses if self.rxBracketGloss.search(g) is None]
        glossesCovert = [g.strip('[].') for g in glosses if self.rxBracketGloss.search(g) is not None]
        if len(wordParts) <= 0 or len(glosses) == 0 or len(wordParts) != len(glossesOvert):
            self.log_message('Wrong gloss or partitioning: ' + ana['parts'] + ' != ' + ana['gloss' + gloss_lang])
            return
        glossIndex = '-'.join(p[1] + '{' + p[0] + '}'
                              for p in zip(wordParts, glossesOvert)) + '-'
        ana['gloss_index' + gloss_lang] = glossIndex
        if len(glossesCovert) > 0:
            ana['glosses_covert' + gloss_lang] = glossesCovert

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
        word = word.strip().lower()
        if 'char_replacements' in self.settings:
            wordClean = ''
            for c in word:
                if c in self.settings['char_replacements']:
                    wordClean += self.settings['char_replacements'][c]
                else:
                    wordClean += c
            word = wordClean
        return word

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

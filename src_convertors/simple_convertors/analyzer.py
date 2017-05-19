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

    rxWordsRNC = re.compile('<w>(<ana.*?/(?:ana)>)([^<>]+)</w>', flags=re.DOTALL)
    rxAnalysesRNC = re.compile('<ana *([^<>]+)(?:></ana>|/>)\\s*')
    rxAnaFieldRNC = re.compile('([^ <>"=]+) *= *"([^<>"=]+)')
    rxSplitGramTags = re.compile('[, /]')
    rxHyphenParts = re.compile('[^\\-]+|-+')
    rxGlossParts = re.compile('[^ \\-=<>]+')

    def __init__(self, settings, categories):
        self.settings = copy.deepcopy(settings)
        self.categories = copy.deepcopy(categories)
        self.analyses = {}
        self.load_analyses(os.path.join(self.settings['corpus_dir'],
                                        self.settings['parsed_wordlist_filename']))

    def load_analyses(self, fname):
        """
        Load parsed word list from a file.
        """
        self.analyses = {}
        f = open(fname, 'r', encoding='utf-8-sig')
        text = f.read()
        f.close()
        if self.settings['parsed_wordlist_format'] == 'xml_rnc':
            self.load_analyses_xml_rnc(text)

    def transform_gramm_str(self, grStr):
        """
        Transform a string with gramtags into a JSON object.
        """
        grJSON = {}
        grTags = self.rxSplitGramTags.split(grStr)
        for tag in grTags:
            if tag not in self.categories:
                print('No category for a gramtag:', tag)
                continue
            cat = 'gr.' + self.categories[tag]
            if cat not in grJSON:
                grJSON[cat] = tag
            else:
                if type(grJSON[cat]) != list:
                    grJSON[cat] = [grJSON[cat]]
                if tag not in grJSON[cat]:
                    grJSON[cat].append(tag)
        return grJSON

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
            return
        glossIndex = '-'.join(p[1] + '{' + p[0] + '}'
                              for p in zip(wordParts, glosses))
        ana['gloss_index'] = glossIndex

    def transform_ana_rnc(self, ana):
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
                    anaJSON.update(self.transform_gramm_str(v))
                else:
                    anaJSON[k] = v
            self.process_gloss_in_ana(anaJSON)
            analyses.append(anaJSON)
        return analyses

    def load_analyses_xml_rnc(self, text):
        """
        Load analyses from a string in the XML format used
        in Russian National Corpus.
        """
        analyses = self.rxWordsRNC.findall(text)
        for ana in analyses:
            word = ana[1].strip('$&^#%*·;·‒–—―•…‘’‚“‛”„‟"\'')
            if len(word) <= 0:
                continue
            ana = self.transform_ana_rnc(ana[0])
            if word not in self.analyses:
                self.analyses[word] = ana
        print('Analyses for', len(self.analyses), 'different words loaded.')

    def normalize(self, word):
        """
        Normalize a word before searching for it in the list of analyses.
        """
        return word.strip().lower()

    def analyze_word(self, wf):
        if wf not in self.analyses and (wf.startswith('-') or wf.endswith('-')):
            wf = wf.strip('-')
        if wf in self.analyses:
            analyses = copy.deepcopy(self.analyses[wf])
        else:
            analyses = []
        return analyses

    def analyze_hyphened_word(self, words, iWord):
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
            wfPart = parts[iPart]
            if iPart > 0:
                wfPart = '-' + wfPart
            if iPart < len(parts) - 1:
                wfPart += '-'
            partAna = self.analyze_word(wfPart)
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

    def analyze(self, sentences):
        """
        Analyze each word in each sentence using preloaded analyses.
        Return statistics.
        """
        nTokens, nWords, nAnalyzed = 0, 0, 0
        for s in sentences:
            if 'words' not in s:
                continue
            iWord = -1
            while iWord < len(s['words']) - 1:
                iWord += 1
                nTokens += 1
                word = s['words'][iWord]
                if word['wtype'] != 'word':
                    continue
                nWords += 1
                wf = self.normalize(word['wf'])
                analyses = self.analyze_word(wf)
                if len(analyses) > 0:
                    word['ana'] = analyses
                    nAnalyzed += 1
                elif '-' in word['wf']:
                    iWord += self.analyze_hyphened_word(s['words'], iWord)
        return nTokens, nWords, nAnalyzed

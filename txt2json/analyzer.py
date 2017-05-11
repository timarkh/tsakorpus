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
    rxAnaFieldRNC = re.compile('([^ <>"=]+) *= *"([^ <>"=]+)')
    rxSplitGramTags = re.compile('[, /]')

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
            if self.categories[tag] not in grJSON:
                grJSON[cat] = tag
            else:
                if type(grJSON[cat]) != list:
                    grJSON[cat] = [grJSON[cat]]
                if tag not in grJSON[cat]:
                    grJSON[cat].append(tag)
        return grJSON

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

    def analyze(self, sentences):
        """
        Analyze each word in each sentence using preloaded analyses.
        """
        for s in sentences:
            if 'words' not in s:
                continue
            for word in s['words']:
                if word['wtype'] != 'word':
                    continue
                wf = self.normalize(word['wf'])
                if wf in self.analyses:
                    word['ana'] = copy.deepcopy(self.analyses[wf])
                else:
                    word['ana'] = []


import copy
import html
import shutil
import base64

import elasticsearch
ESVersion = elasticsearch.__version__[0]   # Should be 7 or 9 (or use 8 at your own risk, I didn't test it)

from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import RequestError
import json
import ijson
import os
import re
import time
from datetime import datetime
import math
import random
import sys
import subprocess
import argparse
from prepare_data import PrepareData
from json_doc_reader import JSONDocReader
from json2html import JSON2HTML
from sqlitedict import SqliteDict
import pickle

DEBUG = False
if DEBUG:
    from pympler import asizeof

def sizeof_fmt(num):
    for unit in ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'):
        if abs(num) < 1024.0:
            return f'{num:3.1f} {unit}B'
        num /= 1024.0
    return f'{num:.1f} YB'


class DBDict:
    """
    A class that works like a dictionary, but only stores the data in memory
    until it has maxCount keys. After that, it creates an sqlite database in
    the current working directory and puts all the rest there.
    No methods for sorting or deleting items are implemented. No removal of
    no-longer-needed databases is performed.
    """
    def __init__(self, maxCount=1000000, dbName='tmp', pickleKeys=False):
        self.d = {}
        self.maxCount = maxCount
        self.pickleKeys = pickleKeys
        self.db = None
        self.dbName = dbName + '.sqlite'
        self.l = 0

    def __len__(self):
        return self.l

    def __getitem__(self, item):
        if self.pickleKeys:
            item = pickle.dumps(item)
        try:
            return self.d[item]
        except KeyError:
            if self.db is None:
                raise KeyError('')
            return self.db[item]

    def __setitem__(self, key, value):
        if self.pickleKeys:
            key = pickle.dumps(key)
        if key in self.d:
            self.d[key] = value
            return
        if self.db is not None and key in self.db:
            self.db[key] = value
            return
        self.l += 1
        if self.l <= self.maxCount:
            self.d[key] = value
            return
        if self.db is None:
            self.db = SqliteDict(self.dbName, outer_stack=False)
        self.db[key] = value

    def __iter__(self):
        for k in self.d:
            if self.pickleKeys:
                k = pickle.loads(k)
            yield k
        if self.db is not None:
            for k in self.db:
                if self.pickleKeys:
                    k = pickle.loads(k)
                yield k

    def items(self):
        for k, v in self.d.items():
            if self.pickleKeys:
                k = pickle.loads(k)
            yield k, v
        if self.db is not None:
            for k, v in self.db.items():
                if self.pickleKeys:
                    k = pickle.loads(k)
                yield k, v

    def __contains__(self, item):
        if self.pickleKeys:
            item = pickle.dumps(item)
        if item in self.d:
            return True
        if self.db is not None and item in self.db:
            return True
        return False


class Indexator:
    """
    Contains methods for loading the JSON documents in the corpus
    database.
    """
    SETTINGS_DIR = '../conf'
    MAX_MEM_DICT_SIZE = 100000
    rxBadFileName = re.compile('[^\\w_.-]*', flags=re.DOTALL)

    def __init__(self, overwrite=False):
        random.seed(datetime.now().timestamp())
        self.fulltextDir = '../search/corpus_html'
        self.overwrite = overwrite  # whether to overwrite an existing index without asking
        with open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                  'r', encoding='utf-8') as fSettings:
            self.settings = json.load(fSettings)
        if not self.check_elastic_version():
            return
        self.j2h = JSON2HTML(settings=self.settings)
        self.name = self.settings['corpus_name']
        self.languages = self.settings['languages']
        if len(self.languages) <= 0:
            self.languages = [self.name]
        self.input_format = self.settings['input_format']
        self.corpus_dir = os.path.join('../corpus', self.name)
        self.lowerWf = False
        if 'wf_lowercase' not in self.settings or self.settings['wf_lowercase']:
            self.lowerWf = True
        self.lowerLemma = False
        if 'lemma_lowercase' in self.settings and self.settings['lemma_lowercase']:
            self.lowerLemma = True
        self.iterSent = None
        if self.input_format in ['json', 'json-gzip']:
            self.iterSent = JSONDocReader(format=self.input_format,
                                          settings=self.settings)

        # Make sure only commonly used word fields and those listed
        # in corpus.json get into the words index.
        self.goodWordFields = [
            'lex',          # lemma
            'wf',           # word form (for search)
            'wf_display',   # word form (for display; optional)
            'parts',        # morpheme breaks in the word form
            'gloss',        # glosses (for display)
            'gloss_index',  # glosses (for search)
            'n_ana'         # number of analyses
        ]
        self.additionalWordFields = set()
        self.additionalLemmaFields = set()
        self.excludeFromDict = {}
        self.subcorpora = {}
        if 'word_fields' in self.settings:
            self.additionalWordFields |= set(self.settings['word_fields'])
        if 'word_table_fields' in self.settings:
            self.additionalWordFields |= set(self.settings['word_table_fields'])
        if 'lemma_table_fields' in self.settings:
            self.additionalLemmaFields = set(self.settings['lemma_table_fields'])
        if 'accidental_word_fields' in self.settings:
            self.additionalWordFields -= set(self.settings['accidental_word_fields'])
            self.additionalLemmaFields -= set(self.settings['accidental_word_fields'])
        if 'exclude_from_dict' in self.settings:
            self.excludeFromDict = {k: re.compile(v) for k, v in self.settings['exclude_from_dict'].items()}
        if 'subcorpora' in self.settings:
            self.subcorpora = {k: {param: re.compile('^(' + value + ')$') for param, value in v.items()}
                               for k, v in self.settings['subcorpora'].items()}
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        categories = json.loads(f.read())
        f.close()
        self.goodWordFields += ['gr.' + v for lang in categories
                                for v in categories[lang].values()]
        self.goodWordFields = set(self.goodWordFields)
        self.characterRegexes = {}

        self.pd = PrepareData()

        # Initialize Elasticsearch connection
        self.es = None
        if ESVersion == 9:
            if 'elastic_pwd' not in self.settings:
                if 'ELASTIC_PASSWORD' in os.environ:
                    self.settings['elastic_pwd'] = os.environ['ELASTIC_PASSWORD']
                elif os.path.exists('../search/elastic_pwd'):
                    with open('../search/elastic_pwd', 'r', encoding='utf-8') as fIn:
                        self.settings['elastic_pwd'] = fIn.read()
                else:
                    self.settings['elastic_pwd'] = ''

        if 'elastic_url' in self.settings and len(self.settings['elastic_url']) > 0:
            # Connect to a non-default URL or supply username and password
            if ESVersion == 7:
                self.es = Elasticsearch([self.settings['elastic_url']], timeout=60)
            else:
                if 'elastic_cacert' not in self.settings or len(self.settings['elastic_cacert']) <= 0:
                    self.es = Elasticsearch([self.settings['elastic_url']], request_timeout=60,
                                            basic_auth=(self.settings['elastic_user'], self.settings['elastic_pwd']))
                else:
                    self.es = Elasticsearch([self.settings['elastic_url']], request_timeout=60,
                                            basic_auth=(self.settings['elastic_user'], self.settings['elastic_pwd']),
                                            ca_certs=self.settings['elastic_cacert'])
        else:
            if ESVersion == 7:
                self.es = Elasticsearch(timeout=60)
            else:
                if 'elastic_cacert' not in self.settings or len(self.settings['elastic_cacert']) <= 0:
                    self.es = Elasticsearch("http://localhost:9200", request_timeout=60,
                                            basic_auth=(self.settings['elastic_user'], self.settings['elastic_pwd']))
                else:
                    self.es = Elasticsearch("https://localhost:9200", request_timeout=60,
                                            basic_auth=(self.settings['elastic_user'], self.settings['elastic_pwd']),
                                            ca_certs=self.settings['elastic_cacert'])
        self.es_ic = IndicesClient(self.es)

        self.shuffled_ids = [i for i in range(1, 1000000)]
        random.shuffle(self.shuffled_ids)
        self.shuffled_ids.insert(0, 0)    # id=0 is special and should not change
        self.tmpWordIDs = [DBDict(maxCount=math.ceil(self.MAX_MEM_DICT_SIZE / len(self.languages)),
                                  dbName='tmpWordID_' + str(i))
                           for i in range(len(self.languages))]       # word as JSON -> its integer ID
        self.tmpLemmaIDs = [DBDict(maxCount=math.ceil(self.MAX_MEM_DICT_SIZE / len(self.languages)),
                                   dbName='tmpLemmaID_' + str(i))
                            for i in range(len(self.languages))]      # lemma as string -> its integer ID

        self.tmpID2lemma = [DBDict(maxCount=math.ceil(self.MAX_MEM_DICT_SIZE / len(self.languages)),
                                   dbName='tmpID2lemma_' + str(i))
                            for i in range(len(self.languages))]      # lemma's integer ID -> lemma as string

        # Apart from the two dictionaries above, words and lemmata
        # have string IDs starting with 'w' or 'l' followed by an integer
        self.word2lemma = [{} for i in range(len(self.languages))]    # word/lemma ID -> ID of its lemma (or -1, if none)
        self.wordFreqs = [{} for i in range(len(self.languages))]     # word/lemma ID -> its frequency
        self.wordFreqsSub = [{subcorpus: {} for subcorpus in self.subcorpora}
                             for i in range(len(self.languages))]     # word/lemma ID -> its frequency in a subcorpus
        self.wordSFreqs = [{} for i in range(len(self.languages))]    # word/lemma ID -> its number of sentences
        self.wordDocFreqs = [DBDict(maxCount=math.ceil(self.MAX_MEM_DICT_SIZE / len(self.languages)),
                                    dbName='wordDocFreqs_' + str(i), pickleKeys=True)
                             for i in range(len(self.languages))]        # (word/lemma ID, dID) -> word frequency in the document
        self.curWordDocFreqs = [{} for i in range(len(self.languages))]  # word/lemma ID -> word frequency in current document
        self.wordDIDs = [DBDict(maxCount=math.ceil(self.MAX_MEM_DICT_SIZE / len(self.languages)),
                                dbName='wordDIDs_' + str(i))
                         for i in range(len(self.languages))]        # word/lemma ID -> set of document IDs
        # self.wordSIDs = [{} for i in range(len(self.languages))]       # word's ID -> set of sentence IDs
        # self.wordDIDs = [{} for i in range(len(self.languages))]         # word/lemma ID -> set of document IDs
        self.lexProfiles = {}    # {lang -> {category -> {value -> {lemma ID -> frequency}}}}
        self.initialize_lex_profiles()
        self.wfs = set()           # set of word forms (for sorting)
        self.lemmata = {''}        # set of lemmata (for sorting)
        self.sID = 0          # current sentence ID for each language
        self.dID = 0          # current document ID
        self.wID = 0          # current word ID
        self.wordFreqID = 0   # current word_freq ID for word/document frequencies
        self.lemmaFreqID = 0  # current word_freq ID for lemma/document frequencies
        self.numWords = 0     # number of words in current document
        self.numSents = 0     # number of sentences in current document
        self.numWordsLang = [0] * len(self.languages)    # number of words in each language in current document
        self.numSentsLang = [0] * len(self.languages)    # number of sentences in each language in current document
        self.totalNumWords = 0
        self.sentID = 0
        self.wordsByPartition = {}
        if 'partitions' in self.settings and self.settings['partitions'] > 0:
            self.wordsByPartition = {l: {p: 0 for p in range(int(self.settings['partitions']))}
                                     for l in range(len(self.languages))}

        self.filenames = []   # List of tuples (filename, filesize)
        self.corpusSizeInBytes = 0
        for fname in os.listdir('.'):
            if fname.lower().endswith(('.sqlite', '.sqlite-journal')):
                os.remove(fname)

    def check_elastic_version(self):
        """
        Check if the Elasticsearch has one of the accepted versions
        and if version-specific settings (if any) are provided.
        Return False if something is wrong, True otherwise.
        """
        if ESVersion == 8:
            print('Warning: this Tsakorpus version has not been tested with Elasticsearch 8.x.')
        elif ESVersion not in (7, 9):
            print('Wrong Elasticsearch version:', ESVersion)
            return False
        if ESVersion == 9:
            if 'elastic_pwd' not in self.settings:
                if 'ELASTIC_PASSWORD' in os.environ:
                    self.settings['elastic_pwd'] = os.environ['ELASTIC_PASSWORD']
                elif os.path.exists('../search/elastic_pwd'):
                    with open('../search/elastic_pwd', 'r', encoding='utf-8') as fIn:
                        self.elastic_pwd = fIn.read()
                else:
                    print('With Elasticsearch 9, a password for basic authentication has to be provided.')
                    return False
            if 'elastic_user' not in self.settings:
                self.settings['elastic_user'] = 'elastic'
        return True

    def initialize_lex_profiles(self):
        for lang in self.languages:
            self.lexProfiles[lang] = {}
            if lang in self.settings['lang_props'] and 'lex_profile_categories' in self.settings['lang_props'][lang]:
                for sub in [s for s in self.subcorpora.keys()] + ['_all']:
                    self.lexProfiles[lang][sub] = {}
                    for c in self.settings['lang_props'][lang]['lex_profile_categories']:
                        self.lexProfiles[lang][sub][c] = {'_other': {}}
                        for v in self.settings['lang_props'][lang]['lex_profile_categories'][c]:
                            self.lexProfiles[lang][sub][c][v] = {}  # lemma ID -> frequency

    def delete_indices(self):
        """
        If there already exist indices with the same names,
        ask the user if they want to overwrite them. If they
        say yes, remove the indices and return True. Otherwise,
        return False.
        """
        if not self.overwrite:
            if (self.es_ic.exists(index=self.name + '.docs')
                    or self.es_ic.exists(index=self.name + '.words')
                    or self.es_ic.exists(index=self.name + '.sentences')):
                print('It seems that a corpus named "' + self.name + '" already exists. '
                      + 'Do you want to overwrite it? [y/n]')
                reply = input()
                if reply.lower() != 'y':
                    print('Indexation aborted.')
                    return False
        if self.es_ic.exists(index=self.name + '.docs'):
            self.es_ic.delete(index=self.name + '.docs')
        if self.es_ic.exists(index=self.name + '.words'):
            self.es_ic.delete(index=self.name + '.words')
        if self.es_ic.exists(index=self.name + '.lex_profiles'):
            self.es_ic.delete(index=self.name + '.lex_profiles')
        if self.es_ic.exists(index=self.name + '.sentences*'):
            if self.es_ic.exists(index=self.name + '.sentences'):
                self.es_ic.delete(index=self.name + '.sentences')
            nPartitions = 100
            if 'partitions' in self.settings and int(self.settings['partitions']) > 1:
                nPartitions = int(self.settings['partitions'])
            for i in range(nPartitions):
                if self.es_ic.exists(index=self.name + '.sentences.' + str(i)):
                    self.es_ic.delete(index=self.name + '.sentences.' + str(i))
                else:
                    break
        # Obsolete index word_freq can be present in pre-2019 corpora
        if self.es_ic.exists(index=self.name + '.word_freqs'):
            self.es_ic.delete(index=self.name + '.word_freqs')
        return True

    def create_indices(self):
        """
        Create empty elasticsearch indices for corpus data, using
        mappings provided by PrepareData.
        """
        self.sentWordMapping = self.pd.generate_words_mapping(wordFreqs=False)
        self.wordMapping = self.pd.generate_words_mapping(wordFreqs=True)
        self.docMapping = self.pd.generate_docs_mapping()
        self.sentMapping = self.pd.generate_sentences_mapping(self.sentWordMapping, self.docMapping,
                                                              corpusSizeInBytes=self.corpusSizeInBytes)

        self.es_ic.create(index=self.name + '.docs',
                          mappings=self.docMapping['mappings'],
                          settings=self.docMapping['settings'])
        self.es_ic.create(index=self.name + '.words',
                          mappings=self.wordMapping['mappings'],
                          settings=self.wordMapping['settings'])
        if 'partitions' in self.settings and self.settings['partitions'] > 1:
            for i in range(int(self.settings['partitions'])):
                self.es_ic.create(index=self.name + '.sentences.' + str(i),
                                  body=self.sentMapping)
        else:
            self.es_ic.create(index=self.name + '.sentences',
                          mappings=self.sentMapping['mappings'],
                          settings=self.sentMapping['settings'])

    def randomize_id(self, realID):
        """
        Return a (relatively) randomized sentence ID. This randomization
        is needed in context-aware word queries where the sentences
        are iterated in the order determined by their IDs.
        """
        if realID < 0:
            return realID
        idStart, idEnd = realID // 1000000, realID % 1000000
        return idStart * 1000000 + self.shuffled_ids[idEnd]

    def enhance_word(self, word):
        """
        Add some calculated fields to the JSON word.
        """
        if 'ana' not in word:
            word['n_ana'] = 0
        else:
            word['n_ana'] = len(word['ana'])
            # n_ana is a (signed) byte, so a word can have at most 127 analyses
            if word['n_ana'] >= 127:
                word['n_ana'] = 127

    def clean_word(self, w, langID):
        """
        Clean a word object by removing unnecessary fields, lowercasing
        things if needed, etc. Return the cleaned object and the lemma.
        Return cleaned lemma as a list of objects, one for each analysis
        (or a list with one element that corresponds to an empty lemma
        if there are no analyses). This list can have multiple elements
        if ambiguous_lemma_multiple_count is set.
        Add word form and lemma to the global lists.
        """
        lang = self.settings['languages'][langID]
        wClean = {'lang': langID}
        lClean = [{'lang': langID, 'wf': ''}]
        for field in w:
            if ((field in self.goodWordFields or field in self.additionalWordFields)
                    or (field.endswith('_display')
                        and (field[:-8] in self.goodWordFields or field[:-8] in self.additionalWordFields))):
                wClean[field] = w[field]
                if field == 'wf':
                    if self.lowerWf:
                        wClean[field] = wClean[field].lower()
                    self.wfs.add(wClean[field])
        if 'ana' not in w or len(w['ana']) <= 0:
            return wClean, lClean

        wClean['ana'] = []
        if 'ambiguous_lemma_multiple_count' in self.settings and self.settings['ambiguous_lemma_multiple_count']:
            lClean = []
            wCleanTmp = copy.deepcopy(wClean)
            for ana in w['ana']:
                lClean.append({'lang': langID, 'wf': ''})
                if 'lex' in ana:
                    lClean[-1]['wf'] = ana['lex']
                    if self.lowerLemma:
                        lClean[-1]['wf'] = lClean[-1]['wf'].lower()
                self.lemmata.add(lClean[-1]['wf'])
                cleanAna = {k: copy.deepcopy(v) for k, v in ana.items()
                            if ((k in self.goodWordFields or k in self.additionalWordFields)
                                or (k.endswith('_display')
                                    and (k[:-8] in self.goodWordFields or k[:-8] in self.additionalWordFields)))}
                wCleanTmp['ana'] = [cleanAna]
                wClean['ana'].append(cleanAna)
                grdic, additionalFields = self.get_grdic(wCleanTmp, lang)
                lClean[-1]['grdic'] = grdic
                lClean[-1].update(additionalFields)
        else:
            lClean[0]['wf'] = self.get_lemma(w, lower_lemma=self.lowerLemma)
            self.lemmata.add(lClean[0]['wf'])
            for ana in w['ana']:
                cleanAna = {}
                for anaField in ana:
                    if anaField in self.goodWordFields or anaField in self.additionalWordFields:
                        cleanAna[anaField] = ana[anaField]
                wClean['ana'].append(cleanAna)
            grdic, additionalFields = self.get_grdic(wClean, lang)
            lClean[0]['grdic'] = grdic
            lClean[0].update(additionalFields)
        return wClean, lClean

    def process_sentence_words(self, words, langID, subcorpora=None):
        """
        Take words from a sentence, remove all non-searchable
        fields from them and add them to self.words dictionary.
        Add w_id and l_id properties to each word of the words list.
        Return the value of the 'sent_analyzed' meta field.
        """
        if subcorpora is None:
            subcorpora = []
        sIDAdded = set()            # word IDs for which the current sentence ID has been counted
        bFullyAnalyzed = True       # Whether each word in the sentence is analyzed
        bUniquelyAnalyzed = True    # Whether, in addition, each word has exactly one analysis
        for w in words:
            if w['wtype'] != 'word':
                continue
            self.numWords += 1
            self.numWordsLang[langID] += 1
            self.totalNumWords += 1
            self.enhance_word(w)

            if 'ana' not in w or len(w['ana']) <= 0:
                bFullyAnalyzed = False
                bUniquelyAnalyzed = False
            elif len(w['ana']) > 1:
                bUniquelyAnalyzed = False

            wClean, lClean = self.clean_word(w, langID)

            # Get lID
            lIDs = 'l0'   # Default: no analysis
            # lIDs can be str or list. If there is at most one analysis, then it is a string.
            # If there are more *and* ambiguous_lemma_multiple_count is True, then it is a list.
            for iLemma in range(len(lClean)):
                if len(lClean[iLemma]['wf']) > 0:
                    lCleanTxt = json.dumps(lClean[iLemma], ensure_ascii=False, sort_keys=True)
                    try:
                        lID = 'l' + str(self.tmpLemmaIDs[langID][lCleanTxt])
                    except KeyError:
                        lID = sum(len(self.tmpLemmaIDs[i])
                                  for i in range(len(self.languages))) + 1
                        self.tmpLemmaIDs[langID][lCleanTxt] = lID
                        lID = 'l' + str(lID)
                        self.tmpID2lemma[langID][lID] = lCleanTxt
                    if iLemma < len(w['ana']):
                        # Should be the case
                        w['ana'][iLemma]['l_id'] = lID
                    if iLemma < len(wClean['ana']):
                        # Should be the case
                        wClean['ana'][iLemma]['l_id'] = lID
                    if lIDs == 'l0' or len(lIDs) <= 0:
                        lIDs = lID
                    elif type(lIDs) is str and lIDs != lID:
                        lIDs = [lIDs, lID]
                    elif type(lIDs) is list and lID not in lIDs:
                       lIDs.append(lID)

            # Get wID
            wCleanTxt = json.dumps(wClean, ensure_ascii=False, sort_keys=True)
            if wCleanTxt in self.tmpWordIDs[langID]:
                wID = self.tmpWordIDs[langID][wCleanTxt]
            else:
                wID = sum(len(self.tmpWordIDs[i]) for i in range(len(self.languages)))
                self.tmpWordIDs[langID][wCleanTxt] = wID
            wID = 'w' + str(wID)
            w['w_id'] = wID

            if lIDs != 'l0':
                self.word2lemma[langID][wID] = lIDs
            w['l_id'] = lIDs
            allIDs = [wID]
            if type(lIDs) is str:
                allIDs.append(lIDs)
            else:
                allIDs += lIDs
            for itemID in allIDs:
                try:
                    self.wordFreqs[langID][itemID] += 1
                except KeyError:
                    self.wordFreqs[langID][itemID] = 1
                for sub in subcorpora:
                    try:
                        self.wordFreqsSub[langID][sub][itemID] += 1
                    except KeyError:
                        self.wordFreqsSub[langID][sub][itemID] = 1
                if itemID not in sIDAdded:
                    sIDAdded.add(itemID)
                    try:
                        self.wordSFreqs[langID][itemID] += 1
                    except KeyError:
                        self.wordSFreqs[langID][itemID] = 1
                try:
                    self.curWordDocFreqs[langID][itemID] += 1
                except KeyError:
                    self.curWordDocFreqs[langID][itemID] = 1
        if not bFullyAnalyzed:
            return 'incomplete'
        if not bUniquelyAnalyzed:
            return 'complete'
        return 'unique'

    def character_regex(self, lang):
        """
        Regex for splitting text into characters. Takes into account
        multicharacter sequences (digraphs etc.) defined in lang_props.lexicographic_order.
        """
        if lang in self.characterRegexes:
            return self.characterRegexes[lang]   # cache
        if lang not in self.settings['lang_props'] or 'lexicographic_order' not in self.settings['lang_props'][lang]:
            self.characterRegexes[lang] = re.compile('.')
            return self.characterRegexes[lang]
        rxChars = '(' + '|'.join(re.escape(c.lower())
                                 for c in sorted(self.settings['lang_props'][lang]['lexicographic_order'],
                                                 key=lambda x: (-len(x), x))
                                 if len(c) > 1)
        if len(rxChars) > 1:
            rxChars += '|'
        rxChars += '.)'
        rxChars = re.compile(rxChars)
        self.characterRegexes[lang] = rxChars
        return rxChars

    def make_sorting_function(self, lang):
        """
        Return a function that can be used for sorting tokens
        in a list according to the alphabetical ordering specified
        for the language lang.
        """
        sortingFunction = lambda x: x
        if lang in self.settings['lang_props'] and 'lexicographic_order' in self.settings['lang_props'][lang]:
            dictSort = {self.settings['lang_props'][lang]['lexicographic_order'][i]:
                            (i, self.settings['lang_props'][lang]['lexicographic_order'][i])
                        for i in range(len(self.settings['lang_props'][lang]['lexicographic_order']))}
            maxIndex = len(dictSort)
            rxChars = self.character_regex(lang)

            def charReplaceFunction(c):
                if c in dictSort:
                    return dictSort[c]
                return (maxIndex, c)

            sortingFunction = lambda x: [charReplaceFunction(c) for c in rxChars.findall(x.lower())]
        return sortingFunction

    def make_sorting_function_lex(self, lang, lID2lex, lexFreqs):
        sortingFunctionStr = self.make_sorting_function(lang)
        def sortingFunction(lID):
            lemma = sortingFunctionStr(lID2lex[lID][0].lower())
            grdic = lID2lex[lID][1]
            freq = lexFreqs[lID]
            return lemma, grdic, -freq
        return sortingFunction

    def sort_words(self, lang):
        """
        Sort word forms and lemmata stored at earlier stages.
        Return dictionaries with positions of word forms and
        lemmata in the sorted list.
        If there is a custom alphabetical order for the language,
        use it. Otherwise, use standard lexicographic sorting.
        """
        wfsSorted = {}
        iOrder = 0
        sortingFunction = self.make_sorting_function(lang)
        for wf in sorted(self.wfs, key=sortingFunction):
            wfsSorted[wf] = iOrder
            iOrder += 1
        lemmataSorted = {}
        iOrder = 0
        for l in sorted(self.lemmata, key=sortingFunction):
            lemmataSorted[l] = iOrder
            iOrder += 1
        return wfsSorted, lemmataSorted

    def get_freq_ranks(self, freqsSorted):
        """
        Calculate frequency ranks and rank/quantile labels for words
        or lemmata.
        """
        freqToRank = {}
        quantiles = {}
        prevFreq = 0
        prevRank = 0
        for i in range(len(freqsSorted)):
            v = freqsSorted[i]
            if v != prevFreq:
                if prevFreq != 0:
                    freqToRank[prevFreq] = prevRank + (i - prevRank) // 2
                prevRank = i
                prevFreq = v
        if prevFreq != 0:
            freqToRank[prevFreq] = prevRank + (len(freqsSorted) - prevRank) // 2
        for q in [0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.25, 0.5]:
            qIndex = math.ceil(q * len(freqsSorted))
            if qIndex >= len(freqsSorted):
                qIndex = len(freqsSorted) - 1
            if qIndex >= 0:
                quantiles[q] = freqsSorted[qIndex]
            else:
                quantiles[q] = 0
        return freqToRank, quantiles

    def quantile_label(self, freq, rank, quantiles):
        """
        Return a string label of the frequency rank (for frequent items)
        or quantile. This label is showed to the user in word query results.
        """
        if freq > 1 and freq >= quantiles[0.5]:
            if freq > quantiles[0.03]:
                return '#' + str(rank + 1)
            else:
                return '&gt; ' + str(min(math.ceil(q * 100) for q in quantiles
                                     if freq >= quantiles[q])) + '%'
        return ''

    def get_lemma(self, word, lower_lemma=False):
        """
        Join all lemmas in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        if 'keep_lemma_order' not in self.settings or not self.settings['keep_lemma_order']:
            curLemmata = set()
            for ana in word['ana']:
                if 'lex' in ana:
                    if type(ana['lex']) == list:
                        for l in ana['lex']:
                            lAdd = l
                            if lower_lemma:
                                lAdd = lAdd.lower()
                            curLemmata.add(lAdd)
                    else:
                        lAdd = ana['lex']
                        if lower_lemma:
                            lAdd = lAdd.lower()
                        curLemmata.add(lAdd)
            if 'ambiguous_lemma_multiple_count' in self.settings and self.settings['ambiguous_lemma_multiple_count']:
                return [l for l in sorted(curLemmata)]
            else:
                return '/'.join(l for l in sorted(curLemmata))
        curLemmata = []
        for ana in word['ana']:
            if 'lex' in ana:
                if type(ana['lex']) == list:
                    for l in ana['lex']:
                        lAdd = l
                        if lower_lemma:
                            lAdd = lAdd.lower()
                        curLemmata.append(lAdd)
                else:
                    lAdd = ana['lex']
                    if lower_lemma:
                        lAdd = lAdd.lower()
                    curLemmata.append(lAdd)
        if 'ambiguous_lemma_multiple_count' in self.settings and self.settings['ambiguous_lemma_multiple_count']:
            return curLemmata
        else:
            return '/'.join(curLemmata)

    def get_grdic(self, word, lang):
        """
        Join all dictionary grammar tags strings in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        curGramm = set()
        additionalValues = {}
        for ana in word['ana']:
            grTags = ''
            if 'gr.pos' in ana:
                value = ana['gr.pos']
                if type(value) == list:
                    value = ', '.join(value)
                grTags = value
            for field in sorted(ana):
                value = ana[field]
                if type(value) == list:
                    value = ', '.join(value)
                if ('lang_props' in self.settings
                        and lang in self.settings['lang_props']
                        and 'dictionary_categories' in self.settings['lang_props'][lang]
                        and field.startswith('gr.')
                        and field[3:] in self.settings['lang_props'][lang]['dictionary_categories']):
                    if len(grTags) > 0:
                        grTags += ', '
                    grTags += value
                elif field in self.additionalLemmaFields:
                    if field in additionalValues:
                        additionalValues[field].add(value)
                    else:
                        additionalValues[field] = {value}
            if len(grTags) > 0:
                curGramm.add(grTags)
        grdic = ' | '.join(grdic for grdic in sorted(curGramm))
        for field in additionalValues:
            additionalValues[field] = ' | '.join(av for av in sorted(additionalValues[field])
                                                 if len(av) > 0)
        return grdic, additionalValues

    def get_gramm(self, word, lang, schema, lID=''):
        """
        Join grammar tag strings in the JSON representation of a word with
        an analysis. Only take category or categories listed in the schema.
        The schema string contains either a name of a single category or a list
        of categories separated by a comma. Return the values as a string.
        """
        if 'ana' not in word:
            return ''
        checkLID = ('ambiguous_lemma_multiple_count' in self.settings
                    and self.settings['ambiguous_lemma_multiple_count']
                    and len(lID) > 0)
        categs = schema.strip(' ,').split(',')
        curGramm = set()
        for ana in word['ana']:
            if (checkLID and ('l_id' not in ana or ana['l_id'] != lID)):
                continue
            grTags = {
                c: '' for c in categs
            }
            for field in sorted(ana):
                if not field.startswith('gr.'):
                    continue
                fieldShort = field[3:]
                if fieldShort not in categs:
                    continue
                value = ana[field]
                if type(value) is list:
                    value = '/'.join(value)
                grTags[fieldShort] = value
            curGrammStr = ''
            for c in categs:
                if len(grTags[c]) > 0:
                    if len(curGrammStr) > 0:
                        curGrammStr += ','
                    curGrammStr += grTags[c]
            if len(curGrammStr) > 0:
                curGramm.add(curGrammStr)
        gramm = ' | '.join(g for g in sorted(curGramm))
        return gramm

    def get_lex_profile(self, lID, langID):
        lang = self.languages[langID]
        if lang not in self.lexProfiles:
            return base64.b64encode('{}'.encode('utf-8')).decode('utf-8')
        curProfile = {}
        for sub in self.lexProfiles[lang]:
            curProfile[sub] = {}
            for c in self.lexProfiles[lang][sub]:
                for v in self.lexProfiles[lang][sub][c]:
                    try:
                        cvFreq = self.lexProfiles[lang][sub][c][v][lID]
                    except KeyError:
                        continue
                    if cvFreq > 0:
                        if c not in curProfile[sub]:
                            curProfile[sub][c] = {}
                        curProfile[sub][c][v] = cvFreq
        return base64.b64encode(json.dumps(curProfile,
                                           ensure_ascii=False,
                                           indent=-1,
                                           sort_keys=True).encode('utf-8')).decode('utf-8')

    def word_to_lex_profile(self, w, langID):
        """
        Add information from one word to the lexical profile of the corresponding lemma.
        """
        lang = self.languages[langID]
        lIDs = w['l_id']
        if type(lIDs) is str:
            lIDs = [lIDs]
        freq = {'_all': w['freq']}
        for sub in self.subcorpora:
            k = 'freq_' + sub
            if k in w:
                freq[sub] = w[k]
        for lID in lIDs:
            if lID == 'l0':
                continue
            for sub in self.lexProfiles[lang]:
                for c in self.lexProfiles[lang][sub]:
                    profileGramm = self.get_gramm(w, self.languages[langID], c, lID)
                    if profileGramm in self.lexProfiles[lang][sub][c]:
                        v = profileGramm
                    else:
                        v = '_other'
                    try:
                        self.lexProfiles[lang][sub][c][v][lID] += freq[sub]
                    except KeyError:
                        self.lexProfiles[lang][sub][c][v][lID] = freq[sub]

    def iterate_lemmata(self, langID, lemmataSorted):
        """
        Iterate over all lemmata for one language collected at the
        word iteration stage.
        """
        lFreqsSorted = [self.wordFreqs[langID][itemID]
                        for itemID in self.wordFreqs[langID]
                        if itemID.startswith('l')]
        lFreqsSorted.sort(reverse=True)
        lemmaFreqToRank, quantiles = self.get_freq_ranks(lFreqsSorted)
        iLemma = 0
        for l, lID in self.tmpLemmaIDs[langID].items():
            lID = 'l' + str(lID)
            if iLemma % 250 == 0:
                print('indexing lemma', iLemma)
            lemmaJson = json.loads(l)
            lOrder = lemmataSorted[lemmaJson['wf']]
            lemmaJson.update({
                'wtype': 'lemma',
                'l_order': lOrder,
                'freq': self.wordFreqs[langID][lID],
                'lemma_freq': self.wordFreqs[langID][lID],
                'rank_true': lemmaFreqToRank[self.wordFreqs[langID][lID]],
                'rank': self.quantile_label(self.wordFreqs[langID][lID],
                                            lemmaFreqToRank[self.wordFreqs[langID][lID]],
                                            quantiles),
                'n_sents': self.wordSFreqs[langID][lID],
                'n_docs': len(self.wordDIDs[langID][lID]),
                'freq_join': 'word',
                'lex_profile': self.get_lex_profile(lID, langID)
            })
            for sub in self.subcorpora:
                try:
                    lemmaJson['freq_' + sub] = self.wordFreqsSub[langID][sub][lID]
                    lemmaJson['lemma_freq_' + sub] = self.wordFreqsSub[langID][sub][lID]
                except KeyError:
                    lemmaJson['freq_' + sub] = 0
                    lemmaJson['lemma_freq_' + sub] = 0
            curAction = {
                '_index': self.name + '.words',
                '_id': lID,
                '_source': lemmaJson
            }
            iLemma += 1
            yield curAction

            for docID in self.wordDIDs[langID][lID]:
                lfreqJson = {
                    'wtype': 'word_freq',
                    'l_id': lID,
                    'd_id': docID,
                    'l_order': lOrder,
                    'freq': self.wordDocFreqs[langID][(lID, docID)],
                    'freq_join': {
                        'name': 'word_freq',
                        'parent': lID
                    }
                }
                curAction = {'_index': self.name + '.words',
                             '_id': 'lfreq' + str(self.lemmaFreqID),
                             '_source': lfreqJson,
                             '_routing': lID}
                self.lemmaFreqID += 1
                yield curAction

    def iterate_wfs(self, langID, wfsSorted, lemmataSorted, lemmaFreqToRank):
        print('Processing words in ' + self.languages[langID] + '...')
        wFreqsSorted = [self.wordFreqs[langID][itemID]
                        for itemID in self.wordFreqs[langID]
                        if itemID.startswith('w')]
        wFreqsSorted.sort(reverse=True)
        wordFreqToRank, quantiles = self.get_freq_ranks(wFreqsSorted)
        iWord = 0
        for w, wID in self.tmpWordIDs[langID].items():
            wID = 'w' + str(wID)
            if iWord % 500 == 0:
                print('indexing word', iWord)
            try:
                lIDs = self.word2lemma[langID][wID]
            except KeyError:
                lIDs = 'l0'

            wJson = json.loads(w)
            wJson['id'] = wID
            wfOrder = len(wfsSorted) + 1
            if 'wf' in wJson:
                wfOrder = wfsSorted[wJson['wf']]
            lOrder = len(lemmataSorted) + 1
            if 'ana' in wJson:
                curLemma = self.get_lemma(wJson, lower_lemma=self.lowerLemma)
                if type(curLemma) is str:
                    lOrder = lemmataSorted[curLemma]
                elif len(curLemma) <= 0:
                    lOrder = lemmataSorted['']
                else:
                    lOrder = min(lemmataSorted[l] for l in curLemma)
            wJson['wf_order'] = wfOrder
            wJson['l_order'] = lOrder
            wJson['l_id'] = lIDs
            wJson['freq'] = self.wordFreqs[langID][wID]

            if type(lIDs) is str:
                wJson['lemma_freq'] = self.wordFreqs[langID][lIDs]
            else:
                wJson['lemma_freq'] = max(self.wordFreqs[langID][lID] for lID in lIDs)

            for sub in self.subcorpora:
                try:
                    wJson['freq_' + sub] = self.wordFreqsSub[langID][sub][wID]
                except KeyError:
                    wJson['freq_' + sub] = 0

                if type(lIDs) is str:
                    try:
                        wJson['lemma_freq_' + sub] = self.wordFreqsSub[langID][sub][lIDs]
                    except KeyError:
                        wJson['lemma_freq_' + sub] = 0
                else:
                    try:
                        wJson['lemma_freq_' + sub] = max(self.wordFreqsSub[langID][sub][lID]
                                                         for lID in lIDs if lID in self.wordFreqsSub[langID][sub])
                    except:
                        wJson['lemma_freq_' + sub] = 0
            # wJson['sids'] = [sid for sid in sorted(self.wordSIDs[langID][wID])]
            wJson['dids'] = [did for did in sorted(self.wordDIDs[langID][wID])]
            wJson['n_sents'] = self.wordSFreqs[langID][wID]
            wJson['n_docs'] = len(wJson['dids'])
            wJson['rank_true'] = wordFreqToRank[wJson['freq']]  # for the calculations

            if type(lIDs) is str:
                wJson['lemma_rank_true'] = lemmaFreqToRank[self.wordFreqs[langID][lIDs]]  # for the calculations
            else:
                wJson['lemma_rank_true'] = max(lemmaFreqToRank[self.wordFreqs[langID][lID]] for lID in lIDs)  # for the calculations
            wJson['rank'] = self.quantile_label(wJson['freq'],
                                                wJson['rank_true'],
                                                quantiles)  # for the user
            wJson['freq_join'] = 'word'
            wJson['wtype'] = 'word'
            self.word_to_lex_profile(wJson, langID)
            curAction = {
                '_index': self.name + '.words',
                '_id': wID,
                '_source': wJson
            }
            yield curAction

            for docID in wJson['dids']:
                wfreqJson = {
                    'wtype': 'word_freq',
                    'w_id': wID,
                    'l_id': lIDs,
                    'd_id': docID,
                    'wf_order': wfOrder,
                    'l_order': lOrder,
                    'freq': self.wordDocFreqs[langID][(wID, docID)],
                    'freq_join': {
                        'name': 'word_freq',
                        'parent': wID
                    }
                }
                curAction = {'_index': self.name + '.words',
                             '_id': 'wfreq' + str(self.wordFreqID),
                             '_source': wfreqJson,
                             '_routing': wID}
                self.wordFreqID += 1
                yield curAction
            iWord += 1
            self.wID += 1

    def iterate_words(self):
        """
        Iterate through all words collected at the previous
        stage. Return JSON objects with actions for bulk indexing
        in Elasticsearch.
        """
        self.wID = 0

        for langID in range(len(self.languages)):
            wfsSorted, lemmataSorted = self.sort_words(self.languages[langID])
            lFreqsSorted = [self.wordFreqs[langID][itemID]
                            for itemID in self.wordFreqs[langID]
                            if itemID.startswith('l')]
            lFreqsSorted.sort(reverse=True)
            lemmaFreqToRank, lemmaQuantiles = self.get_freq_ranks(lFreqsSorted)

            for wAction in self.iterate_wfs(langID, wfsSorted, lemmataSorted, lemmaFreqToRank):
                yield wAction
            for lAction in self.iterate_lemmata(langID, lemmataSorted):
                yield lAction
        emptyLemmaJson = {
            'wf': '',
            'wtype': 'lemma',
            'freq': 0,
            'rank_true': -1
        }
        curAction = {
            '_index': self.name + '.words',
            '_id': 'l0',    # l prefix stands for "lemma"
            '_source': emptyLemmaJson
        }
        yield curAction
        self.wfs = None
        self.lemmata = None

    def write_dictionary(self, langID, lexFreqs, lID2lex):
        """
        Write an HTML dictionary based on the frequency data gathered at a previous step.
        """
        lang = self.languages[langID]
        includeLexProfile = ('lang_props' in self.settings and lang in self.settings['lang_props']
                             and 'lex_profile_categories' in self.settings['lang_props'][lang])
        if not os.path.exists('../search/web_app/templates/dictionaries'):
            os.makedirs('../search/web_app/templates/dictionaries')
        with open(os.path.join('../search/web_app/templates/dictionaries',
                               'dictionary_' + self.settings['corpus_name'] + '_' + lang + '.html'),
                  'w', encoding='utf-8') as fOut:
            fOut.write('<h1 class="dictionary_header"> {{ _(\'Dictionary_header\') }} '
                       '({{ _(\'langname_' + lang + '\') }})</h1>\n')
            prevLetter = ''
            sortingFunction = self.make_sorting_function_lex(lang, lID2lex, lexFreqs)
            for lID in sorted(lexFreqs, key=sortingFunction):
                lemma, grdic, additionalFields = lID2lex[lID]
                if len(lemma) <= 0:
                    continue
                curSubcorpora = [sub for sub in self.subcorpora
                                 if lID in self.wordFreqsSub[langID][sub] and self.wordFreqsSub[langID][sub][lID] > 0]
                additionalFieldsJson = json.loads(additionalFields)
                mChar = self.character_regex(lang).search(lemma.lower())
                if mChar is None:
                    curLetter = '*'
                else:
                    curLetter = mChar.group(0)
                if curLetter != prevLetter:
                    if prevLetter != '':
                        fOut.write('</tbody>\n</table>\n')
                    fOut.write('<h2 class="dictionary_letter">' + curLetter.upper() + '</h2>\n')
                    fOut.write('<table class="dictionary_table">\n<thead>\n'
                               '<th>{{ _(\'word_th_lemma\') }}</th>'
                               '<th>{{ _(\'word_th_gr\') }}</th>')
                    for field in sorted(self.additionalLemmaFields):
                        fOut.write('<th>{{ _(\'word_th_' + html.escape(field) + '\') }}</th>')
                    if len(self.subcorpora) > 0:
                        fOut.write('<th>{{ _(\'Subcorpus\') }}</th>')
                    fOut.write('<th>{{ _(\'word_th_frequency\') }}</th>')
                    if includeLexProfile:
                        fOut.write('<th>{{ _(\'Profile\') }}</th>')
                    fOut.write('</thead>\n<tbody>\n')
                    prevLetter = curLetter
                fOut.write('<tr>\n<td class="dictionary_lemma">' + lemma + '</td><td>' + grdic + '</td>')
                for field in sorted(self.additionalLemmaFields):
                    if field in additionalFieldsJson:
                        fOut.write('<td>' + html.escape(additionalFieldsJson[field]) + '</td>')
                    else:
                        fOut.write('<td></td>')
                if len(self.subcorpora) > 0:
                    if len(curSubcorpora) == 1:
                        fOut.write('<td><div class="circle subcorpus_' + curSubcorpora[0]
                                   + '" data-tooltip="tooltip" data-placement="bottom" title="" '
                                     'data-bs-original-title="Subcorpus: metavalue_' + curSubcorpora[0]
                                   + '"> </div></td>')
                    else:
                        fOut.write('<td></td>')
                fOut.write('<td>' + str(lexFreqs[lID]) + '</td>')
                if includeLexProfile:
                    fOut.write('<td><a class="bi bi-activity lex_profile_link"'
                               ' href="get_lex_profile/' + lang + '/' + lID + '"'
                               ' target="_blank" title="{{ _(\'Lexical profile\') }}"> </a></td>')
                fOut.write('</tr>\n')
            if prevLetter != '':
                fOut.write('</tbody>\n</table>\n')

    def generate_dictionary(self):
        """
        For each language, save an HTML dictionary containing all lexemes of the corpus.
        """
        for langID in range(len(self.languages)):
            lang = self.languages[langID]
            iWord = 0
            print('Generating dictionary for ' + lang + '...')
            lexFreqs = {}            # lemma ID -> its frequency
            lID2lex = {}             # lemma ID -> its features as JSON
            wFreqsSorted = [v for v in sorted(self.wordFreqs[langID].values(), reverse=True)]
            freqToRank, quantiles = self.get_freq_ranks(wFreqsSorted)
            # for wID in self.wordFreqs[langID]:
            for w, wID in self.tmpWordIDs[langID].items():
                wID = 'w' + str(wID)
                if iWord % 1000 == 0:
                    print('processing word', iWord, 'for the dictionary')
                iWord += 1
                wJson = json.loads(w)
                if 'ana' not in wJson or len(wJson['ana']) <= 0:
                    continue
                excludeWord = False
                for ana in wJson['ana']:
                    if any(k in ana and ((type(ana[k]) == str and v.search(ana[k]) is not None)
                                           or (type(ana[k]) == list and any(v.search(anaVPart) is not None for anaVPart in ana[k])))
                           for k, v in self.excludeFromDict.items()):
                        excludeWord = True
                        break
                if excludeWord:
                    continue
                wordFreq = self.wordFreqs[langID][wID]

                try:
                    lIDs = self.word2lemma[langID][wID]
                except KeyError:
                    lIDs = 'l0'
                if type(lIDs) is str:
                    lIDs = [lIDs]
                for lID in lIDs:
                    if lID == 'l0':
                        continue
                    lemma = ''
                    grdic = ''
                    additionalFields = {}
                    try:
                        lexeme = json.loads(self.tmpID2lemma[langID][lID])
                    except KeyError:
                        # This should not happen
                        continue
                    for k, v in lexeme.items():
                        if k == 'wf':
                            lemma = v
                        elif k == 'grdic':
                            grdic = v
                        else:
                            additionalFields[k] = v
                    lexTuple = (lemma, grdic,
                                json.dumps(additionalFields, indent=0, ensure_ascii=False, sort_keys=True))
                    lID2lex[lID] = lexTuple
                    # Lexeme frequency
                    if lID not in lexFreqs:
                        lexFreqs[lID] = wordFreq
                    else:
                        lexFreqs[lID] += wordFreq
            if len(lexFreqs) <= 0:
                continue
            self.write_dictionary(langID, lexFreqs, lID2lex)

    def index_words(self):
        """
        Index all words that have been collected at the previous stage
        in self.words (while the sentences were being indexed).
        """
        bulk(self.es, self.iterate_words(), chunk_size=1000, request_timeout=120)
        if 'generate_dictionary' in self.settings and self.settings['generate_dictionary']:
            self.generate_dictionary()

    def add_parallel_sids(self, sentences, paraIDs):
        """
        In the parallel corpus, add the IDs of aligned sentences in other languages
        to each sentence that has a para_id.
        """
        for s in sentences:
            if 'para_alignment' not in s['_source'] or 'lang' not in s['_source']:
                continue
            langID = s['_source']['lang']
            for pa in s['_source']['para_alignment']:
                paraID = pa['para_id']
                pa['sent_ids'] = []
                for i in range(len(self.languages)):
                    if i == langID:
                        continue
                    if paraID in paraIDs[i]:
                        pa['sent_ids'] += paraIDs[i][paraID]

    def which_subcorpora(self, meta):
        """
        If there are subcorpora set, check if document with this metadata
        belongs to any of them. Return a list of subcorpus labels.
        """
        subcorpora = []
        for sub, rules in self.subcorpora.items():
            bMatch = True
            for field, rule in rules.items():
                if field not in meta:
                    bMatch = False
                    break
                values = meta[field]
                if type(values) is not list:
                    values = [values]
                if all(rule.search(v) is None for v in values):
                    bMatch = False
                    break
            if bMatch:
                subcorpora.append(sub)
        return subcorpora

    def iterate_sentences(self, fname):
        curSentID = 0
        docMeta = self.iterSent.get_metadata(fname)
        subcorpora = self.which_subcorpora(docMeta)
        bFulltextEnabled = False
        bSentIDSortEnabled = False
        if ('fulltext_view_enabled' in self.settings
                and self.settings['fulltext_view_enabled']
                and 'fulltext_id' in docMeta):
            bFulltextEnabled = True
        if ('sent_id_sort_enabled' in self.settings
                and self.settings['sent_id_sort_enabled']):
            bSentIDSortEnabled = True

        if 'doc_to_sentence_meta' in self.settings:
            self.add_meta_keywords(docMeta)
            docMeta = {k: v for k, v in docMeta.items()
                       if (k in self.settings['doc_to_sentence_meta']
                           or (k.endswith('_kw') and k[:-3] in self.settings['doc_to_sentence_meta']))}
        else:
            docMeta = {}
        self.numSents = 0
        prevLast = False
        sentences = []
        paraIDs = [{} for i in range(len(self.languages))]
        self.curWordDocFreqs = [{} for i in range(len(self.languages))]
        for s, bLast in self.iterSent.get_sentences(fname):
            sRandomID = self.randomize_id(self.sID)

            if 'lang' in s:
                langID = s['lang']
            else:
                langID = 0
                s['lang'] = langID
            s['n_words'] = 0

            if bSentIDSortEnabled:
                s['sent_id'] = self.sentID      # unique for the entire corpus (unlike sent_id_local)
                self.sentID += 1

            if 'meta' in s:
                self.add_meta_keywords(s['meta'])
            if len(docMeta) > 0:
                if 'meta' not in s:
                    s['meta'] = copy.deepcopy(docMeta)
                else:
                    for k, v in docMeta.items():
                        if k not in s['meta']:
                            s['meta'][k] = v
            if 'words' in s:
                sentAnaMeta = self.process_sentence_words(s['words'], langID, subcorpora)
                s['n_words'] = sum(1 for w in s['words'] if 'wtype' in w and w['wtype'] == 'word')
                if 'meta' not in s:
                    s['meta'] = {}
                s['meta']['sent_analyses'] = sentAnaMeta
            if prevLast:
                prevLast = False
            elif self.numSents > 0:
                s['prev_id'] = self.randomize_id(self.sID - 1)
            if not bLast and 'last' not in s:
                s['next_id'] = self.randomize_id(self.sID + 1)
            else:
                prevLast = True
            s['doc_id'] = self.dID
            if 'meta' in s:
                for metaField in [mf for mf in s['meta'].keys() if not (mf.startswith('year') or mf.endswith('_kw'))]:
                    s['meta'][metaField + '_kw'] = s['meta'][metaField]

            indexName = self.name + '.sentences'
            iPart = 0       # split a large corpus into partitions for faster (and less precise) queries
            if 'partitions' in self.settings and self.settings['partitions'] > 1:
                smallPartitions = [p for p in sorted(self.wordsByPartition[langID],
                                                     key=lambda x: self.wordsByPartition[langID][x])][:2]
                iPart = random.choice(smallPartitions)
                self.wordsByPartition[langID][iPart] += s['n_words']
                indexName += '.' + str(iPart)
            curAction = {'_index': indexName,
                         '_id': sRandomID,
                         '_source': s}
            if len(self.languages) <= 1:
                yield curAction
            else:
                sentences.append(curAction)
                if 'para_alignment' in s:
                    s['para_ids'] = []
                    for pa in s['para_alignment']:
                        paraID = str(self.dID) + '_' + str(pa['para_id'])
                        pa['para_id'] = paraID
                        s['para_ids'].append(paraID)
                        try:
                            paraIDs[langID][paraID].append(self.randomize_id(self.sID))
                        except KeyError:
                            paraIDs[langID][paraID] = [self.randomize_id(self.sID)]
            if self.sID % 500 == 0:
                print('Indexing sentence', self.sID, ',', self.totalNumWords, 'words so far.')
            self.numSents += 1
            self.numSentsLang[langID] += 1
            self.sID += 1
        if len(self.languages) > 1:
            self.add_parallel_sids(sentences, paraIDs)
            for s in sentences:
                yield s
        for langID in range(len(self.languages)):
            for itemID, freq in self.curWordDocFreqs[langID].items():
                try:
                    self.wordDIDs[langID][itemID].add(self.dID)
                except KeyError:
                    self.wordDIDs[langID][itemID] = {self.dID}
                self.wordDocFreqs[langID][(itemID, self.dID)] = freq

    def index_sentences(self, fname):
        """
        Index all sentences in a text.
        """
        bulk(self.es, self.iterate_sentences(fname), chunk_size=1000, request_timeout=120)

    def add_meta_keywords(self, meta):
        """
        For each text field in the metadata, add a keyword version
        of the same field.
        """
        for field in [k for k in meta.keys()
                      if not (k.startswith('year')
                              or ('integer_meta_fields' in self.settings
                                  and meta in self.settings['integer_meta_fields']))]:
            meta[field + '_kw'] = meta[field]

    def index_doc(self, fname):
        """
        Store the metadata of the source file.
        """
        if self.dID % 100 == 0:
            print('Indexing document', self.dID)
        meta = self.iterSent.get_metadata(fname)
        self.add_meta_keywords(meta)
        meta['n_words'] = self.numWords
        meta['n_sents'] = self.numSents
        meta['doc_id'] = self.dID
        if len(self.settings['languages']) > 1:
            for i in range(len(self.languages)):
                meta['n_words_' + self.languages[i]] = self.numWordsLang[i]
                meta['n_sents_' + self.languages[i]] = self.numSentsLang[i]
        self.numWords = 0
        self.numSents = 0
        self.numWordsLang = [0] * len(self.languages)
        self.numSentsLang = [0] * len(self.languages)

        if ('fulltext_view_enabled' in self.settings
                and self.settings['fulltext_view_enabled']
                and 'fulltext_id' in meta):
            fnameOut = meta['fulltext_id'] + '.json'
            self.j2h.process_file(fname,
                                  os.path.join(self.fulltextDir,
                                               self.name,
                                               fnameOut))
        curAction = {'_index': self.name + '.docs',
                     '_id': self.dID,
                     '_source': meta}
        # try:
        #     self.es.index(index=self.name + '.docs',
        #                   id=self.dID,
        #                   body=meta)
        # except RequestError as err:
        #     print('Metadata error: {0}'.format(err))
        #     shortMeta = {}
        #     if 'filename' in meta:
        #         shortMeta['filename'] = meta['filename']
        #     if 'title' in meta:
        #         shortMeta['title'] = meta['title']
        #         shortMeta['title_kw'] = meta['title']
        #         self.es.index(index=self.name + '.docs',
        #                       id=self.dID,
        #                       body=shortMeta)
        self.dID += 1
        return curAction

    def iterate_docs(self):
        for fname, fsize in sorted(self.filenames, key=lambda p: -p[1]):
            # print(fname, fsize)
            if 'sample_size' in self.settings and 0 < self.settings['sample_size'] < 1:
                # Only take a random sample of the source files (for test purposes)
                if random.random() > self.settings['sample_size']:
                    continue
            meta = self.iterSent.get_metadata(fname)
            if self.exclude_text(meta):
                print('Document excluded by meta:', fname)
                continue
            self.index_sentences(fname)
            yield self.index_doc(fname)

    def exclude_text(self, meta):
        """
        Check if the file should be excluded from output based on the
        metadata rules specified in "exclude_by_meta" in corpus.json.
        """
        if 'exclude_by_meta' not in self.settings:
            return False
        for rule in self.settings['exclude_by_meta']:
            if all(k in meta and meta[k] == rule[k] for k in rule):
                return True
        return False

    def analyze_dir(self):
        """
        Collect all filenames for subsequent indexing and calculate
        their total size. Store them as object properties.
        """
        self.filenames = []
        self.corpusSizeInBytes = 0
        for root, dirs, files in os.walk(self.corpus_dir):
            for fname in files:
                if (not ((self.settings['input_format'] == 'json'
                          and fname.lower().endswith('.json'))
                         or (self.settings['input_format'] == 'json-gzip'
                             and fname.lower().endswith('.json.gz')))):
                    continue
                fnameFull = os.path.join(root, fname)
                fileSize = os.path.getsize(fnameFull)
                self.corpusSizeInBytes += fileSize
                self.filenames.append((fnameFull, fileSize))

    def index_dir(self):
        """
        Index all files from the corpus directory, sorted by their size
        in decreasing order. Use a previously collected list of filenames
        and filesizes. Such sorting helps prevent memory errors
        when indexing large corpora, as the default behavior is to load
        the whole file is into memory, and there is more free memory
        in the beginning of the process. If MemoryError occurs, the
        iterative JSON parser is used, which works much slower.
        """
        if len(self.filenames) <= 0:
            print('There are no files in this corpus.')
            return
        bulk(self.es, self.iterate_docs(), chunk_size=200, request_timeout=60)
        self.index_words()

    def compile_translations(self):
        """
        Compile flask_babel translations in ../search/web_app.
        """
        pythonPath = ''
        for p in sys.path:
            if re.search('Python3[^/\\\\]*[/\\\\]?$', p) is not None:
                pythonPath = p
                break
        if len(pythonPath) <= 0:
            pyBabelPath = 'pybabel'
        else:
            pyBabelPath = os.path.join(pythonPath, 'Scripts', 'pybabel')
        try:
            subprocess.run([pyBabelPath, 'compile',  '-d', 'translations_pybabel'], cwd='../search/web_app', check=True)
        except:
            print('Could not compile translations with ' + pyBabelPath + ' .')
        else:
            print('Interface translations compiled.')

    def clean_dirs(self):
        """
        Flush contents of all directories whose content should be generated
        again.
        """
        if ('fulltext_view_enabled' in self.settings
                and self.settings['fulltext_view_enabled']):
            if os.path.exists(self.fulltextDir):
                shutil.rmtree(self.fulltextDir)
            os.makedirs(self.fulltextDir)

    def load_corpus(self):
        """
        Drop the current database, if any, and load the entire corpus.
        """
        t1 = time.time()
        # self.compile_translations()
        indicesDeleted = self.delete_indices()
        if not indicesDeleted:
            return
        self.analyze_dir()
        self.create_indices()
        self.clean_dirs()
        self.index_dir()
        t2 = time.time()
        print('Corpus indexed in', t2-t1, 'seconds:',
              self.dID, 'documents,',
              self.sID, 'sentences,',
              self.totalNumWords, 'words,',
              sum(len(self.wordFreqs[i]) for i in range(len(self.languages))), 'word types (different words).')
        if DEBUG:
            print('*** Memory usage: ***')
            for k, v in sorted(self.__dict__.items(), key=lambda x: (-asizeof.asizeof(x[1]), x[0])):
                if type(v) not in (bool, str, int, float, None):
                    print(k + ': ' + sizeof_fmt(asizeof.asizeof(v)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Index corpus in Elasticsearch 7.x.')
    parser.add_argument('-y', help='overwrite existing database without asking first')
    args = parser.parse_args()
    overwrite = False
    if args.y is not None:
        overwrite = True
    x = Indexator(overwrite)
    x.load_corpus()

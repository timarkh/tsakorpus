from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import RequestError
import json
import ijson
import os
import time
import math
from prepare_data import PrepareData
from json_doc_reader import JSONDocReader


class Indexator:
    """
    Contains methods for loading the JSON documents in the corpus
    database.
    """
    SETTINGS_DIR = '../conf'

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.languages = self.settings['languages']
        if len(self.languages) <= 0:
            self.languages = [self.name]
        self.input_format = self.settings['input_format']
        self.corpus_dir = os.path.join('../corpus', self.name)
        self.iterSent = None
        if self.input_format in ['json', 'json-gzip']:
            self.iterSent = JSONDocReader(format=self.input_format)
        self.goodWordFields = ['lex', 'wf', 'parts', 'gloss', 'gloss_index', 'n_ana', 'trans_en', 'trans_ru']
        self.AdditionalWordFields = []
        if 'word_fields' in self.settings:
            self.AdditionalWordFields = self.settings['word_fields']
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        categories = json.loads(f.read())
        self.goodWordFields += ['gr.' + v for lang in categories
                                for v in categories[lang].values()]
        self.goodWordFields = set(self.goodWordFields)
        f.close()
        self.pd = PrepareData()
        self.es = Elasticsearch()
        self.es_ic = IndicesClient(self.es)
        self.tmpWordIDs = [{} for i in range(len(self.languages))]    # word as JSON -> its integer ID
        self.wordFreqs = [{} for i in range(len(self.languages))]     # word's ID -> its frequency
        self.wordSFreqs = [{} for i in range(len(self.languages))]     # word's ID -> its number of sentences
        self.wordDocFreqs = [{} for i in range(len(self.languages))]  # (word's ID, dID) -> word frequency in the document
        # self.wordSIDs = [{} for i in range(len(self.languages))]      # word's ID -> set of sentence IDs
        self.wordDIDs = [{} for i in range(len(self.languages))]      # word's ID -> set of document IDs
        self.wfs = set()         # set of word forms (for sorting)
        self.lemmata = set()     # set of lemmata (for sorting)
        self.sID = 0          # current sentence ID for each language
        self.dID = 0          # current document ID
        self.numWords = 0     # number of words in current document
        self.numSents = 0     # number of sentences in current document
        self.numWordsLang = [0] * len(self.languages)    # number of words in each language in current document
        self.numSentsLang = [0] * len(self.languages)    # number of sentences in each language in current document
        self.totalNumWords = 0

    def delete_indices(self):
        if self.es_ic.exists(index=self.name + '.docs'):
            self.es_ic.delete(index=self.name + '.docs')
        if self.es_ic.exists(index=self.name + '.words'):
            self.es_ic.delete(index=self.name + '.words')
        if self.es_ic.exists(index=self.name + '.word_freqs'):
            self.es_ic.delete(index=self.name + '.word_freqs')
        if self.es_ic.exists(index=self.name + '.sentences'):
            self.es_ic.delete(index=self.name + '.sentences')

    def create_indices(self):
        self.wordMapping = self.pd.generate_words_mapping()
        self.wordFreqMapping = self.pd.generate_wordfreq_mapping()
        self.sentMapping = self.pd.generate_sentences_mapping(self.wordMapping)
        self.docMapping = self.pd.generate_docs_mapping()
        self.es_ic.create(index=self.name + '.docs',
                          body=self.docMapping)
        self.es_ic.create(index=self.name + '.words',
                          body=self.wordMapping)
        self.es_ic.create(index=self.name + '.sentences',
                          body=self.sentMapping)

    def enhance_word(self, word):
        """
        Add some calculated fields to the JSON word.
        """
        if 'ana' not in word:
            word['n_ana'] = 0
        else:
            word['n_ana'] = len(word['ana'])
            if word['n_ana'] >= 255:
                word['n_ana'] = 255

    def process_sentence_words(self, words, langID):
        """
        Take words list from a sentence, remove all non-searchable
        fields from them and add them to self.words dictionary.
        Add w_id property to each word of the words list.
        """
        sIDAdded = set()   # word IDs for which the current settence ID has been counted for it
        for w in words:
            if w['wtype'] != 'word':
                continue
            self.numWords += 1
            self.numWordsLang[langID] += 1
            self.totalNumWords += 1
            self.enhance_word(w)
            wClean = {'lang': langID}
            for field in w:
                if field in self.goodWordFields:
                    wClean[field] = w[field]
                    if field == 'wf':
                        wClean[field] = wClean[field].lower()
                        self.wfs.add(wClean[field])
            if 'ana' in w:
                self.lemmata.add(self.get_lemma(w))
                wClean['ana'] = []
                for ana in w['ana']:
                    cleanAna = {}
                    for anaField in ana:
                        if anaField in self.goodWordFields:
                            cleanAna[anaField] = ana[anaField]
                    wClean['ana'].append(cleanAna)
            wCleanTxt = json.dumps(wClean, ensure_ascii=False, sort_keys=True)
            if wCleanTxt in self.tmpWordIDs[langID]:
                wID = self.tmpWordIDs[langID][wCleanTxt]
            else:
                wID = len(self.tmpWordIDs[langID])
                self.tmpWordIDs[langID][wCleanTxt] = wID
            w['w_id'] = wID

            try:
                self.wordFreqs[langID][wID] += 1
            except KeyError:
                self.wordFreqs[langID][wID] = 1
            if wID not in sIDAdded:
                sIDAdded.add(wID)
                try:
                    self.wordSFreqs[langID][wID] += 1
                except KeyError:
                    self.wordSFreqs[langID][wID] = 1
            try:
                self.wordDIDs[langID][wID].add(self.dID)
            except KeyError:
                self.wordDIDs[langID][wID] = {self.dID}
            try:
                self.wordDocFreqs[langID][(wID, self.dID)] += 1
            except KeyError:
                self.wordDocFreqs[langID][(wID, self.dID)] = 1

    def sort_words(self):
        """
        Sort word forms and lemmata stored at earlier stages.
        Return dictionaries with positions of word forms and
        lemmata in the sorted list. Delete the original lists.
        """
        wfsSorted = {}
        iOrder = 0
        for wf in sorted(self.wfs):
            wfsSorted[wf] = iOrder
            iOrder += 1
        self.wfs = None
        lemmataSorted = {}
        iOrder = 0
        for l in sorted(self.lemmata):
            lemmataSorted[l] = iOrder
            iOrder += 1
        self.lemmata = None
        return wfsSorted, lemmataSorted

    def get_lemma(self, word):
        """
        Join all lemmata in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        curLemmata = set()
        for ana in word['ana']:
            if 'lex' in ana:
                curLemmata.add(ana['lex'].lower())
        return '/'.join(l for l in sorted(curLemmata))

    def iterate_words(self):
        """
        Iterate through all words collected at the previous
        stage. Return JSON objects with actions for bulk indexing
        in Elasticsearch.
        """
        iWord = 0
        freqsSorted = [[v for v in sorted(self.wordFreqs[langID].values(), reverse=True)]
                       for langID in range(len(self.languages))]
        wfsSorted, lemmataSorted = self.sort_words()

        for langID in range(len(self.languages)):
            quantiles = {}
            for q in [0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.25, 0.5]:
                qIndex = math.ceil(q * len(freqsSorted[langID]))
                if qIndex >= len(freqsSorted[langID]):
                    qIndex = len(freqsSorted[langID]) - 1
                quantiles[q] = freqsSorted[langID][qIndex]
            # for wID in self.wordFreqs[langID]:
            for w, wID in self.tmpWordIDs[langID].items():
                if iWord % 500 == 0:
                    print('indexing word', iWord)
                wJson = json.loads(w)
                wfOrder = len(wfsSorted) + 1
                if 'wf' in wJson:
                    wfOrder = wfsSorted[wJson['wf']]
                lOrder = len(lemmataSorted) + 1
                if 'ana' in wJson:
                    lOrder = lemmataSorted[self.get_lemma(wJson)]
                wJson['wf_order'] = wfOrder
                wJson['l_order'] = lOrder
                wJson['freq'] = self.wordFreqs[langID][wID]
                # wJson['sids'] = [sid for sid in sorted(self.wordSIDs[langID][wID])]
                wJson['dids'] = [did for did in sorted(self.wordDIDs[langID][wID])]
                wJson['n_sents'] = self.wordSFreqs[langID][wID]
                wJson['n_docs'] = len(wJson['dids'])
                wJson['rank'] = ''
                if wJson['freq'] > 1:
                    if wJson['freq'] > quantiles[0.03]:
                        wJson['rank'] = '#' + str(freqsSorted[langID].index(wJson['freq']) + 1)
                    else:
                        wJson['rank'] = '&gt; ' + str(min(math.ceil(q * 100) for q in quantiles
                                                      if wJson['freq'] >= quantiles[q])) + '%'
                curAction = {'_index': self.name + '.words',
                             '_type': 'word',
                             '_id': iWord,
                             '_source': wJson}
                yield curAction

                for docID in wJson['dids']:
                    wfreqJson = {'w_id': iWord,
                                 'd_id': docID,
                                 'wf_order': wfOrder,
                                 'l_order': lOrder,
                                 'freq': self.wordDocFreqs[langID][(wID, docID)]}
                    curAction = {'_index': self.name + '.words',
                                 '_type': 'word_freq',
                                 '_source': wfreqJson,
                                 '_parent': iWord}
                    yield curAction
                iWord += 1

    def index_words(self):
        """
        Index all words that have been collected at the previous stage
        in self.words (while the sentences were being indexed).
        """
        bulk(self.es, self.iterate_words(), chunk_size=300)

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

    def iterate_sentences(self, fname):
        self.numSents = 0
        sentences = []
        paraIDs = [{} for i in range(len(self.languages))]
        for s, bLast in self.iterSent.get_sentences(fname):
            if 'lang' in s:
                langID = s['lang']
            else:
                langID = 0
                s['lang'] = langID
            if 'words' in s:
                self.process_sentence_words(s['words'], langID)
            if self.numSents > 0:
                s['prev_id'] = self.sID - 1
            if not bLast and 'last' not in s:
                s['next_id'] = self.sID + 1
            s['doc_id'] = self.dID
            # self.es.index(index=self.name + '.sentences',
            #               doc_type='sentence',
            #               id=self.sID,
            #               body=s)
            curAction = {'_index': self.name + '.sentences',
                         '_type': 'sentence',
                         '_id': self.sID,
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
                            paraIDs[langID][paraID].append(self.sID)
                        except KeyError:
                            paraIDs[langID][paraID] = [self.sID]
            if self.sID % 500 == 0:
                print('Indexing sentence', self.sID, ',', self.totalNumWords, 'words so far.')
            self.numSents += 1
            self.numSentsLang[langID] += 1
            self.sID += 1
        if len(self.languages) > 1:
            self.add_parallel_sids(sentences, paraIDs)
            for s in sentences:
                yield s

    @staticmethod
    def add_meta_keywords(meta):
        """
        For each text field in the metadata, add a keyword version
        of the same field.
        """
        for field in [k for k in meta.keys() if not k.startswith('year')]:
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
        if len(self.settings['languages']) > 1:
            for i in range(len(self.languages)):
                meta['n_words_' + self.languages[i]] = self.numWordsLang[i]
                meta['n_sents_' + self.languages[i]] = self.numSentsLang[i]
        self.numWords = 0
        self.numSents = 0
        self.numWordsLang = [0] * len(self.languages)
        self.numSentsLang = [0] * len(self.languages)
        try:
            self.es.index(index=self.name + '.docs',
                          doc_type='doc',
                          id=self.dID,
                          body=meta)
        except RequestError as err:
            print('Metadata error: {0}'.format(err))
            shortMeta = {}
            if 'filename' in meta:
                shortMeta['filename'] = meta['filename']
            if 'title' in meta:
                shortMeta['title'] = meta['title']
                shortMeta['title_kw'] = meta['title']
                self.es.index(index=self.name + '.docs',
                              doc_type='doc',
                              id=self.dID,
                              body=shortMeta)
        self.dID += 1

    def index_dir(self):
        """
        Index all files from the corpus directory, sorted by their size
        in decreasing order. Such sorting helps prevent memory errors
        when indexing large corpora, as the default behavior is to load
        the whole file is into memory, and there is more free memory
        in the beginning of the process. If MemoryError occurs, the
        iterative JSON parser is used, which works much slower.
        """
        filenames = []
        for root, dirs, files in os.walk(self.corpus_dir):
            for fname in files:
                if (not ((self.settings['input_format'] == 'json'
                          and fname.lower().endswith('.json'))
                         or (self.settings['input_format'] == 'json-gzip'
                             and fname.lower().endswith('.json.gz')))):
                    continue
                fnameFull = os.path.join(root, fname)
                filenames.append((fnameFull, os.path.getsize(fnameFull)))
        for fname, fsize in sorted(filenames, key=lambda p: -p[1]):
            # print(fname, fsize)
            bulk(self.es, self.iterate_sentences(fname), chunk_size=300)
            self.index_doc(fname)
        self.index_words()

    def load_corpus(self):
        """
        Drop the current database, if any, and load the entire corpus.
        """
        t1 = time.time()
        self.delete_indices()
        self.create_indices()
        self.index_dir()
        t2 = time.time()
        print('Corpus indexed in', t2-t1, 'seconds:',
              self.dID, 'documents,',
              self.sID, 'sentences,',
              self.totalNumWords, 'words,',
              sum(len(self.wordFreqs[i]) for i in range(len(self.languages))), 'word types (different words).')


if __name__ == '__main__':
    x = Indexator()
    x.load_corpus()

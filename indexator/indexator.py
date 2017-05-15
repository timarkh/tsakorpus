from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk
import json
import os
import time
from prepare_data import PrepareData
from json_doc_reader import JSONDocReader


class Indexator:
    """
    Contains methods for loading the data in the corpus
    database.
    """
    SETTINGS_DIR = '../conf'

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.input_format = self.settings['input_format']
        self.corpus_dir = os.path.join('../corpus', self.name)
        self.iterSent = None
        if self.input_format == 'json':
            self.iterSent = JSONDocReader()
        f = open(os.path.join(self.SETTINGS_DIR, 'word_fields.json'),
                 'r', encoding='utf-8')
        self.goodWordFields = ['lex', 'wf'] + json.loads(f.read())
        f.close()
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        categories = json.loads(f.read())
        self.goodWordFields += ['gr.' + v for v in categories.values()]
        self.goodWordFields = set(self.goodWordFields)
        f.close()
        self.pd = PrepareData()
        self.es = Elasticsearch()
        self.es_ic = IndicesClient(self.es)
        self.wordFreqs = {}   # word as JSON -> its frequency
        self.wordSIDs = {}    # word as JSON -> set of sentence IDs
        self.sID = 0          # current sentence ID
        self.dID = 0          # current document ID

    def delete_indices(self):
        if self.es_ic.exists(index=self.name + '.docs'):
            self.es_ic.delete(index=self.name + '.docs')
        if self.es_ic.exists(index=self.name + '.words'):
            self.es_ic.delete(index=self.name + '.words')
        if self.es_ic.exists(index=self.name + '.sentences'):
            self.es_ic.delete(index=self.name + '.sentences')

    def create_indices(self):
        self.wordMapping = self.pd.generate_words_mapping()
        self.sentMapping = self.pd.generate_sentences_mapping(self.wordMapping)
        self.es_ic.create(index=self.name + '.docs')
        self.es_ic.create(index=self.name + '.words',
                          body=self.wordMapping)
        self.es_ic.create(index=self.name + '.sentences',
                          body=self.sentMapping)

    def process_sentence_words(self, words):
        """
        Take words list from a sentence, remove all non-searchable
        fields from them and add them to self.words dictionary.
        """
        for w in words:
            wClean = {}
            for field in w:
                if field in self.goodWordFields:
                    wClean[field] = w[field]
                    if field == 'wf':
                        wClean[field] = wClean[field].lower()
            if 'ana' in w:
                wClean['ana'] = []
                for ana in w['ana']:
                    cleanAna = {}
                    for anaField in ana:
                        if anaField in self.goodWordFields:
                            cleanAna[anaField] = ana[anaField]
                    wClean['ana'].append(cleanAna)
            wCleanTxt = json.dumps(wClean, ensure_ascii=False, sort_keys=True)
            try:
                self.wordFreqs[wCleanTxt] += 1
                self.wordSIDs[wCleanTxt].add(self.sID)
            except KeyError:
                self.wordFreqs[wCleanTxt] = 1
                self.wordSIDs[wCleanTxt] = {self.sID}

    def iterate_words(self):
        """
        Iterate through all words collected at the previous
        stage. Return JSON objects with actions for bulk indexing
        in Elasticsearch.
        """
        iWord = 0
        for w in self.wordFreqs:
            if iWord % 500 == 0:
                print('indexing word', iWord)
            wJson = json.loads(w)
            wJson['freq'] = self.wordFreqs[w]
            wJson['sids'] = [sid for sid in sorted(self.wordSIDs[w])]
            wJson['n_sents'] = len(wJson['sids'])
            curAction = {'_index': self.name + '.words',
                         '_type': 'word',
                         '_id': iWord,
                         '_source': wJson}
            iWord += 1
            yield curAction

    def index_words(self):
        """
        Index all words that have been collected at the previous stage
        in self.words (while the sentences were being indexed).
        """
        bulk(self.es, self.iterate_words())

    def iterate_sentences(self, fname):
        iSent = 0
        for s, bLast in self.iterSent.get_sentences(fname):
            if 'words' in s:
                self.process_sentence_words(s['words'])
            if iSent > 0:
                s['prev_id'] = self.sID - 1
            if not bLast:
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
            yield curAction
            if self.sID % 500 == 0:
                print('indexing sentence', self.sID)
            iSent += 1
            self.sID += 1

    def index_doc(self, fname):
        """
        Store the metadata of the source file.
        """
        self.dID += 1
        if self.dID % 100 == 0:
            print('indexing document', self.dID)
        meta = self.iterSent.get_metadata(fname)
        self.es.index(index=self.name + '.docs',
                      doc_type='doc',
                      id=self.dID,
                      body=meta)

    def index_dir(self):
        """
        Index all files from the corpus directory.
        """
        for root, dirs, files in os.walk(self.corpus_dir):
            for fname in files:
                if not fname.lower().endswith('.json'):
                    continue
                fnameFull = os.path.join(root, fname)
                self.index_doc(fnameFull)
                bulk(self.es, self.iterate_sentences(fnameFull))
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
              len(self.wordFreqs), 'different words.')


if __name__ == '__main__':
    x = Indexator()
    x.load_corpus()

from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk
import json
import os
import time
from prepare_data import PrepareData


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
        self.corpus_dir = os.path.join('../corpus', self.name)
        self.pd = PrepareData()
        self.es = Elasticsearch()
        self.es_ic = IndicesClient(self.es)
        self.words = {}   # word as JSON -> its frequency
        self.sId = 0

    def delete_indices(self):
        if self.es_ic.exists(index=self.name + '.words'):
            self.es_ic.delete(index=self.name + '.words')
        if self.es_ic.exists(index=self.name + '.sentences'):
            self.es_ic.delete(index=self.name + '.sentences')

    def create_indices(self):
        self.es_ic.create(index=self.name + '.words',
                          body=self.pd.generate_words_mapping())
        self.es_ic.create(index=self.name + '.sentences',
                          body=self.pd.generate_sentences_mapping())

    def iterate_sentences(self, fname):
        fIn = open(fname, 'r', encoding='utf-8-sig')
        curSentences = json.load(fIn)
        fIn.close()
        for iSent in range(len(curSentences)):
            s = curSentences[iSent]
            if iSent > 0:
                s['prev_id'] = self.sId - 1
            if iSent < len(curSentences) - 1:
                s['next_id'] = self.sId + 1
            # self.es.index(index=self.name + '.sentences',
            #               doc_type='sentence',
            #               id=self.sId,
            #               body=s)
            curAction = {'_index': self.name + '.sentences',
                         '_type': 'sentence',
                         '_id': self.sId,
                         '_source': s}
            yield curAction
            self.sId += 1
            if self.sId % 100 == 1:
                print('sentence', self.sId)

    def index_dir(self):
        """
        Index all files from the corpus directory.
        """
        sId = 0
        for root, dirs, files in os.walk(self.corpus_dir):
            for fname in files:
                if not fname.lower().endswith('.json'):
                    continue
                bulk(self.es, self.iterate_sentences(os.path.join(root, fname)))

    def load_corpus(self):
        """
        Drop the current database, if any, and load the entire corpus.
        """
        t1 = time.time()
        self.delete_indices()
        self.create_indices()
        self.index_dir()
        t2 = time.time()
        print('Corpus indexed in', t2-t1, 'seconds.')


if __name__ == '__main__':
    x = Indexator()
    x.load_corpus()

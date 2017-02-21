from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
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

    def index_dir(self):
        """
        Index all files from the corpus directory.
        """
        sId = 0
        for root, dirs, files in os.walk(self.corpus_dir):
            for fname in files:
                if not fname.lower().endswith('.json'):
                    continue
                fIn = open(os.path.join(root, fname), 'r', encoding='utf-8-sig')
                curSentences = json.load(fIn)
                fIn.close()
                for s in curSentences:
                    if sId > 0:
                        s['prev_id'] = sId - 1
                    if sId < len(curSentences) - 1:
                        s['next_id'] = sId + 1
                    self.es.index(index=self.name + '.sentences',
                                  doc_type='sentence',
                                  id=sId,
                                  body=s)
                    sId += 1
                    if sId % 100 == 1:
                        print('sentence', sId)

    def load_corpus(self):
        """
        Drop the current database, if any, and load the entire corpus.
        """
        t1 = time.clock()
        self.delete_indices()
        self.create_indices()
        self.index_dir()
        t2 = time.clock()
        print('Corpus indexed in', t2-t1, 'seconds.')


if __name__ == '__main__':
    x = Indexator()
    x.load_corpus()

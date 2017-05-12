from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
import json
import os
import time
from .query_parsers import InterfaceQueryParser


class SearchClient:
    """
    Contains methods for querying the corpus database.
    """

    def __init__(self, settings_dir, mode='production'):
        self.settings_dir = settings_dir
        self.mode = mode
        f = open(os.path.join(self.settings_dir, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.es = Elasticsearch()
        self.es_ic = IndicesClient(self.es)
        self.qp = InterfaceQueryParser(self.settings_dir)

    def get_words(self, esQuery):
        hits = self.es.search(index=self.name + '.words', doc_type='word',
                              body=esQuery)
        return hits

    def get_sentences(self, esQuery):
        hits = self.es.search(index=self.name + '.sentences', doc_type='sentence',
                              body=esQuery)
        return hits

    def get_sentence_by_id(self, sentId):
        esQuery = {'query': {'term': {'_id': sentId}}}
        hits = self.es.search(index=self.name + '.sentences', doc_type='sentence',
                              body=esQuery)
        return hits


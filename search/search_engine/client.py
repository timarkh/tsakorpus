from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
import json
import os
import time


class SearchClient:
    """
    Contains methods for querying the corpus database.
    """
    SETTINGS_DIR = '../conf'

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.es = Elasticsearch()
        self.es_ic = IndicesClient(self.es)

    def make_sent_ana_query(self, query, sortOrder='random'):
        mustClauses = []
        esQuery = {'nested': {'path': 'words.ana', 'filter': {'bool': {'must': mustClauses}}}}
        for k, v in query.items():
            mustClauses.append({'match': {'words.' + k: v}})
        return esQuery

    def make_word_ana_query(self, query, sortOrder='random'):
        mustClauses = []
        esQuery = {'nested': {'path': 'ana', 'filter': {'bool': {'must': mustClauses}}}}
        for k, v in query.items():
            mustClauses.append({'match': {k: v}})
        return esQuery

    def get_words(self, query, sortOrder='random'):
        esQuery = {'query': query}
        hits = self.es.search(index=self.name + '.words', doc_type='word',
                              body=esQuery)
        return hits

    def get_sentences(self, query, query_from=0, query_size=10, sortOrder='random'):
        if sortOrder == 'random':
            query = {'function_score': {'query': query, 'random_score': {}}}
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        hits = self.es.search(index=self.name + '.sentences', doc_type='sentence',
                              body=esQuery)
        return hits

    def find_sentences(self, htmlQuery):
        esQuery = {}
        prelimQuery = {}
        if 'wf' in htmlQuery and len(htmlQuery['wf']) > 0:
            prelimQuery['ana.wf'] = htmlQuery['wf']
        if 'l' in htmlQuery and len(htmlQuery['l']) > 0:
            prelimQuery['ana.lex'] = htmlQuery['l']
        if 'gr' in htmlQuery and len(htmlQuery['gr']) > 0:
            prelimQuery['ana.wf'] = htmlQuery['wf']

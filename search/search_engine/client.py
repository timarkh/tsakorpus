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

    def make_sent_ana_query(self, filterQuery, sortOrder='random'):
        esQuery = {'nested': {'path': 'words.ana', 'filter': filterQuery}}
        return esQuery

    def make_word_ana_query(self, filterQuery, sortOrder='random'):
        esQuery = {'nested': {'path': 'ana', 'filter': filterQuery}}
        return esQuery

    def get_words(self, query, sortOrder='random'):
        esQuery = {'query': query}
        if self.mode == 'test':
            return esQuery
        hits = self.es.search(index=self.name + '.words', doc_type='word',
                              body=esQuery)
        return hits

    def get_sentences(self, queryDict, query_from=0, query_size=10, sortOrder='random'):
        wordAnaFields = ['words.ana.lex', 'words.ana.wf', 'words.ana.gr']
        queryDict = {k: queryDict[k] for k in queryDict
                     if queryDict[k] is not None and queryDict[k] != {}}
        if len(queryDict) == 0:
            query = {'match_none': {}}
        else:
            query = self.make_sent_ana_query(list(queryDict.values()))
        if sortOrder == 'random':
            query = {'function_score': {'query': query, 'random_score': {}}}
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        if self.mode == 'test':
            return esQuery
        hits = self.es.search(index=self.name + '.sentences', doc_type='sentence',
                              body=esQuery)
        return hits

    def find_sentences(self, htmlQuery, query_from=0, query_size=10, sortOrder='random'):
        prelimQuery = {}
        if 'wf' in htmlQuery and len(htmlQuery['wf']) > 0:
            prelimQuery['words.ana.wf'] = self.qp.make_bool_query(htmlQuery['wf'], 'words.ana.wf')
        if 'l' in htmlQuery and len(htmlQuery['l']) > 0:
            prelimQuery['words.ana.lex'] = self.qp.make_bool_query(htmlQuery['l'], 'words.ana.lex')
        if 'gr' in htmlQuery and len(htmlQuery['gr']) > 0:
            prelimQuery['words.ana.wf'] = self.qp.make_bool_query(htmlQuery['gr'], 'words.ana.gr')
        esQuery = self.get_sentences(prelimQuery, query_from, query_size, sortOrder)
        return esQuery

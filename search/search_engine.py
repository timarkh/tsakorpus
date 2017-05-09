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

    def make_sent_ana_query(self, query):
        mustClauses = []
        esQuery = {'nested': {'path': 'words.ana', 'query': {'bool': {'must': mustClauses}}}}
        for k, v in query.items():
            mustClauses.append({'match': {'words.' + k: v}})
        return esQuery

    def make_word_ana_query(self, query):
        mustClauses = []
        esQuery = {'nested': {'path': 'ana', 'query': {'bool': {'must': mustClauses}}}}
        for k, v in query.items():
            mustClauses.append({'match': {k: v}})
        return esQuery

    def get_words(self, query):
        esQuery = {'query': query}
        hits = self.es.search(index=self.name + '.words', doc_type='word',
                              body=esQuery)
        return hits

    def get_sentences(self, query, query_from=0, query_size=10):
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        hits = self.es.search(index=self.name + '.sentences', doc_type='sentence',
                              body=esQuery)
        return hits


if __name__ == '__main__':
    sc = SearchClient()

    # 1. Lexical query.
    query1 = {'ana.lex': 'vbcvqr'}
    query1 = sc.make_word_ana_query(query1)
    print('query1 (words):', json.dumps(query1, ensure_ascii=False))
    hits = sc.get_words(query1)
    print('Results of query1:')
    print(json.dumps(hits, ensure_ascii=False, indent=1))

    # 2. Grammar query.
    query2 = {'ana.gr.tense': 't7', 'ana.gr.pers': '2'}
    query2 = sc.make_word_ana_query(query2)
    print('query2 (words):', json.dumps(query2, ensure_ascii=False))
    hits = sc.get_words(query2)
    print('Results of query2:')
    print(json.dumps(hits, ensure_ascii=False, indent=1))

    # 3. Grammar query in sentences:
    query2 = {'ana.gr.tense': 't7', 'ana.gr.pers': '2'}
    query2 = sc.make_sent_ana_query(query2)
    print('query2 (sentences):', json.dumps(query2, ensure_ascii=False))
    hits = sc.get_sentences(query2)
    print('Results of query2:')
    print('Hits:', hits['hits']['total'], ', took: ', hits['took'], 'ms.')

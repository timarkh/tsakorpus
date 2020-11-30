from elasticsearch import Elasticsearch, helpers
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
        print(esQuery)
        if self.settings['query_timeout'] > 0:
            hits = self.es.search(index=self.name + '.words',
                                  body=esQuery, request_timeout=self.settings['query_timeout'])
        else:
            hits = self.es.search(index=self.name + '.words',
                                  body=esQuery)
        return hits

    def get_lemmata(self, esQuery):
        print(esQuery)
        if self.settings['query_timeout'] > 0:
            hits = self.es.search(index=self.name + '.words',
                                  body=esQuery, request_timeout=self.settings['query_timeout'])
        else:
            hits = self.es.search(index=self.name + '.words',
                                  body=esQuery)
        return hits

    def get_word_freqs(self, esQuery):
        hits = self.es.search(index=self.name + '.words',
                              body=esQuery)
        return hits

    def get_docs(self, esQuery):
        hits = self.es.search(index=self.name + '.docs',
                              body=esQuery)
        return hits

    def get_all_docs(self, esQuery):
        """
        Iterate over all documents found with the query.
        """
        iterator = helpers.scan(self.es, index=self.name + '.docs',
                                query=esQuery)
        return iterator

    def get_sentences(self, esQuery):
        # esQuery = {
        #     'query': {'bool': {'must': [{'nested': {'path': 'words', 'query': {'constant_score': {'filter': {'bool': {
        #         'must': [{'match': {'words.wtype': 'word'}}, {'nested': {'path': 'words.ana', 'query': {
        #             'constant_score': {'filter': {'wildcard': {'words.ana.lex': 'a*'}}, 'boost': 1}},
        #                                                                  'score_mode': 'sum'}}]}},
        #         'boost': 1}},
        #                                             'score_mode': 'sum', 'inner_hits': {
        #             'highlight': {'fields': {'words': {'number_of_fragments': 100, 'fragment_size': 2048}}}, 'size': 50,
        #             'name': 'w1'}}}], 'filter': [{'term': {'lang': {'value': 0}}}]}}, 'size': 1, 'from': 0,
        #     'aggs': {'agg_ndocs': {'cardinality': {'field': 'doc_id'}}, 'agg_nwords': {'stats': {'script': '_score'}}}}
        print(esQuery)
        if self.settings['query_timeout'] > 0:
            hits = self.es.search(index=self.name + '.sentences',
                                  body=esQuery, request_timeout=self.settings['query_timeout'])
        else:
            hits = self.es.search(index=self.name + '.sentences',
                                  body=esQuery)
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return hits

    def get_all_sentences(self, esQuery):
        """
        Iterate over all sentences found with the query.
        """
        if self.settings['query_timeout'] > 0:
            iterator = helpers.scan(self.es, index=self.name + '.sentences',
                                    query=esQuery, request_timeout=self.settings['query_timeout'])
        else:
            iterator = helpers.scan(self.es, index=self.name + '.sentences',
                                    query=esQuery)
        return iterator

    def get_sentence_by_id(self, sentId):
        esQuery = {'query': {'term': {'_id': sentId}}}
        hits = self.es.search(index=self.name + '.sentences',
                              body=esQuery)
        return hits

    def get_word_by_id(self, wordId):
        esQuery = {'query': {'term': {'_id': wordId}}}
        hits = self.es.search(index=self.name + '.words',
                              body=esQuery)
        return hits

    def get_doc_by_id(self, docId):
        esQuery = {'query': {'term': {'_id': docId}}}
        hits = self.es.search(index=self.name + '.docs',
                              body=esQuery)
        return hits

    def get_n_words(self):
        """
        Return total number of words in the primary language in the corpus.
        """
        aggNWords = {'agg_nwords': {'sum': {'field': 'n_words'}}}
        esQuery = {'query': {'match_all': {}}, 'from': 0, 'size': 0,
                   'aggs': aggNWords}
        hits = self.es.search(index=self.name + '.docs',
                              body=esQuery)
        return hits['aggregations']['agg_nwords']['value']

    def get_n_words_in_document(self, docId):
        """
        Return number of words in the primary language in given document.
        """
        response = self.get_doc_by_id(docId=docId)
        if response['hits']['total']['value'] <= 0:
            return 0
        return response['hits']['hits'][0]['_source']['n_words']

    def get_word_freq_by_rank(self, lang):
        """
        Return word frequencies in the entire corpus aggregated by their
        frequency rank.
        """
        htmlQuery = {'lang': lang, 'lang1': lang, 'wf1': '*', 'n_ana1': 'any'}
        esQuery = self.qp.word_freqs_query(htmlQuery, searchType='word')
        hits = self.es.search(index=self.name + '.words',
                              body=esQuery)
        return hits

    def get_lemma_freq_by_rank(self, lang):
        """
        Return lemma frequencies in the entire corpus aggregated by their
        frequency rank.
        """
        htmlQuery = {'lang': lang, 'lang1': lang, 'wf1': '*', 'n_ana1': 'any'}
        esQuery = self.qp.word_freqs_query(htmlQuery, searchType='lemma')
        hits = self.es.search(index=self.name + '.words',
                              body=esQuery)
        return hits

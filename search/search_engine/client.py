from elasticsearch import Elasticsearch, helpers
from elasticsearch.client import IndicesClient
import subprocess
import os
import json
import time
from .query_parsers import InterfaceQueryParser


def log_if_needed(f):
    """
    A decorator used to log the query if logging is on.
    """
    def f_decorated(self, esQuery):
        if self.logging == 'query':
            self.query_log.append(esQuery)
        hits = f(self, esQuery)
        if self.logging == 'hits' and type(hits) == dict:
            self.query_log.append(hits)
        return hits
    return f_decorated


class SearchClient:
    """
    Contains methods for querying the corpus database.
    """

    def __init__(self, settings_dir, settings):
        self.settings = settings
        self.name = self.settings.corpus_name
        esTimeout = max(20, self.settings.query_timeout)
        self.es = None
        if self.settings.elastic_url is not None and len(self.settings.elastic_url) > 0:
            # Connect to a non-default URL or supply username and password
            self.es = Elasticsearch([self.settings.elastic_url], timeout=esTimeout)
        else:
            self.es = Elasticsearch(timeout=esTimeout)
        self.es_ic = IndicesClient(self.es)
        self.qp = InterfaceQueryParser(settings_dir, self.settings)
        self.logging = 'none'   # none|query|hits
        self.query_log = []
        # Logging is only switched temporarily when the user clicks on
        # "show query" or "show response" buttons in debug mode.

    def start_query_logging(self):
        """
        Start temporarily logging queries to a list.
        """
        self.query_log = []
        self.logging = 'query'

    def start_hits_logging(self):
        """
        Start temporarily logging ES response JSONs to a list.
        """
        self.query_log = []
        self.logging = 'hits'

    def stop_logging(self):
        """
        Stop logging queries. Return query log.
        """
        queryLog = self.query_log
        self.query_log = []
        self.logging = 'none'
        return queryLog

    @log_if_needed
    def get_words(self, esQuery):
        """
        Retrieve hits from the words index. This includes
        words, lemmata and word_freq and lemma_freq objects
        used to count the number of occurrences in a particular
        subcorpus.
        """
        if self.settings.query_timeout > 0:
            hits = self.es.search(index=self.name + '.words',
                                  body=esQuery, request_timeout=self.settings.query_timeout)
        else:
            hits = self.es.search(index=self.name + '.words',
                                  body=esQuery)
        return hits

    @log_if_needed
    def get_docs(self, esQuery):
        hits = self.es.search(index=self.name + '.docs',
                              body=esQuery)
        return hits

    @log_if_needed
    def get_all_docs(self, esQuery):
        """
        Iterate over all documents found with the query.
        """
        iterator = helpers.scan(self.es, index=self.name + '.docs',
                                query=esQuery)
        return iterator

    @log_if_needed
    def get_sentences(self, esQuery):
        print(json.dumps(esQuery, ensure_ascii=False, indent=1))
        if self.settings.query_timeout > 0:
            hits = self.es.search(index=self.name + '.sentences',
                                  body=esQuery, request_timeout=self.settings.query_timeout)
        else:
            hits = self.es.search(index=self.name + '.sentences',
                                  body=esQuery)
        # print(json.dumps(hits, ensure_ascii=False, indent=1))
        return hits

    @log_if_needed
    def get_all_sentences(self, esQuery):
        """
        Iterate over all sentences found with the query.
        """
        if self.settings.query_timeout > 0:
            iterator = helpers.scan(self.es, index=self.name + '.sentences',
                                    query=esQuery, request_timeout=self.settings.query_timeout)
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

    def start_elastic_service(self):
        """
        Try to restart the system's Elasticsearch server.
        """
        subprocess.Popen(os.path.abspath('restart_elasticsearch.sh'), shell=True,
                         stdout=subprocess.PIPE)

    def is_alive(self):
        """
        Check if the Elasticsearch connection is alive.
        """
        try:
            return self.es.ping()
        except Exception as err:
            return False

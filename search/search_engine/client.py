import elasticsearch
ESVersion = elasticsearch.__version__[0]   # Should be 7 or 9 (or use 8 at your own risk, I didn't test it)

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


def log_if_needed_partition(f):
    """
    A decorator used to log the query if logging is on.
    """
    def f_decorated(self, esQuery, partition=0):
        if self.logging == 'query':
            self.query_log.append(esQuery)
        hits = f(self, esQuery, partition=partition)
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
        if not self.check_elastic_version():
            return
        if self.settings.elastic_url is not None and len(self.settings.elastic_url) > 0:
            # Connect to a non-default URL or supply username and password
            if ESVersion == 7:
                self.es = Elasticsearch([self.settings.elastic_url], timeout=esTimeout)
            else:
                if len(self.settings.elastic_cacert) > 0:
                    self.es = Elasticsearch([self.settings.elastic_url], request_timeout=60,
                                            basic_auth=(self.settings.elastic_user, self.settings.elastic_pwd),
                                            ca_certs=self.settings.elastic_cacert)
                else:
                    self.es = Elasticsearch([self.settings.elastic_url], request_timeout=60,
                                            basic_auth=(self.settings.elastic_user, self.settings.elastic_pwd))
        else:
            if ESVersion == 7:
                self.es = Elasticsearch(timeout=esTimeout)
            else:
                if len(self.settings.elastic_cacert) > 0:
                    self.es = Elasticsearch("https://localhost:9200", request_timeout=60,
                                            basic_auth=(self.settings.elastic_user, self.settings.elastic_pwd),
                                            ca_certs=self.settings.elastic_cacert)
                else:
                    self.es = Elasticsearch("http://localhost:9200", request_timeout=60,
                                            basic_auth=(self.settings.elastic_user, self.settings.elastic_pwd))

        self.es_ic = IndicesClient(self.es)
        self.qp = InterfaceQueryParser(settings_dir, self.settings)
        self.logging = 'none'   # none|query|hits
        self.query_log = []
        # Logging is only switched temporarily when the user clicks on
        # "show query" or "show response" buttons in debug mode.

    def check_elastic_version(self):
        """
        Check if the Elasticsearch has one of the accepted versions
        and if version-specific settings (if any) are provided.
        Return False if something is wrong, True otherwise.
        """
        if ESVersion == 8:
            print('Warning: this Tsakorpus version has not been tested with Elasticsearch 8.x.')
        elif ESVersion not in (7, 9):
            print('Wrong Elasticsearch version:', ESVersion)
            return False
        if ESVersion == 9:
            if len(self.settings.elastic_pwd) <= 0:
                print('With Elasticsearch 9, a password for basic authentication has to be provided.')
            if len(self.settings.elastic_user) <= 0:
                self.settings.elastic_user = 'elastic'
        return True

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

    @log_if_needed_partition
    def get_sentences(self, esQuery, partition=0):
        # print(json.dumps(esQuery, ensure_ascii=False, indent=1))
        indexName = self.name + '.sentences'
        if partition > 0:
            indexName += '.' + str(partition - 1)
        else:
            indexName += '*'
        # print(esQuery)
        if self.settings.query_timeout > 0:
            hits = self.es.search(index=indexName,
                                  body=esQuery, request_timeout=self.settings.query_timeout)
        else:
            hits = self.es.search(index=indexName,
                                  body=esQuery)
        # print(json.dumps(hits, ensure_ascii=False, indent=1))
        return hits

    @log_if_needed_partition
    def get_all_sentences(self, esQuery, partition=0):
        """
        Iterate over all sentences found with the query.
        """
        indexName = self.name + '.sentences'
        if partition > 0:
            indexName += '.' + str(partition - 1)
        else:
            indexName += '*'
        # print(esQuery)
        if self.settings.query_timeout > 0:
            iterator = helpers.scan(self.es, index=indexName,
                                    query=esQuery, request_timeout=self.settings.query_timeout)
        else:
            iterator = helpers.scan(self.es, index=indexName,
                                    query=esQuery)
        return iterator

    def get_sentence_by_id(self, sentId):
        esQuery = {'query': {'term': {'_id': sentId}}}
        hits = self.es.search(index=self.name + '.sentences*',
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

    def get_n_words(self, primaryLanguages=None, partition=0):
        """
        Return total number of words in the primary language(s) in the corpus.
        """
        aggNWords = {'agg_nwords': {'sum': {'field': 'n_words'}}}
        if primaryLanguages is not None and len(primaryLanguages) > 0:
            for lang in primaryLanguages:
                aggNWords['agg_nwords_' + lang] = {'sum': {'field': 'n_words_' + lang}}
        esQuery = {'query': {'match_all': {}}, 'from': 0, 'size': 0,
                   'aggs': aggNWords}
        index = self.name + '.docs'
        if partition > 0:
            index = self.name + '.sentences.' + str(partition - 1)
        # print(esQuery, index)
        hits = self.es.search(index=index,
                              body=esQuery)
        if primaryLanguages is not None and len(primaryLanguages) > 0:
            nWords = 0
            for lang in primaryLanguages:
                nWords += hits['aggregations']['agg_nwords_' + lang]['value']
            return nWords
        return hits['aggregations']['agg_nwords']['value']

    def get_n_words_in_document(self, docId, primaryLanguages=None):
        """
        Return number of words in the primary language in given document.
        """
        response = self.get_doc_by_id(docId=docId)
        if response['hits']['total']['value'] <= 0:
            return 0
        if primaryLanguages is not None and len(primaryLanguages) > 0:
            nWords = 0
            for lang in primaryLanguages:
                nWords += response['hits']['hits'][0]['_source']['n_words_' + lang]
            return nWords
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
        if os.name != 'nt':
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

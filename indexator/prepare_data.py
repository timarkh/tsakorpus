import json
import os
import re


class PrepareData:
    """
    Contains functions called when preparing the data
    for indexing in the database.
    """
    SETTINGS_DIR = '../conf'
    rxBadField = re.compile('[^a-zA-Z0-9_]|^(?:lex|gr|gloss_index|wf|[wm]type|ana|sent_ids|id)$')

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.wordFields = []
        if 'word_fields' in self.settings:
            self.wordFields = self.settings['word_fields']
        self.kwFields = []
        if 'kw_word_fields' in self.settings:
            self.kwFields = self.settings['kw_word_fields']
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        self.categories = json.loads(f.read())
        f.close()
        wfAnalyzerPatter = '[.\n()\\[\\]/]'
        if 'wf_analyzer_pattern' in self.settings:
            wfAnalyzerPatter = self.settings['wf_analyzer_pattern']
        wfLowercase = True
        if 'wf_lowercase' in self.settings:
            wfLowercase = self.settings['wf_lowercase']
        self.wfAnalyzer = {
            'analysis': {
                'analyzer': {
                    'wf_analyzer': {
                        'type': 'pattern',
                        'pattern': wfAnalyzerPatter,
                        'lowercase': wfLowercase
                    },
                    'gloss_analyzer': {
                        'type': 'pattern',
                        'pattern': ' ',
                        'lowercase': True
                    }
                }
            }
        }
        self.docNormalizer = {
            'analysis': {
                'analyzer': {
                    'lowercase_normalizer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'char_filter': [],
                        'filter': ['lowercase']
                    }
                }
            }
        }

    def generate_words_mapping(self, wordFreqs=True):
        """
        Return Elasticsearch mapping for the type "word", based
        on searchable features described in word_fields.json and
        categories.json.
        If wordFreqs is True, also include mapping for the type
        "word_freq" (this is needed only for the words index, but
        not for the sentences index).
        """
        m = {'wf': {'type': 'text',
                    'fielddata': True,
                    'analyzer': 'wf_analyzer'},
             'wf_display': {'type': 'text', 'index': False},
             'wtype': {'type': 'keyword'},
             'lang': {'type': 'byte'},
             'sentence_index': {'type': 'short'},
             'sids': {'type': 'integer', 'index': False},
             'n_ana': {'type': 'byte'},
             'ana': {'type': 'nested',
                     'properties': {'lex': {'type': 'text',
                                            'fielddata': True,
                                            'analyzer': 'wf_analyzer'},
                                    'gloss_index': {'type': 'text',
                                                    'analyzer': 'gloss_analyzer'}}},
             'freq': {'type': 'integer'},
             'rank': {'type': 'keyword'},
             'rank_true': {'type': 'integer'},
             'n_sents': {'type': 'integer'},
             'n_docs': {'type': 'integer'},
             'wf_order': {'type': 'integer'},   # position of the word form in sorted list of word forms
             'l_order': {'type': 'integer'}     # position of the lemma in sorted list of lemmata
             }
        for field in self.wordFields:
            if self.rxBadField.search(field) is None and field not in self.kwFields:
                m['ana']['properties'][field] = {'type': 'text'}
        for field in self.kwFields:
            if self.rxBadField.search(field) is None:
                m['ana']['properties'][field] = {'type': 'keyword'}
        for field in set(v for lang in self.categories.values()
                         for v in lang.values()):
            if self.rxBadField.search(field) is None:
                m['ana']['properties']['gr.' + field] = {'type': 'keyword'}
        if not wordFreqs:
            return {'mappings': {'word': {'properties': m}},
                    'settings': self.wfAnalyzer}
        lemmaMapping = self.generate_lemma_mapping()
        wordFreqMapping = self.generate_wordfreq_mapping()
        return {'mappings': {'lemma': lemmaMapping,
                             'word': {'properties': m, '_parent': {'type': 'lemma'}},
                             'word_freq': wordFreqMapping},
                'settings': self.wfAnalyzer}

    def generate_lemma_mapping(self):
        """
        Return Elasticsearch mapping for the type "lemma".
        """
        m = {'wf': {'type': 'text',
                    'fielddata': True,
                    'analyzer': 'wf_analyzer'},
             'lang': {'type': 'byte'},
             'freq': {'type': 'integer'},
             'rank': {'type': 'keyword'},
             'rank_true': {'type': 'integer'},
             'n_sents': {'type': 'integer'},
             'n_docs': {'type': 'integer'},
             'l_order': {'type': 'integer'}
            }
        return {'properties': m}

    def generate_wordfreq_mapping(self):
        """
        Return Elasticsearch mapping for the type "word_freq".
        Each element of word_freq index contains data about frequency
        of a specific word in a specific document.
        """
        m = {'w_id': {'type': 'integer'},
             'd_id': {'type': 'integer'},
             'freq': {'type': 'integer'},
             'wf_order': {'type': 'integer'},   # position of the word form in sorted list of word forms
             'l_order': {'type': 'integer'}     # position of the lemma in sorted list of lemmata
             }
        return {'properties': m, '_parent': {'type': 'word'}}

    def generate_docs_mapping(self):
        """
        Return Elasticsearch mapping for the type "doc".
        Each element of docs index contains metadata about
        about a single document.
        """
        m = {}
        m['n_words'] = {'type': 'integer'}
        m['n_sents'] = {'type': 'integer'}
        if len(self.settings['languages']) > 1:
            for lang in self.settings['languages']:
                m['n_words_' + lang] = {'type': 'integer'}
                m['n_sents_' + lang] = {'type': 'integer'}
        for meta in self.settings['viewable_meta']:
            if meta.startswith('year'):
                m[meta] = {'type': 'integer'}
            else:
                m[meta] = {'type': 'text',
                           'analyzer': 'lowercase_normalizer'}
                m[meta + '_kw'] = {'type': 'keyword'}
        return {'mappings': {'doc': {'properties': m}}, 'settings': self.docNormalizer}

    def generate_sentences_mapping(self, word_mapping):
        """
        Return Elasticsearch mapping for the type "sentence", based
        on searchable features described in word_fields.json and
        categories.json.
        """
        wordProps = word_mapping['mappings']['word']['properties']
        wordProps['w_id'] = {'type': 'integer'}
        m = {'prev_id': {'type': 'integer'},
             'next_id': {'type': 'integer'},
             'doc_id': {'type': 'integer'},
             'text': {'type': 'text'},
             'lang': {'type': 'byte'},
             'n_words': {'type': 'short'},
             'src_alignment': {'type': 'nested',
                               'properties': {
                                   'mtype': {'type': 'keyword'},
                                   'src': {'type': 'keyword',
                                           'index': False},
                                   'off_start_src': {'type': 'float',
                                                     'index': False},
                                   'off_start_sent': {'type': 'short',
                                                      'index': False},
                                   'off_end_src': {'type': 'float',
                                                   'index': False},
                                   'off_end_sent': {'type': 'short',
                                                    'index': False},
                                   'rect_src': {'type': 'integer',
                                                'index': False},
                                   'src_id': {'type': 'keyword',
                                              'index': False},
                               }},
             'para_ids': {'type': 'keyword'},
             'para_alignment': {'type': 'nested',
                                'properties': {
                                    'off_start': {'type': 'short',
                                                  'index': False},
                                    'off_end': {'type': 'short',
                                                'index': False},
                                    'para_id': {'type': 'keyword',
                                                'index': False},
                                    'sent_ids': {'type': 'integer',
                                                 'index': False}
                                }},
             'style_spans': {'type': 'nested',
                             'properties': {
                                 'off_start': {'type': 'short',
                                               'index': False},
                                 'off_end': {'type': 'short',
                                             'index': False},
                                 'span_class': {'type': 'keyword',
                                                'index': False}
                             }},
             'segment_ids': {'type': 'integer',
                             'index': False},
             'words': {'type': 'nested',
                       'properties': word_mapping['mappings']['word']['properties']}}
        sentMetaDict = {}
        for meta in self.settings['sentence_meta']:
            if meta.startswith('year') or ('integer_meta_fields' in self.settings
                                           and meta in self.settings['integer_meta_fields']):
                sentMetaDict[meta] = {'type': 'integer'}
            else:
                sentMetaDict[meta] = {'type': 'text'}
                sentMetaDict[meta + '_kw'] = {'type': 'keyword'}
        if len(sentMetaDict) > 0:
            m['meta'] = {'properties': sentMetaDict}
        return {'mappings': {'sentence': {'properties': m}}, 'settings': self.wfAnalyzer}

    def generate_mappings(self):
        """
        Return Elasticsearch mappings for all types to be used
        in the corpus database.
        """
        mSentWord = self.generate_words_mapping(wordFreqs=False)
        mWord = self.generate_words_mapping()
        mSent = self.generate_sentences_mapping(mSentWord)
        mDoc = self.generate_docs_mapping()
        mappings = {'docs': mDoc,
                    'sentences': mSent,
                    'words': mWord}
        return mappings

    def write_mappings(self, fnameOut):
        """
        Generate and write Elasticsearch mappings for all types to be used
        in the corpus database.
        """
        fOut = open(fnameOut, 'w', encoding='utf-8')
        fOut.write(json.dumps(self.generate_mappings(), indent=2,
                              ensure_ascii=False))
        fOut.close()


if __name__ == '__main__':
    pd = PrepareData()
    pd.write_mappings('mappings.json')

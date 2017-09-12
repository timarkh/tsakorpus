import json
import os
import re


class PrepareData:
    """
    Contains functions called when preparing the data
    for indexing in the database.
    """
    SETTINGS_DIR = '../conf'
    rxBadField = re.compile('[^a-z0-9_]|^(?:lex|gr|gloss_index|wf|[wm]type|ana|sent_ids|id)$')

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.wordFields = []
        if 'word_fields' in self.settings:
            self.wordFields = self.settings['word_fields']
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        self.categories = json.loads(f.read())
        f.close()
        self.wfAnalyzer = {
            'analysis': {
                'analyzer': {
                    'wf_analyzer': {
                        'type': 'pattern',
                        'pattern': '[\\-\n()]',
                        'lowercase': True
                    },
                    'gloss_analyzer': {
                        'type': 'pattern',
                        'pattern': ' ',
                        'lowercase': True
                    },
                }
            }
        }

    def generate_words_mapping(self):
        """
        Return Elasticsearch mapping for the type "word", based
        on searchable features described in word_fields.json and
        categories.json.
        """
        m = {'wf': {'type': 'text',
                    'fielddata': True,
                    'analyzer': 'wf_analyzer'},
             'wtype': {'type': 'keyword'},
             'lang': {'type': 'byte'},
             'sids': {'type': 'integer', 'index': False},
             'ana': {'type': 'nested',
                     'properties': {'lex': {'type': 'text'},
                                    'gloss_index': {'type': 'text',
                                                    'analyzer': 'gloss_analyzer'}}},
             'freq': {'type': 'integer'},
             'rank': {'type': 'keyword'},
             'n_sents': {'type': 'integer'},
             'n_docs': {'type': 'integer'}
             }
        for field in self.wordFields:
            if self.rxBadField.search(field) is None:
                m['ana']['properties'][field] = {'type': 'text'}
        for field in set(v for lang in self.categories.values()
                         for v in lang.values()):
            if self.rxBadField.search(field) is None:
                m['ana']['properties']['gr.' + field] = {'type': 'keyword'}
        return {'mappings': {'word': {'properties': m}}, 'settings': self.wfAnalyzer}

    def generate_wordfreq_mapping(self):
        """
        Return Elasticsearch mapping for the type "word_freq".
        Each element of word_freq index contains data about frequency
        of a specific word in a specific document.
        """
        m = {'w_id': {'type': 'integer'},
             'd_id': {'type': 'integer'},
             'freq': {'type': 'integer'}}
        return {'mappings': {'word_freq': {'properties': m}}}

    def generate_sentences_mapping(self, word_mapping):
        """
        Return Elasticsearch mapping for the type "sentence", based
        on searchable features described in word_fields.json and
        categories.json.
        """
        m = {'prev_id': {'type': 'integer'},
             'next_id': {'type': 'integer'},
             'doc_id': {'type': 'integer'},
             'text': {'type': 'text'},
             'lang': {'type': 'byte'},
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
             'segment_ids': {'type': 'integer',
                             'index': False},
             'words': {'type': 'nested',
                       'properties': word_mapping['mappings']['word']['properties']}}
        return {'mappings': {'sentence': {'properties': m}}, 'settings': self.wfAnalyzer}

    def generate_mappings(self):
        """
        Return Elasticsearch mappings for all types to be used
        in the corpus database.
        """
        mWord = self.generate_words_mapping()
        mSent = self.generate_sentences_mapping(mWord)
        mWFreq = self.generate_wordfreq_mapping()
        mappings = {'sentences': mSent,
                    'words': mWord,
                    'word_freqs': mWFreq}
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

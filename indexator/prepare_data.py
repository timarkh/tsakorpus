import copy
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
    MULTIPLE_SHARDS_THRESHOLD = 256 * 1024 * 1024

    def __init__(self):
        """
        Load corpus-specific settings from conf/corpus.json. Create
        analyzer patterns used by Elasticsearch to tokenize text.
        """
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
        if 'wf_analyzer_pattern' in self.settings and self.settings['wf_analyzer_pattern'] is not None:
            wfAnalyzerPatter = self.settings['wf_analyzer_pattern']
        wfLowercase = True
        if 'wf_lowercase' in self.settings:
            wfLowercase = self.settings['wf_lowercase']
        textFieldsAnalyzerPattern = '[.\n()\\[\\]/,:;?!" ]'
        if 'text_fields_analyzer_pattern' in self.settings and self.settings['text_fields_analyzer_pattern'] is not None:
            textFieldsAnalyzerPattern = self.settings['text_fields_analyzer_pattern']
        textFieldsLowercase = True
        if 'text_fields_lowercase' in self.settings:
            textFieldsLowercase = self.settings['text_fields_lowercase']
        self.wfAnalyzer = {
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
                },
                'text_fields_analyzer': {
                    'type': 'pattern',
                    'pattern': textFieldsAnalyzerPattern,
                    'lowercase': textFieldsLowercase
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
                    },
                    'lowercase_normalizer_notokenize': {
                        'type': 'pattern',
                        'pattern': '[|]',
                        'lowercase': True
                    },
                    'keepcase_normalizer_notokenize': {
                        'type': 'pattern',
                        'pattern': '[|]',
                        'lowercase': False
                    }
                }
            }
        }
        if 'meta_analyzer_patterns' in self.settings:
            metaFieldsWithPatterns = [m for m in sorted(self.settings['meta_analyzer_patterns'])]
        else:
            metaFieldsWithPatterns = []
        for i in range(len(metaFieldsWithPatterns)):
            self.docNormalizer['analysis']['analyzer']['lowercase_normalizer_meta_' + str(i)] = {
                'type': 'pattern',
                'pattern': self.settings['meta_analyzer_patterns'][metaFieldsWithPatterns[i]],
                'lowercase': True
            }
            self.docNormalizer['analysis']['analyzer']['keepcase_normalizer_meta_' + str(i)] = {
                'type': 'pattern',
                'pattern': self.settings['meta_analyzer_patterns'][metaFieldsWithPatterns[i]],
                'lowercase': False
            }

    def generate_words_mapping(self, wordFreqs=True):
        """
        Return Elasticsearch mapping for the type "word", based
        on searchable features described in the corpus settings.
        This type is used for storing both words and lemmata.
        If wordFreqs is True, also include fields for a "word_freq"
        object (this is needed only for the words index, but
        not for the sentences index).
        """
        m = {
            'wf': {
                'type': 'text',
                'fielddata': True,
                'index_prefixes': {
                    'min_chars': 3,
                    'max_chars': 10
                },
                'analyzer': 'wf_analyzer'
            },
            'wf_display': {
                'type': 'text',
                'index': False
            },
            'wtype': {'type': 'keyword'},
            # wtype=word|punct|lemma|word_freq
            # "lemma" and "word_freq" values are only used in the words index
            'lang': {'type': 'byte'},
            'sentence_index': {'type': 'short'},
            'sentence_index_neg': {'type': 'short'},
            'sids': {
                'type': 'integer',
                'index': False
            },
            'n_ana': {'type': 'byte'},
            'ana': {
                'type': 'nested',
                'properties': {
                    'lex': {
                        'type': 'text',
                        'fielddata': True,
                        'index_prefixes': {
                            'min_chars': 3,
                            'max_chars': 10
                        },
                        'analyzer': 'wf_analyzer'
                    },
                    'gloss_index': {
                        'type': 'text',
                        'analyzer': 'gloss_analyzer'
                    },
                    'gloss': {
                        'type': 'text',
                        'index': False
                    }
                }
            },
            'freq': {'type': 'integer'},
            'lemma_freq': {'type': 'integer'},
            'rank': {'type': 'keyword'},
            'rank_true': {'type': 'integer'},
            'n_sents': {'type': 'integer'},
            'n_docs': {'type': 'integer'},
            'id': {'type': 'keyword'},         # for aggregations / sorting
            'w_id': {'type': 'keyword'},       # word ID
            'l_id': {'type': 'keyword'},       # lemma ID
            'wf_order': {'type': 'integer'},   # position of the word form in sorted list of word forms
            'l_order': {'type': 'integer'}     # position of the lemma in sorted list of lemmata
        }
        for field in self.wordFields:
            # additional word-level fields such as translation
            if self.rxBadField.search(field) is None and field not in self.kwFields:
                m['ana']['properties'][field] = {
                    'type': 'text',
                    'analyzer': 'text_fields_analyzer'
                }
        for field in self.kwFields:
            # additional word-level fields with no full-text search
            if self.rxBadField.search(field) is None:
                m['ana']['properties'][field] = {'type': 'keyword'}
        for field in set(v for lang in self.categories.values()
                         for v in lang.values()):
            # grammatical categories
            if self.rxBadField.search(field) is None:
                m['ana']['properties']['gr.' + field] = {'type': 'keyword'}
        if wordFreqs:
            # If preparing a mapping for the words index:
            # add fields used by word_freq objects, i.e. Document ID.
            m['d_id'] = {'type': 'integer'}
            # A join field is a mechanism by which a parent-child
            # relation can be established. A word_freq object, which
            # represents a number of occurrences of a particular word/lemma
            # in a particular text, is a child of a word object
            # that represents that word or lemma in general.
            m['freq_join'] = {
                'type': 'join',
                'relations': {
                    'word': 'word_freq'
                    # This comprises both words and lemmata
                    # (and maybe other objects in the future).
                }
            }
        mapping = {
            'mappings': {
                'properties': m
            },
            'settings': {
                'analysis': self.wfAnalyzer
            }
        }
        return mapping

    def generate_docs_mapping(self):
        """
        Return Elasticsearch mapping for the type "doc".
        Each element of docs index contains metadata about
        about a single document.
        """
        m = {
            'n_words': {'type': 'integer'},
            'n_sents': {'type': 'integer'},
            'doc_id': {'type': 'keyword'}
        }
        if len(self.settings['languages']) > 1:
            for lang in self.settings['languages']:
                m['n_words_' + lang] = {'type': 'integer'}
                m['n_sents_' + lang] = {'type': 'integer'}

        metaFields = self.settings['viewable_meta'][:]
        if 'search_meta' in self.settings and 'stat_options' in self.settings['search_meta']:
            metaFields += self.settings['search_meta']['stat_options']
        if 'title' not in metaFields:
            metaFields.append('title')
        if ('author_metafield' in self.settings
                and len(self.settings['author_metafield']) > 0
                and self.settings['author_metafield'] not in metaFields):
            metaFields.append(self.settings['author_metafield'])
        for meta in metaFields:
            if meta.startswith('year') or ('integer_meta_fields' in self.settings
                                           and meta in self.settings['integer_meta_fields']):
                m[meta] = {'type': 'integer'}
            elif meta == 'title' or ('notokenize_meta_fields' in self.settings
                                     and meta in self.settings['notokenize_meta_fields']):
                if ('case_sensitive_meta_fields' in self.settings
                        and meta in self.settings['case_sensitive_meta_fields']):
                    m[meta] = {
                        'type': 'text',
                        'analyzer': 'keepcase_normalizer_notokenize'
                    }
                else:
                    m[meta] = {
                        'type': 'text',
                        'analyzer': 'lowercase_normalizer_notokenize'
                    }
                m[meta + '_kw'] = {'type': 'keyword'}
            elif ('meta_analyzer_patterns' in self.settings
                  and meta in self.settings['meta_analyzer_patterns']):
                patternID = [m for m in sorted(self.settings['meta_analyzer_patterns'])].index(meta)
                if ('case_sensitive_meta_fields' in self.settings
                        and meta in self.settings['case_sensitive_meta_fields']):
                    m[meta] = {
                        'type': 'text',
                        'analyzer': 'keepcase_normalizer_meta_' + str(patternID)
                    }
                else:
                    m[meta] = {
                        'type': 'text',
                        'analyzer': 'lowercase_normalizer_meta_' + str(patternID)
                    }
                m[meta + '_kw'] = {'type': 'keyword'}
            else:
                m[meta] = {
                    'type': 'text',
                    'analyzer': 'lowercase_normalizer'
                }
                m[meta + '_kw'] = {'type': 'keyword'}
            if ('localized_metadata_values' in self.settings
                    and 'interface_languages' in self.settings
                    and meta in self.settings['localized_metadata_values']):
                for lang in self.settings['interface_languages']:
                    if len(lang) > 0:
                        m[meta + '_' + lang] = copy.deepcopy(m[meta])
                        if meta + '_kw' in m:
                            m[meta + '_' + lang + '_kw'] = copy.deepcopy(m[meta + '_kw'])
        mapping = {
            'mappings': {
                'properties': m
            },
            'settings': self.docNormalizer
        }
        return mapping

    def generate_sentences_mapping(self, word_mapping, doc_mapping, corpusSizeInBytes=0):
        """
        Return Elasticsearch mapping for the type "sentence", based
        on searchable features described in the corpus settings.
        """
        wordProps = word_mapping['mappings']['properties']
        m = {
            'prev_id': {'type': 'keyword'},
            'next_id': {'type': 'keyword'},
            'doc_id': {'type': 'keyword'},
            'sent_id': {'type': 'long'},
            'partition': {'type': 'keyword'},
            'text': {'type': 'text'},
            'lang': {'type': 'keyword'},
            'words': {
                'type': 'nested',
                'properties': wordProps
            },
            'n_words': {'type': 'short'},
            'src_alignment': {
                'type': 'nested',
                'properties': {
                    'mtype': {'type': 'keyword'},
                    'src': {
                        'type': 'keyword',
                        'index': False
                    },
                    'off_start_src': {
                        'type': 'float',
                        'index': False
                    },
                    'off_start_sent': {
                        'type': 'short',
                        'index': False
                    },
                    'off_end_src': {
                        'type': 'float',
                        'index': False}
                    ,
                    'off_end_sent': {
                        'type': 'short',
                        'index': False
                    },
                    'rect_src': {
                        'type': 'integer',
                        'index': False
                    },
                    'src_id': {
                        'type': 'keyword',
                        'index': False
                    },
                }
            },
            'para_ids': {'type': 'keyword'},
            'para_alignment': {
                'type': 'nested',
                'properties': {
                    'off_start': {
                        'type': 'short',
                        'index': False
                    },
                    'off_end': {
                        'type': 'short',
                        'index': False
                    },
                    'para_id': {
                        'type': 'keyword',
                        'index': False
                    },
                    'sent_ids': {
                        'type': 'integer',
                        'index': False
                    }
                }
            },
            'style_spans': {
                'type': 'nested',
                'properties': {
                    'off_start': {
                        'type': 'short',
                        'index': False
                    },
                    'off_end': {
                        'type': 'short',
                        'index': False
                    },
                    'span_class': {
                        'type': 'keyword',
                        'index': False
                    }
                }
            },
            'segment_ids': {
                'type': 'integer',
                'index': False
            }
        }

        sentMetaDict = {
            'sent_analyses_kw': {
                'type': 'keyword'
            },
            'year': {
                'type': 'integer'
            }
        }
        # Document-level metadata that should be denormalized, i.e., included
        # in each sentence of the document to speed up search
        if 'doc_to_sentence_meta' in self.settings:
            for meta in self.settings['doc_to_sentence_meta']:
                if meta in doc_mapping['mappings']['properties']:
                    sentMetaDict[meta] = doc_mapping['mappings']['properties'][meta]
                if meta + '_kw' in doc_mapping['mappings']['properties']:
                    sentMetaDict[meta + '_kw'] = doc_mapping['mappings']['properties'][meta + '_kw']
        # Normal sentence-level metadata
        for meta in self.settings['sentence_meta']:
            if meta.startswith('year') or ('integer_meta_fields' in self.settings
                                           and meta in self.settings['integer_meta_fields']):
                sentMetaDict[meta] = {'type': 'integer'}
            else:
                sentMetaDict[meta] = {'type': 'text'}
                sentMetaDict[meta + '_kw'] = {'type': 'keyword'}
        if len(sentMetaDict) > 0:
            m['meta'] = {'properties': sentMetaDict}

        # Large corpora on machines with enough CPU cores
        # are split into shards, so that searches can run in parallel
        # on different pieces of the corpus.
        numShards = 1
        cpuCount = os.cpu_count()
        if (corpusSizeInBytes > self.MULTIPLE_SHARDS_THRESHOLD
                and cpuCount is not None and cpuCount > 2
                and ('partitions' not in self.settings or int(self.settings['partitions']) < 2)):
            numShards = cpuCount - 1
        mapping = {
            'mappings': {
                'properties': m
            },
            'settings': {
                'number_of_shards': numShards,
                'analysis': self.wfAnalyzer,
                'refresh_interval': '30s',
                'max_regex_length': 5000,
                'mapping': {
                    'nested_objects.limit': 50000
                }
            }
        }
        mapping['settings']['analysis']['analyzer'].update(self.docNormalizer['analysis']['analyzer'])
        return mapping

    def generate_mappings(self):
        """
        Return Elasticsearch mappings for all types to be used
        in the corpus database.
        """
        mSentWord = self.generate_words_mapping(wordFreqs=False)
        mWord = self.generate_words_mapping()
        mDoc = self.generate_docs_mapping()
        mSent = self.generate_sentences_mapping(mSentWord, mDoc)
        mappings = {
            'docs': mDoc,
            'sentences': mSent,
            'words': mWord
        }
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

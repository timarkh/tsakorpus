"""
Contains a class that handles corpus settings. Its main
functions are reading the settings files and restoring the
defaults if some keys are absent in corpus.json.
"""


import json
import copy


class CorpusSettings:
    """
    Properties of this class correspond to the keys in corpus.json.
    """
    def __init__(self):
        # General information
        self.corpus_name = ''
        self.input_format = 'json'

        # Corpus type
        self.images = False
        self.media = False
        self.media_length = 60
        self.media_youtube = False

        # Metadata and annotation
        self.sentence_meta = []
        self.sentence_meta_values = {}
        self.viewable_meta = []
        self.word_fields = []
        self.search_meta = {'columns': [], 'stat_options': []}
        self.ambiguous_analyses = True
        self.keep_lemma_order = False

        # Search options
        self.debug = False
        self.all_language_search_enabled = True
        self.fulltext_search_enabled = True
        self.negative_search_enabled = True
        self.gloss_search_enabled = True
        self.year_sort_enabled = False
        self.fulltext_view_enabled = False
        self.max_docs_retrieve = 9999
        self.max_words_in_sentence = 40
        self.max_context_expand = 5
        self.max_distance_filter = 200000
        self.max_hits_retrieve = 10000
        self.query_timeout = 60

        # Interface options and tools
        self.interface_languages = ['en', 'ru']
        self.default_locale = 'en'
        self.transliterations = None
        self.input_methods = None
        self.generate_dictionary = False
        self.author_metafield = None
        self.word_fields_by_tier = {}
        self.auto_switch_tiers = {}
        self.line_plot_meta = ['year']    # metadata fields whose statistics can be displayed on a line plot
        self.multiple_choice_fields = []
        self.integer_meta_fields = []
        self.word_table_fields = []
        self.default_values = {}
        self.sentence_meta_values = {}
        self.display_freq_rank = True
        self.word_search_display_gr = True
        self.citation = None
        self.start_page_url = None
        self.fulltext_page_size = 100     # Size of one page of the full-text representation in sentences

        # Languages and their properties
        self.languages = []
        self.rtl_languages = []
        self.context_header_rtl = False
        self.categories = {}
        self.lang_props = {}

        # Statistics calculated at runtime
        self.corpus_size = 0
        self.word_freq_by_rank = []      # number of word types for each frequency rank
        self.lemma_freq_by_rank = []     # number of lemmata for each frequency rank
        self.ready_for_work = False      # turns True when all initialization queries have been made

    def load_settings(self, fnameCorpus, fnameCategories):
        """
        Load corpus settings from JSON files (corpus.json and categories.json).
        """
        with open(fnameCorpus, 'r', encoding='utf-8') as fCorpus:
            settings = json.load(fCorpus)
        for k, v in settings.items():
            setattr(self, k, v)
        with open(fnameCategories, 'r', encoding='utf-8') as fCategories:
            self.categories = json.load(fCategories)

        # Add empty dictionary for each language absent in categories.json:
        for lang in self.languages:
            if lang not in self.categories:
                self.categories[lang] = {}

        if 'stat_options' not in self.search_meta:
            self.search_meta['stat_options'] = []

    def as_dict(self):
        """
        Return current settings as a dictionary. Only include
        parameters relevant for corpus.json.
        """
        badFields = {
            'ready_for_work',
            'corpus_size',
            'word_freq_by_rank',
            'lemma_freq_by_rank'
        }
        dictSettings = copy.deepcopy(vars(self))
        for k in [_ for _ in dictSettings.keys()]:
            if k in badFields:
                del dictSettings[k]
        return dictSettings

    def save_settings(self, fname):
        """
        Save current settings as a JSON file (can be used to edit
        corpus.json through a web interface).
        """
        dictSettings = self.as_dict()
        with open(fname, 'w', encoding='utf-8') as fOut:
            json.dump(dictSettings, fOut, sort_keys=True, ensure_ascii=False, indent=2)

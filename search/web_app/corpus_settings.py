"""
Contains a class that handles corpus settings. Its main
functions are reading the settings files and restoring the
defaults if some keys are absent in corpus.json.
"""


import json
import copy
import re
import os
import shutil
if __name__.startswith('web_app.'):
    from . import load_csv_translations


class CorpusSettings:
    """
    Properties of this class correspond to the keys in corpus.json.
    """

    def __init__(self):
        # General information
        self.corpus_name = ''
        self.input_format = 'json'
        self.elastic_url = ''

        # Corpus type
        self.images = False
        self.media = False
        self.video = False
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

        # Indexation and search options
        self.debug = False
        self.sample_size = 1.0
        self.all_language_search_enabled = True
        self.fulltext_search_enabled = True
        self.negative_search_enabled = True
        self.gloss_search_enabled = True
        self.year_sort_enabled = False
        self.sent_id_sort_enabled = False
        self.fulltext_view_enabled = False
        self.max_docs_retrieve = 9999
        self.max_words_in_sentence = 40
        self.max_context_expand = 5
        self.max_distance_filter = 200000
        self.max_hits_retrieve = 10000      # Increasing this value will have no effect unless you also reconfigure Elasticsearch
        self.query_timeout = 60
        self.max_suggestions = 8

        # Interface options and tools
        self.interface_languages = ['en', 'ru']
        self.default_locale = 'en'
        self.transliterations = None
        self.input_methods = None
        self.keyboards = {}
        self.generate_dictionary = False
        self.author_metafield = None
        self.line_plot_meta = ['year']    # metadata fields whose statistics can be displayed on a line plot
        self.multiple_choice_fields = {}
        self.integer_meta_fields = []
        self.word_table_fields = []
        self.default_values = {}
        self.sentence_meta_values = {}
        self.display_freq_rank = True
        self.word_search_display_gr = True
        self.citation = None
        self.start_page_url = None
        self.fulltext_page_size = 100     # Size of one page of the full-text representation in sentences
        self.accidental_word_fields = []
        self.default_view = 'standard'

        # Languages and their properties
        self.languages = []
        self.rtl_languages = []
        self.context_header_rtl = False
        self.categories = {}
        self.lang_props = {}
        self.auto_switch_tiers = {}

        # Regexes etc.
        self.wf_analyzer_pattern = None
        self.wf_lowercase = True
        self.regex_simple_search = None
        self.search_remove_whitespaces = True
        self.detect_lemma_queries = False

        # Server configuration
        self.session_cookie_domain = None
        self.query_log = True
        self.try_restart_elastic = True     # Try restarting elasticsearch.service if it is down

        # Statistics calculated at runtime
        self.corpus_size = 0
        self.word_freq_by_rank = []      # number of word types for each frequency rank
        self.lemma_freq_by_rank = []     # number of lemmata for each frequency rank
        self.ready_for_work = False      # turns True when all initialization queries have been made

        # Parameters restructured for convenience
        self.word_fields_by_tier = {}

        self.booleanFields = set(k for k in self.__dict__
                                 if type(self.__dict__[k]) == bool)
        self.integerFields = set(k for k in self.__dict__
                                 if type(self.__dict__[k]) == int)
        self.lsFields = {
            'sentence_meta',
            'viewable_meta',
            'word_fields',
            'interface_languages',
            'transliterations',
            'input_methods',
            'line_plot_meta',
            'integer_meta_fields',
            'word_table_fields',
            'accidental_word_fields',
            'languages',
            'rtl_languages',
            'search_meta.stat_options'
        }

        # dictionaries where values are strings
        self.dict_sFields = {
            'auto_switch_tiers',
            'default_values',
            'keyboards'
        }

        # dictionaries where values are lists of strings,
        # including elements of lang_props.
        self.dict_lsFields = {
            'lang_props.dictionary_categories',
            'lang_props.exclude_fields',
            'lang_props.gr_fields_order',
            'lang_props.lexicographic_order',
            'lang_props.other_fields_order',
            'lang_props.word_fields'
        }

        # dictionaries where values are dictionaries {k: string},
        # including elements of lang_props.
        self.dict_dFields = {
            'lang_props.gramm_shortcuts',
            'lang_props.gloss_shortcuts'
        }

        # Fields that should never be saved to corpus.json.
        self.hiddenFields = {
            'ready_for_work',
            'corpus_size',
            'word_freq_by_rank',
            'lemma_freq_by_rank',
            'categories'
        }

    def update_format(self):
        """
        Rename keys that have been changed since Tsakorpus 1.0.
        """
        for lang in self.lang_props:
            if 'gramm_selection' in self.lang_props[lang]:
                for el in self.lang_props[lang]['gramm_selection']:
                    if 'type' in el and el['type'] in ('gramm', 'gloss'):
                        el['type'] = 'tag'
            if 'gloss_selection' in self.lang_props[lang]:
                for el in self.lang_props[lang]['gloss_selection']:
                    if 'type' in el and el['type'] in ('gramm', 'gloss'):
                        el['type'] = 'tag'
        for lang in self.word_fields_by_tier:
            if lang not in self.languages:
                continue
            if lang not in self.lang_props:
                self.lang_props[lang] = {}
            if 'word_fields' not in self.lang_props[lang]:
                self.lang_props[lang]['word_fields'] = []
            self.lang_props[lang]['word_fields'] = [f for f in sorted(set(self.lang_props[lang]['word_fields'])
                                                                      | set(self.word_fields_by_tier[lang]))]

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
        self.update_format()

        # Add empty dictionary for each language absent in categories.json and lang_props:
        for lang in self.languages:
            if lang not in self.categories:
                self.categories[lang] = {}
            if lang not in self.lang_props:
                self.lang_props[lang] = {}

        if 'stat_options' not in self.search_meta:
            self.search_meta['stat_options'] = []

        # Move data to self.word_fields_by_tier for convenience
        self.word_fields_by_tier = {}
        for lang in self.lang_props:
            if 'word_fields' in self.lang_props[lang]:
                self.word_fields_by_tier[lang] = self.lang_props[lang]['word_fields']

        # Glosses are searched in lowercase (maybe that will change in the future)
        for lang in self.lang_props:
            if 'gloss_shortcuts' in self.lang_props[lang]:
                curGlossShortcuts = copy.deepcopy(self.lang_props[lang]['gloss_shortcuts'])
                for k, v in curGlossShortcuts.items():
                    self.lang_props[lang]['gloss_shortcuts'][k.lower()] = v.lower()

    def as_dict(self):
        """
        Return current settings as a dictionary. Only include
        parameters relevant for corpus.json.
        """
        dictSettings = copy.deepcopy(vars(self))
        for k in [_ for _ in dictSettings.keys()]:
            if k in self.hiddenFields:
                del dictSettings[k]
            elif dictSettings[k] is None:
                dictSettings[k] = ''
        return dictSettings

    def gui_str_to_dict(self, s, value_type='list'):
        """
        Process one input string that describes a dictionary.
        """
        d = {}
        s = s.replace('\r', '').strip()
        s = re.sub('\n\n+', '\n', s, flags=re.DOTALL)
        if value_type == 'dict':
            prevKey = ''
            curData = {}
            for line in s.split('\n'):
                if not line.startswith(' '):
                    curKey = line.strip(': ')
                    if len(prevKey) > 0 and curKey != prevKey:
                        d[prevKey] = curData
                        curData = {}
                    prevKey = curKey
                else:
                    line = line.strip()
                    if ':' not in line:
                        continue
                    k, v = line.split(':')
                    k = k.rstrip()
                    v = v.lstrip()
                    curData[k] = v
            if len(curData) > 0:
                d[prevKey] = curData
        else:
            for line in s.split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                k, v = line.split(':')
                k = k.rstrip()
                v = v.lstrip()
                if value_type == 'list':
                    if len(v) <= 0:
                        v = []
                    else:
                        v = [vp.strip() for vp in v.split(',')]
                d[k] = v
        return d

    def extract_lang_props_values(self, data):
        """
        Extract values of lang_props dictionary from the
        GUI form data.
        """
        langProps = {}
        grammSel = {}
        grammSelLangs = {}
        glossSel = {}
        glossSelLangs = {}
        for k, v in data.items():
            if not k.startswith('lang_props.') or '%' in k:
                continue
            k = k[len('lang_props.'):]
            if 'lang_props.' + k in self.dict_sFields:
                curDict = self.gui_str_to_dict(v, value_type='string')
                for lang in curDict:
                    if lang not in langProps:
                        langProps[lang] = {}
                    langProps[lang][k] = curDict[lang]
            elif 'lang_props.' + k in self.dict_lsFields:
                curDict = self.gui_str_to_dict(v, value_type='list')
                for lang in curDict:
                    if lang not in langProps:
                        langProps[lang] = {}
                    langProps[lang][k] = curDict[lang]
            elif 'lang_props.' + k in self.dict_dFields:
                curDict = self.gui_str_to_dict(v, value_type='dict')
                for lang in curDict:
                    if lang not in langProps:
                        langProps[lang] = {}
                    langProps[lang][k] = curDict[lang]
            elif k.startswith('gloss_selection_'):
                m = re.search('gloss_selection_([0-9]+)[._]([a-z]+)', k)
                if m is None:
                    continue
                nLang = m.group(1)
                elType = m.group(2)
                if nLang not in glossSel:
                    glossSel[nLang] = {}
                if elType == 'key':
                    glossSelLangs[nLang] = v
                    continue
                elif elType == 'columns':
                    m = re.search('gloss_selection_([0-9]+)\\.columns_([0-9]+)_([0-9]+)_([a-z]+)', k)
                    if m is None:
                        continue
                    nCol = m.group(2)
                    nRow = m.group(3)
                    attr = m.group(4)
                    if nCol not in glossSel[nLang]:
                        glossSel[nLang][nCol] = {}
                    if nRow not in glossSel[nLang][nCol]:
                        glossSel[nLang][nCol][nRow] = {}
                    glossSel[nLang][nCol][nRow][attr] = v
            elif k.startswith('gramm_selection_'):
                m = re.search('gramm_selection_([0-9]+)[._]([a-z]+)', k)
                if m is None:
                    continue
                nLang = m.group(1)
                elType = m.group(2)
                if nLang not in grammSel:
                    grammSel[nLang] = {}
                if elType == 'key':
                    grammSelLangs[nLang] = v
                    continue
                elif elType == 'columns':
                    m = re.search('gramm_selection_([0-9]+)\\.columns_([0-9]+)_([0-9]+)_([a-z]+)', k)
                    if m is None:
                        continue
                    nCol = m.group(2)
                    nRow = m.group(3)
                    attr = m.group(4)
                    if nCol not in grammSel[nLang]:
                        grammSel[nLang][nCol] = {}
                    if nRow not in grammSel[nLang][nCol]:
                        grammSel[nLang][nCol][nRow] = {}
                    grammSel[nLang][nCol][nRow][attr] = v
        for nLang in glossSelLangs:
            if glossSelLangs[nLang] not in langProps:
                langProps[glossSelLangs[nLang]] = {}
            langProps[glossSelLangs[nLang]]['gloss_selection'] = {'columns': []}
            for nCol in sorted(glossSel[nLang], key=lambda x: int(x)):
                curCol = []
                for nRow in sorted(glossSel[nLang][nCol], key=lambda x: int(x)):
                    curEl = glossSel[nLang][nCol][nRow]
                    if 'category' in curEl:
                        del curEl['category']
                    curCol.append(curEl)
                langProps[glossSelLangs[nLang]]['gloss_selection']['columns'].append(curCol)
        for nLang in grammSelLangs:
            if grammSelLangs[nLang] not in langProps:
                langProps[grammSelLangs[nLang]] = {}
            langProps[grammSelLangs[nLang]]['gramm_selection'] = {'columns': []}
            for nCol in sorted(grammSel[nLang], key=lambda x: int(x)):
                curCol = []
                for nRow in sorted(grammSel[nLang][nCol], key=lambda x: int(x)):
                    curEl = grammSel[nLang][nCol][nRow]
                    if 'type' in curEl and curEl['type'] in ('header', 'separator'):
                        if 'category' in curEl:
                            del curEl['category']
                        if 'tooltip' in curEl:
                            del curEl['tooltip']
                    curCol.append(curEl)
                langProps[grammSelLangs[nLang]]['gramm_selection']['columns'].append(curCol)

        return langProps

    def extract_search_meta_values(self, data):
        """
        Extract values of search_meta dictionary from the
        GUI form data.
        """
        searchMetaColumns = {}
        searchMeta = {'columns': [], 'stat_options': []}
        for k, v in data.items():
            if not k.startswith('search_meta.') or '%' in k:
                continue
            k = k[len('search_meta.'):]
            if k == 'stat_options':
                searchMeta['stat_options'] = [vp.strip() for vp in v.replace('\r', '').strip().split('\n')]
            elif k.startswith('columns_'):
                m = re.search('columns_([0-9]+)_([0-9]+)_([a-z]+)', k)
                if m is None:
                    continue
                nCol = m.group(1)
                nRow = m.group(2)
                attr = m.group(3)
                if nCol not in searchMetaColumns:
                    searchMetaColumns[nCol] = {}
                if nRow not in searchMetaColumns[nCol]:
                    searchMetaColumns[nCol][nRow] = {}
                searchMetaColumns[nCol][nRow][attr] = v

        for nCol in sorted(searchMetaColumns, key=lambda x: int(x)):
            curCol = []
            for nRow in sorted(searchMetaColumns[nCol], key=lambda x: int(x)):
                curEl = searchMetaColumns[nCol][nRow]
                curCol.append(curEl)
            searchMeta['columns'].append(curCol)
        return searchMeta

    def extract_multiple_choice_fields_values(self, data):
        """
        Extract values of multiple_choice_fields dictionary from the
        GUI form data.
        """
        multipleChoiceFields = {}
        fieldsTmp = {}
        fieldNames = {}
        for k, v in data.items():
            if k.startswith('multiple_choice_fields_'):
                m = re.search('multiple_choice_fields_([0-9]+)[._]([a-z]+)', k)
                if m is None:
                    continue
                nField = m.group(1)
                elType = m.group(2)
                if nField not in fieldNames:
                    fieldsTmp[nField] = {}
                if elType == 'key':
                    fieldNames[nField] = v
                    continue
                elif elType == 'columns':
                    m = re.search('multiple_choice_fields_([0-9]+)\\.columns_([0-9]+)_([0-9]+)_([a-z]+)', k)
                    if m is None:
                        continue
                    nCol = m.group(2)
                    nRow = m.group(3)
                    attr = m.group(4)
                    if nCol not in fieldsTmp[nField]:
                        fieldsTmp[nField][nCol] = {}
                    if nRow not in fieldsTmp[nField][nCol]:
                        fieldsTmp[nField][nCol][nRow] = {}
                    fieldsTmp[nField][nCol][nRow][attr] = v

        for nField in fieldNames:
            multipleChoiceFields[fieldNames[nField]] = {'columns': []}
            for nCol in sorted(fieldsTmp[nField], key=lambda x: int(x)):
                curCol = []
                for nRow in sorted(fieldsTmp[nField][nCol], key=lambda x: int(x)):
                    curEl = fieldsTmp[nField][nCol][nRow]
                    curCol.append(curEl)
                multipleChoiceFields[fieldNames[nField]]['columns'].append(curCol)

        return multipleChoiceFields

    def processed_gui_settings(self, data):
        """
        Turn form data filled by the user in the configuration GUI to
        a dictionary in the correct format.
        """
        dictSettings = {}
        for f in self.booleanFields:
            if f.startswith(('lang_props.', 'search_meta.')):
                continue
            if f in self.hiddenFields:
                continue
            if f in data and len(data[f]) > 0:
                dictSettings[f] = True
            else:
                dictSettings[f] = False
        for f in self.integerFields:
            if f.startswith(('lang_props.', 'search_meta.')):
                continue
            if f in self.hiddenFields:
                continue
            if f in data and len(data[f]) > 0:
                dictSettings[f] = int(data[f])
        for f in self.lsFields:
            if f.startswith(('lang_props.', 'search_meta.')):
                continue
            if f in self.hiddenFields:
                continue
            if f in data and len(data[f]) > 0:
                dictSettings[f] = [v.strip() for v in data[f].replace('\r', '').strip().split('\n')]
            else:
                dictSettings[f] = []
        for f in self.dict_sFields:
            if f.startswith(('lang_props.', 'search_meta.')):
                continue
            if f in self.hiddenFields:
                continue
            if f in data and len(data[f]) > 0:
                dictSettings[f] = self.gui_str_to_dict(data[f], value_type='string')
            else:
                dictSettings[f] = {}
        for f in self.dict_lsFields:
            if f.startswith(('lang_props.', 'search_meta.')):
                continue
            if f in self.hiddenFields:
                continue
            if f in data and len(data[f]) > 0:
                dictSettings[f] = self.gui_str_to_dict(data[f], value_type='list')
            else:
                dictSettings[f] = {}
        dictSettings['lang_props'] = self.extract_lang_props_values(data)
        dictSettings['search_meta'] = self.extract_search_meta_values(data)
        dictSettings['multiple_choice_fields'] = self.extract_multiple_choice_fields_values(data)
        for k, v in data.items():
            if k.startswith(('lang_props.', 'search_meta.', 'multiple_choice_fields_')):
                continue
            if '%' in k:
                continue
            if k not in dictSettings:
                dictSettings[k] = v
        return dictSettings

    def save_settings(self, fname, data=None):
        """
        Save current or new settings as a JSON file (can be used to edit
        corpus.json through a web interface).
        """
        if data is None or len(data) <= 0:
            dictSettings = self.as_dict()
        else:
            dictSettings = self.processed_gui_settings(data)
        with open(fname, 'w', encoding='utf-8') as fOut:
            json.dump(dictSettings, fOut, sort_keys=True, ensure_ascii=False, indent=2)

    def write_translation_csv(self, existingTranslations, values, fnameOut):
        """
        Write one tab-delimited translation file based on the values that need
        to be translated and data from an existing translation file.
        """
        with open(fnameOut, 'w', encoding='utf-8') as fOut:
            for k in sorted(existingTranslations):
                fOut.write(k + '\t' + existingTranslations[k] + '\n')
            fOut.write('\n')
            for v in sorted(values):
                v = v.replace('\t', ' ').replace('\n', '\\n')
                if v not in existingTranslations:
                    fOut.write(v + '\t' + v + '\n')

    def prepare_translation(self, dirname, langSrc, langTarget, data):
        """
        Generate corpus-specific translation files for one
        language (langTarget) based on the existing translation
        (langSrc) and the data entered by the user.
        """
        srcDir = os.path.join('web_app/translations', langSrc)
        targetDir = os.path.join(dirname, langTarget)
        shutil.copy2(os.path.join(srcDir, 'header.txt'),
                     os.path.join(targetDir, 'header.txt'))
        shutil.copy2(os.path.join(srcDir, 'main.txt'),
                     os.path.join(targetDir, 'main.txt'))
        shutil.copy2(os.path.join(srcDir, 'corpus-specific.txt'),
                     os.path.join(targetDir, 'corpus-specific.txt'))
        inputMethods = load_csv_translations(os.path.join(srcDir, 'input_methods.txt'))
        languages = load_csv_translations(os.path.join(srcDir, 'languages.txt'))
        metaFields = load_csv_translations(os.path.join(srcDir, 'metadata_fields.txt'))
        metaValues = load_csv_translations(os.path.join(srcDir, 'metadata_values.txt'))
        tooltips = load_csv_translations(os.path.join(srcDir, 'tooltips.txt'))
        transliterations = load_csv_translations(os.path.join(srcDir, 'transliterations.txt'))
        wordFields = load_csv_translations(os.path.join(srcDir, 'word_fields.txt'))
        self.write_translation_csv(inputMethods, data['input_methods'],
                                   os.path.join(targetDir, 'input_methods.txt'))
        self.write_translation_csv(languages, data['languages'],
                                   os.path.join(targetDir, 'languages.txt'))
        self.write_translation_csv(metaFields, list(set(data['viewable_meta']) | set(data['sentence_meta'])),
                                   os.path.join(targetDir, 'metadata_fields.txt'))
        newSentMetaValues = []
        if 'sentence_meta_values' in data:
            newSentMetaValues = [v
                                 for field in data['sentence_meta_values']
                                 for v in data['sentence_meta_values'][field]]
        self.write_translation_csv(metaValues, newSentMetaValues,
                                   os.path.join(targetDir, 'metadata_values.txt'))
        self.write_translation_csv(transliterations, data['transliterations'],
                                   os.path.join(targetDir, 'transliterations.txt'))
        self.write_translation_csv(wordFields, data['word_fields'],
                                   os.path.join(targetDir, 'word_fields.txt'))
        newTooltips = set()
        for lang in data['lang_props']:
            if ('gramm_selection' in data['lang_props'][lang]
                    and 'columns' in data['lang_props'][lang]['gramm_selection']):
                for col in data['lang_props'][lang]['gramm_selection']['columns']:
                    for el in col:
                        if 'tooltip' in el:
                            newTooltips.add(el['tooltip'])
                        elif 'type' in el and 'value' in el and el['type'] == 'header':
                            newTooltips.add(el['value'])
            if ('gloss_selection' in data['lang_props'][lang]
                    and 'columns' in data['lang_props'][lang]['gloss_selection']):
                for col in data['lang_props'][lang]['gloss_selection']['columns']:
                    for el in col:
                        if 'tooltip' in el:
                            newTooltips.add(el['tooltip'])
                        elif 'type' in el and 'value' in el and el['type'] == 'header':
                            newTooltips.add(el['value'])
        if 'multiple_choice_fields' in data and 'columns' in data['multiple_choice_fields']:
            for col in data['multiple_choice_fields']['columns']:
                for el in col:
                    if 'tooltip' in el:
                        newTooltips.add(el['tooltip'])
                    elif 'type' in el and 'value' in el and el['type'] == 'header':
                        newTooltips.add(el['value'])
        self.write_translation_csv(tooltips, list(newTooltips),
                                   os.path.join(targetDir, 'tooltips.txt'))

    def prepare_translations(self, dirname, data=None):
        """
        Generate corpus-specific translation files based on the
        data eneterd by the user.
        """
        dictSettings = self.processed_gui_settings(data)
        for interfaceLang in dictSettings['interface_languages']:
            langSrc = interfaceLang
            if not os.path.exists(os.path.join('../USER_CONFIG/translations', interfaceLang)):
                os.makedirs(os.path.join('../USER_CONFIG/translations', interfaceLang))
            if not os.path.exists(os.path.join('web_app/translations', interfaceLang)):
                langSrc = 'en'
            self.prepare_translation(dirname, langSrc, interfaceLang, dictSettings)
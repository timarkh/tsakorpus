from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import RequestError
import json
import ijson
import os
import re
import time
import math
import random
import sys
import subprocess
from prepare_data import PrepareData
from json_doc_reader import JSONDocReader


class Indexator:
    """
    Contains methods for loading the JSON documents in the corpus
    database.
    """
    SETTINGS_DIR = '../conf'

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.languages = self.settings['languages']
        if len(self.languages) <= 0:
            self.languages = [self.name]
        self.input_format = self.settings['input_format']
        self.corpus_dir = os.path.join('../corpus', self.name)
        self.iterSent = None
        if self.input_format in ['json', 'json-gzip']:
            self.iterSent = JSONDocReader(format=self.input_format)
        self.goodWordFields = ['lex', 'wf', 'wf_display',
                               'parts', 'gloss', 'gloss_index', 'n_ana',
                               'trans_en', 'trans_ru']
        self.AdditionalWordFields = set()
        if 'word_fields' in self.settings:
            self.AdditionalWordFields |= set(self.settings['word_fields'])
        if 'word_table_fields' in self.settings:
            self.AdditionalWordFields |= set(self.settings['word_table_fields'])
        if 'accidental_word_fields' in self.settings:
            self.AdditionalWordFields -= set(self.settings['accidental_word_fields'])
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        categories = json.loads(f.read())
        self.goodWordFields += ['gr.' + v for lang in categories
                                for v in categories[lang].values()]
        self.goodWordFields = set(self.goodWordFields)
        f.close()
        self.pd = PrepareData()
        self.es = Elasticsearch()
        self.es_ic = IndicesClient(self.es)
        self.shuffled_ids = [i for i in range(1, 1000000)]
        random.shuffle(self.shuffled_ids)
        self.shuffled_ids.insert(0, 0)    # id=0 is special and should not change
        self.tmpWordIDs = [{} for i in range(len(self.languages))]    # word as JSON -> its integer ID
        self.tmpLemmaIDs = [{} for i in range(len(self.languages))]   # lemma as string -> its integer ID
        self.word2lemma = [{} for i in range(len(self.languages))]    # word's ID -> ID of its lemma (or -1, if none)
        self.wordFreqs = [{} for i in range(len(self.languages))]     # word's ID -> its frequency
        self.wordSFreqs = [{} for i in range(len(self.languages))]    # word's ID -> its number of sentences
        self.wordDocFreqs = [{} for i in range(len(self.languages))]  # (word's ID, dID) -> word frequency in the document
        # self.wordSIDs = [{} for i in range(len(self.languages))]      # word's ID -> set of sentence IDs
        self.wordDIDs = [{} for i in range(len(self.languages))]      # word's ID -> set of document IDs
        self.wfs = set()         # set of word forms (for sorting)
        self.lemmata = set()     # set of lemmata (for sorting)
        self.sID = 0          # current sentence ID for each language
        self.dID = 0          # current document ID
        self.wID = 0          # current word ID
        self.wordFreqID = 0
        self.numWords = 0     # number of words in current document
        self.numSents = 0     # number of sentences in current document
        self.numWordsLang = [0] * len(self.languages)    # number of words in each language in current document
        self.numSentsLang = [0] * len(self.languages)    # number of sentences in each language in current document
        self.totalNumWords = 0

    def delete_indices(self):
        if self.es_ic.exists(index=self.name + '.docs'):
            self.es_ic.delete(index=self.name + '.docs')
        if self.es_ic.exists(index=self.name + '.words'):
            self.es_ic.delete(index=self.name + '.words')
        if self.es_ic.exists(index=self.name + '.word_freqs'):
            self.es_ic.delete(index=self.name + '.word_freqs')
        if self.es_ic.exists(index=self.name + '.sentences'):
            self.es_ic.delete(index=self.name + '.sentences')

    def create_indices(self):
        self.wordMapping = self.pd.generate_words_mapping()
        self.wordFreqMapping = self.pd.generate_wordfreq_mapping()
        self.sentMapping = self.pd.generate_sentences_mapping(self.wordMapping)
        self.docMapping = self.pd.generate_docs_mapping()
        self.es_ic.create(index=self.name + '.docs',
                          body=self.docMapping)
        self.es_ic.create(index=self.name + '.words',
                          body=self.wordMapping)
        self.es_ic.create(index=self.name + '.sentences',
                          body=self.sentMapping)

    def randomize_id(self, realID):
        """
        Return a (relatively) randomized sentence ID. This randomization
        is needed in context-aware word queries where the sentences
        are iterated in the order determined by their IDs.
        """
        if realID < 0:
            return realID
        idStart, idEnd = realID // 1000000, realID % 1000000
        return idStart * 1000000 + self.shuffled_ids[idEnd]

    def enhance_word(self, word):
        """
        Add some calculated fields to the JSON word.
        """
        if 'ana' not in word:
            word['n_ana'] = 0
        else:
            word['n_ana'] = len(word['ana'])
            if word['n_ana'] >= 127:
                word['n_ana'] = 127

    def process_sentence_words(self, words, langID):
        """
        Take words list from a sentence, remove all non-searchable
        fields from them and add them to self.words dictionary.
        Add w_id and l_id properties to each word of the words list.
        Return the value of the 'sent_analyzed' meta field.
        """
        sIDAdded = set()   # word IDs for which the current settence ID has been counted for it
        bUniquelyAnalyzed = True
        bFullyAnalyzed = True
        for w in words:
            if w['wtype'] != 'word':
                continue
            self.numWords += 1
            self.numWordsLang[langID] += 1
            self.totalNumWords += 1
            self.enhance_word(w)
            wClean = {'lang': langID}
            lemma = ''
            for field in w:
                if field in self.goodWordFields or field in self.AdditionalWordFields:
                    wClean[field] = w[field]
                    if field == 'wf':
                        if 'wf_lowercase' not in self.settings or self.settings['wf_lowercase']:
                            wClean[field] = wClean[field].lower()
                        self.wfs.add(wClean[field])
            if 'ana' in w:
                if len(w['ana']) > 1:
                    bUniquelyAnalyzed = False
                lemma = self.get_lemma(w)
                self.lemmata.add(lemma)
                wClean['ana'] = []
                for ana in w['ana']:
                    cleanAna = {}
                    for anaField in ana:
                        if anaField in self.goodWordFields or anaField in self.AdditionalWordFields:
                            cleanAna[anaField] = ana[anaField]
                    wClean['ana'].append(cleanAna)
            if 'ana' not in w or len(w['ana']) <= 0:
                bFullyAnalyzed = False
                bUniquelyAnalyzed = False
            wCleanTxt = json.dumps(wClean, ensure_ascii=False, sort_keys=True)
            if wCleanTxt in self.tmpWordIDs[langID]:
                wID = self.tmpWordIDs[langID][wCleanTxt]
            else:
                wID = sum(len(self.tmpWordIDs[i]) for i in range(len(self.languages)))
                self.tmpWordIDs[langID][wCleanTxt] = wID
            w['w_id'] = wID
            if len(lemma) > 0:
                try:
                    lemmaID = self.tmpLemmaIDs[langID][lemma]
                except KeyError:
                    lemmaID = sum(len(self.tmpLemmaIDs[i])
                                  for i in range(len(self.languages))) + 1
                    self.tmpLemmaIDs[langID][lemma] = lemmaID
                self.word2lemma[langID][wID] = lemmaID
                w['l_id'] = lemmaID
            try:
                self.wordFreqs[langID][wID] += 1
            except KeyError:
                self.wordFreqs[langID][wID] = 1
            if wID not in sIDAdded:
                sIDAdded.add(wID)
                try:
                    self.wordSFreqs[langID][wID] += 1
                except KeyError:
                    self.wordSFreqs[langID][wID] = 1
            try:
                self.wordDIDs[langID][wID].add(self.dID)
            except KeyError:
                self.wordDIDs[langID][wID] = {self.dID}
            try:
                self.wordDocFreqs[langID][(wID, self.dID)] += 1
            except KeyError:
                self.wordDocFreqs[langID][(wID, self.dID)] = 1
        if not bFullyAnalyzed:
            return 'incomplete'
        if not bUniquelyAnalyzed:
            return 'complete'
        return 'unique'

    def make_sorting_function(self, lang):
        """
        Return a function that can be used for sorting tokens
        in a list according to the alphabetical ordering specified
        for the language lang.
        """
        sortingFunction = lambda x: x
        if lang in self.settings['lang_props'] and 'lexicographic_order' in self.settings['lang_props'][lang]:
            dictSort = {self.settings['lang_props'][lang]['lexicographic_order'][i]:
                            (i, self.settings['lang_props'][lang]['lexicographic_order'][i])
                        for i in range(len(self.settings['lang_props'][lang]['lexicographic_order']))}
            maxIndex = len(dictSort)

            def charReplaceFunction(c):
                if c in dictSort:
                    return dictSort[c]
                return (maxIndex, c)

            sortingFunction = lambda x: [charReplaceFunction(c) for c in x.lower()]
        return sortingFunction

    def sort_words(self, lang):
        """
        Sort word forms and lemmata stored at earlier stages.
        Return dictionaries with positions of word forms and
        lemmata in the sorted list.
        If there is a custom alphabetical order for the language,
        use it. Otherwise, use standard lexicographic sorting.
        """
        wfsSorted = {}
        iOrder = 0
        sortingFunction = self.make_sorting_function(lang)
        for wf in sorted(self.wfs, key=sortingFunction):
            wfsSorted[wf] = iOrder
            iOrder += 1
        lemmataSorted = {}
        iOrder = 0
        for l in sorted(self.lemmata, key=sortingFunction):
            lemmataSorted[l] = iOrder
            iOrder += 1
        return wfsSorted, lemmataSorted

    def get_freq_ranks(self, freqsSorted):
        """
        Calculate frequency ranks and rank/quantile labels for words
        or lemmata.
        """
        freqToRank = {}
        quantiles = {}
        prevFreq = 0
        prevRank = 0
        for i in range(len(freqsSorted)):
            v = freqsSorted[i]
            if v != prevFreq:
                if prevFreq != 0:
                    freqToRank[prevFreq] = prevRank + (i - prevRank) // 2
                prevRank = i
                prevFreq = v
        if prevFreq != 0:
            freqToRank[prevFreq] = prevRank + (len(freqsSorted) - prevRank) // 2
        for q in [0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.25, 0.5]:
            qIndex = math.ceil(q * len(freqsSorted))
            if qIndex >= len(freqsSorted):
                qIndex = len(freqsSorted) - 1
            if qIndex >= 0:
                quantiles[q] = freqsSorted[qIndex]
            else:
                quantiles[q] = 0
        return freqToRank, quantiles

    def quantile_label(self, freq, rank, quantiles):
        """
        Return a string label of the frequency rank (for frequent items)
        or quantile. This label is showed to the user in word query results.
        """
        if freq > 1 and freq >= quantiles[0.5]:
            if freq > quantiles[0.03]:
                return '#' + str(rank + 1)
            else:
                return '&gt; ' + str(min(math.ceil(q * 100) for q in quantiles
                                     if freq >= quantiles[q])) + '%'
        return ''

    def get_lemma(self, word, lower_lemma=True):
        """
        Join all lemmata in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        if 'keep_lemma_order' not in self.settings or not self.settings['keep_lemma_order']:
            curLemmata = set()
            for ana in word['ana']:
                if 'lex' in ana:
                    if type(ana['lex']) == list:
                        for l in ana['lex']:
                            lAdd = l
                            if lower_lemma:
                                lAdd = lAdd.lower()
                            curLemmata.add(lAdd)
                    else:
                        lAdd = ana['lex']
                        if lower_lemma:
                            lAdd = lAdd.lower()
                        curLemmata.add(lAdd)
            return '/'.join(l for l in sorted(curLemmata))
        curLemmata = []
        for ana in word['ana']:
            if 'lex' in ana:
                if type(ana['lex']) == list:
                    for l in ana['lex']:
                        lAdd = l
                        if lower_lemma:
                            lAdd = lAdd.lower()
                        curLemmata.append(lAdd)
                else:
                    lAdd = ana['lex']
                    if lower_lemma:
                        lAdd = lAdd.lower()
                    curLemmata.append(lAdd)
        return '/'.join(curLemmata)

    def get_grdic(self, word, lang):
        """
        Join all dictionary grammar tags strings in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        curGramm = set()
        translations = set()
        for ana in word['ana']:
            grTags = ''
            if 'gr.pos' in ana:
                value = ana['gr.pos']
                if type(value) == list:
                    value = ', '.join(value)
                grTags = value
            for field in sorted(ana):
                value = ana[field]
                if type(value) == list:
                    value = ', '.join(value)
                if ('lang_props' in self.settings
                        and lang in self.settings['lang_props']
                        and 'dictionary_categories' in self.settings['lang_props'][lang]
                        and field.startswith('gr.')
                        and field[3:] in self.settings['lang_props'][lang]['dictionary_categories']):
                    if len(grTags) > 0:
                        grTags += ', '
                    grTags += value
                elif field.startswith('trans_'):
                    translations.add(value)
            if len(grTags) > 0:
                curGramm.add(grTags)
        return ' | '.join(grdic for grdic in sorted(curGramm)), ' | '.join(tr for tr in sorted(translations))

    def iterate_lemmata(self, langID, lemmaFreqs, lemmaDIDs):
        """
        Iterate over all lemmata for one language collected at the
        word iteration stage.
        """
        lFreqsSorted = [v for v in sorted(lemmaFreqs.values(), reverse=True)]
        freqToRank, quantiles = self.get_freq_ranks(lFreqsSorted)
        iLemma = 0
        for l, lID in self.tmpLemmaIDs[langID].items():
            if iLemma % 250 == 0:
                print('indexing lemma', iLemma)
            lemmaJson = {'wf': l,
                         'freq': lemmaFreqs[lID],
                         'rank_true': freqToRank[lemmaFreqs[lID]],
                         'rank': self.quantile_label(lemmaFreqs[lID],
                                                     freqToRank[lemmaFreqs[lID]],
                                                     quantiles),
                         'n_docs': len(lemmaDIDs[lID])}
            curAction = {'_index': self.name + '.words',
                         '_type': 'lemma',
                         '_id': lID,
                         '_source': lemmaJson}
            iLemma += 1
            yield curAction

    def iterate_words(self):
        """
        Iterate through all words collected at the previous
        stage. Return JSON objects with actions for bulk indexing
        in Elasticsearch.
        """
        self.wID = 0

        for langID in range(len(self.languages)):
            wfsSorted, lemmataSorted = self.sort_words(self.languages[langID])
            iWord = 0
            print('Processing words in ' + self.languages[langID] + '...')
            lemmaFreqs = {}       # lemma ID -> its frequency
            lemmaDIDs = {}        # lemma ID -> its document IDs
            wFreqsSorted = [v for v in sorted(self.wordFreqs[langID].values(), reverse=True)]
            freqToRank, quantiles = self.get_freq_ranks(wFreqsSorted)
            # for wID in self.wordFreqs[langID]:
            for w, wID in self.tmpWordIDs[langID].items():
                if iWord % 500 == 0:
                    print('indexing word', iWord)
                try:
                    lID = self.word2lemma[langID][wID]
                except KeyError:
                    lID = 0
                wJson = json.loads(w)
                wfOrder = len(wfsSorted) + 1
                if 'wf' in wJson:
                    wfOrder = wfsSorted[wJson['wf']]
                lOrder = len(lemmataSorted) + 1
                if 'ana' in wJson:
                    lOrder = lemmataSorted[self.get_lemma(wJson)]
                wJson['wf_order'] = wfOrder
                wJson['l_order'] = lOrder
                wordFreq = self.wordFreqs[langID][wID]
                wJson['freq'] = wordFreq
                try:
                    lemmaFreqs[lID] += wordFreq
                except KeyError:
                    lemmaFreqs[lID] = wordFreq
                if lID != 0:
                    try:
                        lemmaDIDs[lID] |= self.wordDIDs[langID][wID]
                    except KeyError:
                        lemmaDIDs[lID] = set(self.wordDIDs[langID][wID])
                # wJson['sids'] = [sid for sid in sorted(self.wordSIDs[langID][wID])]
                wJson['dids'] = [did for did in sorted(self.wordDIDs[langID][wID])]
                wJson['n_sents'] = self.wordSFreqs[langID][wID]
                wJson['n_docs'] = len(wJson['dids'])
                wJson['rank_true'] = freqToRank[wJson['freq']]  # for the calculations
                wJson['rank'] = self.quantile_label(wJson['freq'],
                                                    wJson['rank_true'],
                                                    quantiles)  # for the user
                curAction = {'_index': self.name + '.words',
                             '_type': 'word',
                             '_id': wID,
                             '_source': wJson,
                             '_parent': lID}
                yield curAction

                for docID in wJson['dids']:
                    wfreqJson = {'w_id': wID,
                                 'd_id': docID,
                                 'wf_order': wfOrder,
                                 'l_order': lOrder,
                                 'freq': self.wordDocFreqs[langID][(wID, docID)]}
                    curAction = {'_index': self.name + '.words',
                                 '_type': 'word_freq',
                                 '_id': self.wordFreqID,
                                 '_source': wfreqJson,
                                 '_parent': wID,
                                 '_routing': lID}
                    self.wordFreqID += 1
                    yield curAction
                iWord += 1
                self.wID += 1
            for lAction in self.iterate_lemmata(langID, lemmaFreqs, lemmaDIDs):
                yield lAction
        emptyLemmaJson = {'wf': 0,
                          'freq': 0,
                          'rank_true': -1}
        curAction = {'_index': self.name + '.words',
                     '_type': 'lemma',
                     '_id': 0,
                     '_source': emptyLemmaJson}
        yield curAction
        self.wfs = None
        self.lemmata = None


    def generate_dictionary(self, fnameOut):
        """
        For each language, print out an HTML dictionary containing all lexemes of the corpus.
        """
        for langID in range(len(self.languages)):
            iWord = 0
            print('Generating dictionary for ' + self.languages[langID] + '...')
            lexFreqs = {}       # lemma ID -> its frequency
            wFreqsSorted = [v for v in sorted(self.wordFreqs[langID].values(), reverse=True)]
            freqToRank, quantiles = self.get_freq_ranks(wFreqsSorted)
            # for wID in self.wordFreqs[langID]:
            for w, wID in self.tmpWordIDs[langID].items():
                if iWord % 1000 == 0:
                    print('processing word', iWord, 'for the dictionary')
                iWord += 1
                wJson = json.loads(w)
                if 'ana' not in wJson or len(wJson['ana']) <= 0:
                    continue
                lemma = self.get_lemma(wJson, lower_lemma=False)
                grdic, translations = self.get_grdic(wJson, self.languages[langID])
                wordFreq = self.wordFreqs[langID][wID]
                lexTuple = (lemma, grdic, translations)
                if lexTuple not in lexFreqs:
                    lexFreqs[lexTuple] = wordFreq
                else:
                    lexFreqs[lexTuple] += wordFreq
            if len(lexFreqs) <= 0:
                continue

            fOut = open(os.path.join('../search/web_app/templates', 'dictionary_' + self.settings['corpus_name']
                                     + '_' + self.languages[langID] + '.html'), 'w', encoding='utf-8')
            fOut.write('<h1 class="dictionary_header"> {{ _(\'Dictionary_header\') }} '
                       '({{ _(\'langname_' + self.languages[langID] + '\') }})</h1>\n')
            prevLetter = ''
            sortingFunction = self.make_sorting_function(self.settings['languages'][langID])
            for lemma, grdic, trans in sorted(lexFreqs, key=lambda x: (sortingFunction(x[0].lower()), -lexFreqs[x])):
                if len(lemma) <= 0:
                    continue
                curLetter = lemma.lower()[0]
                if curLetter != prevLetter:
                    if prevLetter != '':
                        fOut.write('</tbody>\n</table>\n')
                    fOut.write('<h2 class="dictionary_letter">' + curLetter.upper() + '</h2>\n')
                    fOut.write('<table class="dictionary_table">\n<thead>\n'
                               '<th>{{ _(\'word_th_lemma\') }}</th>'
                               '<th>{{ _(\'word_th_gr\') }}</th>'
                               '<th>{{ _(\'word_th_trans_en\') }}</th>'
                               '<th>{{ _(\'word_th_frequency\') }}</th>'
                               '</thead>\n<tbody>\n')
                    prevLetter = curLetter
                fOut.write('<tr>\n<td class="dictionary_lemma">' + lemma + '</td><td>' + grdic + '</td>'
                           '<td>' + trans + '</td><td>'
                           + str(lexFreqs[(lemma, grdic, trans)]) + '</td></tr>\n')
            if prevLetter != '':
                fOut.write('</tbody>\n</table>\n')
            fOut.close()

    def index_words(self):
        """
        Index all words that have been collected at the previous stage
        in self.words (while the sentences were being indexed).
        """
        bulk(self.es, self.iterate_words(), chunk_size=300, request_timeout=60)
        if 'generate_dictionary' in self.settings and self.settings['generate_dictionary']:
            self.generate_dictionary(os.path.join(self.corpus_dir, 'dictionary.html'))

    def add_parallel_sids(self, sentences, paraIDs):
        """
        In the parallel corpus, add the IDs of aligned sentences in other languages
        to each sentence that has a para_id.
        """
        for s in sentences:
            if 'para_alignment' not in s['_source'] or 'lang' not in s['_source']:
                continue
            langID = s['_source']['lang']
            for pa in s['_source']['para_alignment']:
                paraID = pa['para_id']
                pa['sent_ids'] = []
                for i in range(len(self.languages)):
                    if i == langID:
                        continue
                    if paraID in paraIDs[i]:
                        pa['sent_ids'] += paraIDs[i][paraID]

    def iterate_sentences(self, fname):
        self.numSents = 0
        prevLast = False
        sentences = []
        paraIDs = [{} for i in range(len(self.languages))]
        for s, bLast in self.iterSent.get_sentences(fname):
            if 'lang' in s:
                langID = s['lang']
            else:
                langID = 0
                s['lang'] = langID
            s['n_words'] = 0
            if 'words' in s:
                sentAnaMeta = self.process_sentence_words(s['words'], langID)
                s['n_words'] = sum(1 for w in s['words'] if 'wtype' in w and w['wtype'] == 'word')
                if 'meta' not in s:
                    s['meta'] = {}
                s['meta']['sent_analyses'] = sentAnaMeta
            if prevLast:
                prevLast = False
            elif self.numSents > 0:
                s['prev_id'] = self.randomize_id(self.sID - 1)
            if not bLast and 'last' not in s:
                s['next_id'] = self.randomize_id(self.sID + 1)
            else:
                prevLast = True
            s['doc_id'] = self.dID
            if 'meta' in s:
                for metaField in [mf for mf in s['meta'].keys() if not (mf.startswith('year') or mf.endswith('_kw'))]:
                    s['meta'][metaField + '_kw'] = s['meta'][metaField]
            # self.es.index(index=self.name + '.sentences',
            #               doc_type='sentence',
            #               id=self.sID,
            #               body=s)
            curAction = {'_index': self.name + '.sentences',
                         '_type': 'sentence',
                         '_id': self.randomize_id(self.sID),
                         '_source': s}
            if len(self.languages) <= 1:
                yield curAction
            else:
                sentences.append(curAction)
                if 'para_alignment' in s:
                    s['para_ids'] = []
                    for pa in s['para_alignment']:
                        paraID = str(self.dID) + '_' + str(pa['para_id'])
                        pa['para_id'] = paraID
                        s['para_ids'].append(paraID)
                        try:
                            paraIDs[langID][paraID].append(self.randomize_id(self.sID))
                        except KeyError:
                            paraIDs[langID][paraID] = [self.randomize_id(self.sID)]
            if self.sID % 500 == 0:
                print('Indexing sentence', self.sID, ',', self.totalNumWords, 'words so far.')
            self.numSents += 1
            self.numSentsLang[langID] += 1
            self.sID += 1
        if len(self.languages) > 1:
            self.add_parallel_sids(sentences, paraIDs)
            for s in sentences:
                yield s

    @staticmethod
    def add_meta_keywords(meta):
        """
        For each text field in the metadata, add a keyword version
        of the same field.
        """
        for field in [k for k in meta.keys() if not k.startswith('year')]:
            meta[field + '_kw'] = meta[field]

    def index_doc(self, fname):
        """
        Store the metadata of the source file.
        """
        if self.dID % 100 == 0:
            print('Indexing document', self.dID)
        meta = self.iterSent.get_metadata(fname)
        self.add_meta_keywords(meta)
        meta['n_words'] = self.numWords
        meta['n_sents'] = self.numSents
        if len(self.settings['languages']) > 1:
            for i in range(len(self.languages)):
                meta['n_words_' + self.languages[i]] = self.numWordsLang[i]
                meta['n_sents_' + self.languages[i]] = self.numSentsLang[i]
        self.numWords = 0
        self.numSents = 0
        self.numWordsLang = [0] * len(self.languages)
        self.numSentsLang = [0] * len(self.languages)
        try:
            self.es.index(index=self.name + '.docs',
                          doc_type='doc',
                          id=self.dID,
                          body=meta)
        except RequestError as err:
            print('Metadata error: {0}'.format(err))
            shortMeta = {}
            if 'filename' in meta:
                shortMeta['filename'] = meta['filename']
            if 'title' in meta:
                shortMeta['title'] = meta['title']
                shortMeta['title_kw'] = meta['title']
                self.es.index(index=self.name + '.docs',
                              doc_type='doc',
                              id=self.dID,
                              body=shortMeta)
        self.dID += 1

    def index_dir(self):
        """
        Index all files from the corpus directory, sorted by their size
        in decreasing order. Such sorting helps prevent memory errors
        when indexing large corpora, as the default behavior is to load
        the whole file is into memory, and there is more free memory
        in the beginning of the process. If MemoryError occurs, the
        iterative JSON parser is used, which works much slower.
        """
        filenames = []
        for root, dirs, files in os.walk(self.corpus_dir):
            for fname in files:
                if (not ((self.settings['input_format'] == 'json'
                          and fname.lower().endswith('.json'))
                         or (self.settings['input_format'] == 'json-gzip'
                             and fname.lower().endswith('.json.gz')))):
                    continue
                fnameFull = os.path.join(root, fname)
                filenames.append((fnameFull, os.path.getsize(fnameFull)))
        if len(filenames) <= 0:
            print('There are no files in this corpus.')
            return
        for fname, fsize in sorted(filenames, key=lambda p: -p[1]):
            # print(fname, fsize)
            bulk(self.es, self.iterate_sentences(fname), chunk_size=200, request_timeout=60)
            self.index_doc(fname)
        self.index_words()

    def compile_translations(self):
        """
        Compile flask_babel translations in ../search/web_app.
        """
        pythonPath = ''
        for p in sys.path:
            if re.search('Python3[^/\\\\]*[/\\\\]?$', p) is not None:
                pythonPath = p
                break
        if len(pythonPath) <= 0:
            pyBabelPath = 'pybabel'
        else:
            pyBabelPath = os.path.join(pythonPath, 'Scripts', 'pybabel')
        try:
            subprocess.run([pyBabelPath, 'compile',  '-d', 'translations'], cwd='../search/web_app', check=True)
        except:
            print('Could not compile translations with ' + pyBabelPath + ' .')
        else:
            print('Interface translations compiled.')

    def load_corpus(self):
        """
        Drop the current database, if any, and load the entire corpus.
        """
        t1 = time.time()
        self.compile_translations()
        self.delete_indices()
        self.create_indices()
        self.index_dir()
        t2 = time.time()
        print('Corpus indexed in', t2-t1, 'seconds:',
              self.dID, 'documents,',
              self.sID, 'sentences,',
              self.totalNumWords, 'words,',
              sum(len(self.wordFreqs[i]) for i in range(len(self.languages))), 'word types (different words).')


if __name__ == '__main__':
    x = Indexator()
    x.load_corpus()

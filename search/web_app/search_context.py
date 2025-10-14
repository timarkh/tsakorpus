"""
Contains functions to prepare and store the search context,
i.e. the hits already found and retrieved for current query,
as well as user's interaction with them, e.g. which hits
have been switched off by the user.
The context is stored at server side rather than in a cookie
because it can be quite large and cookies have size limits.
This means that Tsakorpus API is not as RESTful as you might
have imagined.
"""
import copy
import re
from . import sentView, settings


class SearchContext:
    rxCSVMeta = re.compile('^\\[.*:.*\\]$')
    rxCSVMetaSplit = re.compile('^\\[(.*?) *: *(.*)\\]$')

    def __init__(self, curLocale=''):
        """
        Whenever someone clicks one of the Search buttons, a new
        SearchContext object is created and stored in sessionData.
        """
        self.translit = ''
        self.last_sent_num = -1
        self.page_data = {}
        self.sentence_data = {}
        self.processed_words = []  # List of word hits taken from sentences when looking for
                                   # word/lemma in multi-word search
        self.after_key = None      # ID of the last retrieved word/lemma bucket for pagination
        self.locale = settings.default_locale
        if len(curLocale) > 0:
            self.locale = curLocale

    def flush(self):
        """
        Remove the old data after a new query has been made.
        """
        self.last_sent_num = -1
        self.page_data = {}
        self.sentence_data = {}
        self.processed_words = []
        self.after_key = None

    def add_sent_data_for_session(self, sent, sentData):
        """
        Add information about one particular sentence to the
        sentData dictionary for storing in the session data
        dictionary.
        Modify sentData, do not return anything.
        """
        if len(sentData) <= 0:
            docID = -1
            if '_source' in sent:
                docID = sent['_source']['doc_id']
            sentData.update({'languages': {},
                             'doc_id': docID,
                             'times_expanded': 0,
                             'src_alignment_files': [],
                             'header_csv': ['']})
        langID = 0
        nextID = prevID = -1
        highlightedText = ''
        if '_source' in sent:
            if 'next_id' in sent['_source']:
                nextID = sent['_source']['next_id']
            if 'prev_id' in sent['_source']:
                prevID = sent['_source']['prev_id']
            if (len(sentData['header_csv']) <= 0
                    or (len(sentData['header_csv']) == 1 and len(sentData['header_csv'][0]) <= 0)):
                sentData['header_csv'] = sentView.process_sentence_header(sent['_source'],
                                                                          format='csv',
                                                                          curLocale=self.locale)
            if 'lang' in sent['_source']:
                langID = sent['_source']['lang']
                highlightedText = sentView.process_sentence_csv(sent,
                                                                lang=settings.languages[langID],
                                                                translit=self.translit,
                                                                curLocale=self.locale)
            lang = settings.languages[langID]
            langView = lang
            if 'transVar' in sent['_source']:
                langView += '_' + str(sent['_source']['transVar'])
            if langView not in sentData['languages']:
                sentData['languages'][langView] = {'id': sent['_id'],
                                                   'next_id': nextID,
                                                   'prev_id': prevID,
                                                   'source_next': [],
                                                   'source_prev': [],
                                                   'highlighted_text': highlightedText,
                                                   'source': sent['_source']}
            else:
                if ('next_id' not in sentData['languages'][langView]
                        or nextID == -1
                        or nextID > sentData['languages'][langView]['next_id']):
                    sentData['languages'][langView]['next_id'] = nextID
                if ('prev_id' not in sentData['languages'][langView]
                        or prevID < sentData['languages'][langView]['prev_id']):
                    sentData['languages'][langView]['prev_id'] = prevID
            if 'src_alignment' in sent['_source']:
                for alignment in sent['_source']['src_alignment']:
                    if alignment['src'] not in sentData['src_alignment_files']:
                        sentData['src_alignment_files'].append(alignment['src'])

    def add_sent_to_session(self, hits):
        """
        Store the ids of the currently viewed sentences in the
        session data dictionary, so that the user can later ask
        for expanded context.
        """
        if 'hits' not in hits or 'hits' not in hits['hits']:
            return
        curSentIDs = []
        self.last_sent_num = len(hits['hits']['hits'])
        for sent in hits['hits']['hits']:
            curSentID = {}
            self.add_sent_data_for_session(sent, curSentID)
            curSentIDs.append(curSentID)
        self.sentence_data = curSentIDs

    def get_page_data(self, hitsProcessed):
        """
        Extract all relevant information from the processed hits
        of one results page. Return a list of dictionaries, one dictionary
        per result sentence.
        """
        result = []
        if self.sentence_data is None or len(self.sentence_data) != len(hitsProcessed['contexts']):
            return [{}] * len(hitsProcessed['contexts'])
        for iHit in range(len(hitsProcessed['contexts'])):
            hit = hitsProcessed['contexts'][iHit]
            sentPageDataDict = {'toggled_off': False,
                                'highlighted_text_csv': [],
                                'header_csv': ['']}
            if not hit['toggled_on']:
                sentPageDataDict['toggled_off'] = True
            for lang in settings.languages:
                if lang not in self.sentence_data[iHit]['languages']:
                    sentPageDataDict['highlighted_text_csv'].append('')
                else:
                    sentPageDataDict['highlighted_text_csv'].append(
                        self.sentence_data[iHit]['languages'][lang]['highlighted_text'])
                    glossed = sentView.get_glossed_sentence(self.sentence_data[iHit]['languages'][lang]['source'],
                                                            lang=lang, glossOnly=True, curLocale=self.locale)
                    if settings.gloss_search_enabled and '{{' in self.sentence_data[iHit]['languages'][lang]['highlighted_text']:
                        sentPageDataDict['glossed'] = glossed
                if 'header_csv' in self.sentence_data[iHit]:
                    sentPageDataDict['header_csv'] = self.sentence_data[iHit]['header_csv']
            result.append(sentPageDataDict)
        return result

    def sync_page_data(self, page, hitsProcessed):
        """
        If the user is going to see this page for the first time,
        add relevant information to page_data. Otherwise, toggle on/off
        the sentences according to the previously saved page data.
        """
        if (self.page_data is not None and page in self.page_data
                and 'contexts' in hitsProcessed
                and len(hitsProcessed['contexts']) == len(self.page_data[page])):
            for iHit in range(len(hitsProcessed['contexts'])):
                if self.page_data[page][iHit]['toggled_off']:
                    hitsProcessed['contexts'][iHit]['toggled_on'] = False
                else:
                    hitsProcessed['contexts'][iHit]['toggled_on'] = True
        elif self.page_data is None:
            self.page_data = {}
        self.page_data[page] = self.get_page_data(hitsProcessed)

    def update_expanded_contexts(self, context, neighboringIDs):
        """
        Update the session data dictionary with the expanded
        context data.
        """
        if (self.sentence_data is None
                or 'n' not in context
                or context['n'] < 0
                or context['n'] >= len(self.sentence_data)):
            return
        curSent = self.sentence_data[context['n']]
        curSent['times_expanded'] += 1
        for lang in curSent['languages']:
            for side in ['next', 'prev']:
                if side in context['languages'][lang] and len(context['languages'][lang][side]) > 0:
                    curSent['languages'][lang][side + '_id'] = neighboringIDs[lang][side]
                    curSent['languages'][lang]['source_' + side].append(context['languages'][lang][side + '_source'])

    def get_expanded_context(self, n, lang):
        """
        Return a list with the sources of all sentences in current n_th expanded
        context, from left to right. If the context has not been expanded, this
        list will contain one item (the search hit).
        """
        if n < 0 or n >= len(self.sentence_data):
            return []
        curSent = self.sentence_data[n]
        if lang not in curSent['languages']:
            return []
        context = []
        curSentLang = curSent['languages'][lang]
        for iContextSent in range(len(curSentLang['source_prev']) - 1, -1, -1):
            context.append(copy.deepcopy(curSentLang['source_prev'][iContextSent]))
        context.append(curSentLang['source'])
        for iContextSent in range(len(curSentLang['source_next'])):
            context.append(copy.deepcopy(curSentLang['source_next'][iContextSent]))
        return context

    def prepare_results_for_download(self, page=-1, format='csv'):
        """
        Return a list of search results in a format easily transformable
        to CSV/XLSX. If page == -1, return all pages visited in the current session.
        If format == 'csv' (default), return a list of values that can be tab-joined
        later. If format == 'json', return a more well-structured dictionary.
        """
        result = []
        pages2download = self.page_data.keys()
        if page >= 0:
            pages2download = [page]
        for page in pages2download:
            for sent in self.page_data[page]:
                if not sent['toggled_off']:
                    curLine = sent['header_csv']
                    if format == 'json':
                        curLineJSON = {'doc_meta': {}, 'sent_meta': {}, 'tiers': [], 'glossed': ''}
                        for metaValue in curLine:
                            m = self.rxCSVMetaSplit.search(metaValue)
                            if m is None:
                                continue
                            curLineJSON['doc_meta'][m.group(1)] = m.group(2)
                        curLine = curLineJSON
                    for s in sent['highlighted_text_csv']:
                        for sPart in s.split('\t'):
                            if len(sPart) > 0:
                                if format == 'json':
                                    m = self.rxCSVMetaSplit.search(sPart)
                                    if m is not None:
                                        k, v = m.group(1), m.group(2)
                                        if k not in curLine['doc_meta'] and k not in curLine['sent_meta']:
                                            curLine['sent_meta'][k] = v
                                    else:
                                        curLine['tiers'].append(sPart)
                                else:
                                    if (self.rxCSVMeta.search(sPart) is None or sPart not in curLine):
                                        curLine.append(sPart)
                    if settings.gloss_search_enabled and 'glossed' in sent:
                        if format == 'json':
                            curLine['glossed'] = sent['glossed']
                        else:
                            curLine.append(sent['glossed'])
                    result.append(curLine)
        return result

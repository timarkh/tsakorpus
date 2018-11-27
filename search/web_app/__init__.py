from flask import Flask, request, after_this_request, render_template, session, jsonify, current_app, send_from_directory, make_response, config
from flask_babel import gettext
import json
import gzip
import functools
from functools import wraps, update_wrapper
import os
import copy
import random
import uuid
import math
import xlsxwriter
import time
from search_engine.client import SearchClient
from .response_processors import SentenceViewer
from .transliteration import *


SETTINGS_DIR = '../conf'
MAX_PAGE_SIZE = 100     # maximum number of sentences per page
f = open(os.path.join(SETTINGS_DIR, 'corpus.json'), 'r', encoding='utf-8')
settings = json.loads(f.read())
f.close()
corpus_name = settings['corpus_name']
if settings['max_docs_retrieve'] >= 10000:
    settings['max_docs_retrieve'] = 9999
localizations = {}
sc = SearchClient(SETTINGS_DIR, mode='test')
sentView = SentenceViewer(SETTINGS_DIR, sc)
sc.qp.rp = sentView
sc.qp.wr.rp = sentView
random.seed()
corpus_size = sc.get_n_words()  # size of the corpus in words
word_freq_by_rank = []
lemma_freq_by_rank = []
for lang in settings['languages']:
    # number of word types for each frequency rank
    word_freq_by_rank.append(sentView.extract_cumulative_freq_by_rank(sc.get_word_freq_by_rank(lang)))
    # number of lemmata for each frequency rank
    lemma_freq_by_rank.append(sentView.extract_cumulative_freq_by_rank(sc.get_lemma_freq_by_rank(lang)))
if 'line_plot_meta' in settings:
    linePlotMetafields = settings['line_plot_meta']
else:
    linePlotMetafields = ['year']   # metadata fields whose statistics can be displayed on a line plot


def jsonp(func):
    """
    Wrap JSONified output for JSONP requests.
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated_function


def gzipped(f):
    """
    Gzipper taken from https://gist.github.com/RedCraig/94e43cdfe447964812c3
    """
    @functools.wraps(f)
    def view_func(*args, **kwargs):
        @after_this_request
        def zipper(response):
            accept_encoding = request.headers.get('Accept-Encoding', '')
            if 'gzip' not in accept_encoding.lower():
                return response
            response.direct_passthrough = False
            if (response.status_code < 200 or
                    response.status_code >= 300 or
                    'Content-Encoding' in response.headers):
                return response
            response.data = gzip.compress(response.data)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'
            response.headers['Content-Length'] = len(response.data)
            return response
        return f(*args, **kwargs)
    return view_func


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        # response.headers['Last-Modified'] = http_date(datetime.now())
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)


app = Flask(__name__)
app.secret_key = 'kkj6hd)^js7#dFQ'
sessionData = {}    # session key -> dictionary with the data for current session
app.config.update(dict(
    LANGUAGES=settings['interface_languages'],
    BABEL_DEFAULT_LOCALE='en'
))


def lang_sorting_key(l):
    """
    Function for sorting language names in the output according
    to the general order provided by the settings.
    """
    if l in settings['languages']:
        return settings['languages'].index(l), -1, ''
    elif re.sub('_[0-9]+$', '', l) in settings['languages']:
        return (settings['languages'].index(re.sub('_[0-9]+$', '', l)),
                int(re.sub('^.*_', '', l)), '')
    else:
        return len(settings['languages']), 0, l

def initialize_session():
    """
    Generate a unique session ID and initialize a dictionary with
    parameters for the current session. Write it to the global
    sessionData dictionary.
    """
    global sessionData
    session['session_id'] = str(uuid.uuid4())
    sessionData[session['session_id']] = {'page_size': 10,
                                          'page': 1,
                                          'login': False,
                                          'locale': 'en',
                                          'sort': '',
                                          'distance_strict': False,
                                          'last_sent_num': -1,
                                          'last_query': {},
                                          'seed': random.randint(1, 1e6),
                                          'excluded_doc_ids': set(),
                                          'progress': 100}


def get_session_data(fieldName):
    """
    Get the value of the fieldName parameter for the current session.
    If the session has not yet been initialized, initialize it first.
    If the parameter is supported, but not in the session dictionary,
    initialize the parameter first.
    """
    global sessionData
    if 'session_id' not in session:
        initialize_session()
    if session['session_id'] not in sessionData:
        sessionData[session['session_id']] = {}
    if fieldName == 'login' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['login'] = False
    elif fieldName == 'locale' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['locale'] = 'en'
    elif fieldName == 'page_size' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['page_size'] = 10
    elif fieldName == 'last_sent_num' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['last_sent_num'] = -1
    elif fieldName == 'seed' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['seed'] = random.randint(1, 1e6)
    elif fieldName == 'excluded_doc_ids' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['excluded_doc_ids'] = set()
    elif fieldName == 'progress' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['progress'] = 0
    elif fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']][fieldName] = ''
    try:
        dictCurData = sessionData[session['session_id']]
        requestedValue = dictCurData[fieldName]
        return requestedValue
    except KeyError:
        return None


def set_session_data(fieldName, value):
    """
    Set the value of the fieldName parameter for the current session.
    If the session has not yet been initialized, initialize it first.
    """
    global sessionData
    if 'session_id' not in session:
        initialize_session()
    if session['session_id'] not in sessionData:
        sessionData[session['session_id']] = {}
    sessionData[session['session_id']][fieldName] = value


def in_session(fieldName):
    """
    Check if the fieldName parameter exists in the dictionary with
    parameters for the current session.
    """
    global sessionData
    if 'session_id' not in session:
        return False
    return fieldName in sessionData[session['session_id']]


def get_locale():
    return get_session_data('locale')


def change_display_options(query):
    """
    Remember the new display options provided in the query.
    """
    if 'page_size' in query:
        try:
            ps = int(query['page_size'])
            if ps > MAX_PAGE_SIZE:
                ps = MAX_PAGE_SIZE
            elif ps < 1:
                ps = 1
            set_session_data('page_size', ps)
        except:
            set_session_data('page_size', 10)
    if 'sort' in query:
        set_session_data('sort', query['sort'])
    if 'distance_strict' in query:
        set_session_data('distance_strict', True)
    else:
        set_session_data('distance_strict', False)
    if 'translit' in query:
        set_session_data('translit', query['translit'])
    else:
        set_session_data('translit', None)
    if ('random_seed' in query
            and re.search('^[1-9][0-9]*', query['random_seed']) is not None
            and 0 < int(query['random_seed']) < 1000000):
        set_session_data('seed', int(query['random_seed']))


def add_sent_data_for_session(sent, sentData):
    """
    Add information about one particluar sentence to the
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
                         'header_csv': ''})
    langID = 0
    nextID = prevID = -1
    highlightedText = ''
    if '_source' in sent:
        if 'next_id' in sent['_source']:
            nextID = sent['_source']['next_id']
        if 'prev_id' in sent['_source']:
            prevID = sent['_source']['prev_id']
        if len(sentData['header_csv']) <= 0:
            sentData['header_csv'] = sentView.process_sentence_header(sent['_source'], format='csv')
        if 'lang' in sent['_source']:
            langID = sent['_source']['lang']
            highlightedText = sentView.process_sentence_csv(sent, lang=settings['languages'][langID],
                                                            translit=get_session_data('translit'))
        lang = settings['languages'][langID]
        langView = lang
        if 'transVar' in sent['_source']:
            langView += '_' + str(sent['_source']['transVar'])
        if langView not in sentData['languages']:
            sentData['languages'][langView] = {'id': sent['_id'],
                                               'next_id': nextID,
                                               'prev_id': prevID,
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


def add_sent_to_session(hits):
    """
    Store the ids of the currently viewed sentences in the
    session data dictionary, so that the user can later ask
    for expanded context.
    """
    if 'hits' not in hits or 'hits' not in hits['hits']:
        return
    curSentIDs = []
    set_session_data('last_sent_num', len(hits['hits']['hits']) - 1)
    for sent in hits['hits']['hits']:
        curSentID = {}
        add_sent_data_for_session(sent, curSentID)
        curSentIDs.append(curSentID)
    set_session_data('sentence_data', curSentIDs)


def get_page_data(hitsProcessed):
    """
    Extract all relevant information from the processed hits
    of one results page. Return a list of dictionaries, one dictionary
    per result sentence.
    """
    result = []
    curSentData = get_session_data('sentence_data')
    if curSentData is None or len(curSentData) != len(hitsProcessed['contexts']):
        return [{}] * len(hitsProcessed['contexts'])
    for iHit in range(len(hitsProcessed['contexts'])):
        hit = hitsProcessed['contexts'][iHit]
        sentPageDataDict = {'toggled_off': False,
                            'highlighted_text_csv': [],
                            'header_csv': ''}
        if not hit['toggled_on']:
            sentPageDataDict['toggled_off'] = True
        for lang in settings['languages']:
            if lang not in curSentData[iHit]['languages']:
                sentPageDataDict['highlighted_text_csv'].append('')
            else:
                sentPageDataDict['highlighted_text_csv'].append(curSentData[iHit]['languages'][lang]['highlighted_text'])
            if 'header_csv' in curSentData[iHit]:
                sentPageDataDict['header_csv'] = curSentData[iHit]['header_csv']
        result.append(sentPageDataDict)
    return result


def sync_page_data(page, hitsProcessed):
    """
    If the user is going to see this page for the first time,
    add relevant information to page_data. Otherwise, toggle on/off
    the sentences according to the previously saved page data.
    """
    pageData = get_session_data('page_data')
    if (pageData is not None and page in pageData
            and 'contexts' in hitsProcessed
            and len(hitsProcessed['contexts']) == len(pageData[page])):
        for iHit in range(len(hitsProcessed['contexts'])):
            if pageData[page][iHit]['toggled_off']:
                hitsProcessed['contexts'][iHit]['toggled_on'] = False
            else:
                hitsProcessed['contexts'][iHit]['toggled_on'] = True
    elif pageData is None:
        pageData = {}
    curPageData = get_page_data(hitsProcessed)
    pageData[page] = curPageData


def update_expanded_contexts(context, neighboringIDs):
    """
    Update the session data dictionary with the expanded
    context data.
    """
    curSentIDs = get_session_data('sentence_data')
    if (curSentIDs is None
            or 'n' not in context
            or context['n'] < 0
            or context['n'] >= len(curSentIDs)):
        return
    curSent = curSentIDs[context['n']]
    curSent['times_expanded'] += 1
    for lang in curSent['languages']:
        for side in ['next', 'prev']:
            if side in context['languages'][lang] and len(context['languages'][lang][side]) > 0:
                curSent['languages'][lang][side + '_id'] = neighboringIDs[lang][side]


@app.route('/search')
def search_page():
    """
    Return HTML of the search page (the main page of the corpus).
    """
    allLangSearch = settings['all_language_search_enabled']
    if 'transliterations' in settings:
        transliterations = settings['transliterations']
    else:
        transliterations = None
    if 'input_methods' in settings:
        inputMethods = settings['input_methods']
    else:
        inputMethods = None
    if 'media_youtube' in settings and settings['media_youtube']:
        mediaYoutube = True
    else:
        mediaYoutube = False
    return render_template('index.html',
                           locale=get_locale(),
                           corpus_name=corpus_name,
                           languages=settings['languages'],
                           all_lang_search=allLangSearch,
                           transliterations=transliterations,
                           input_methods=inputMethods,
                           media=settings['media'],
                           youtube=mediaYoutube,
                           gloss_search_enabled=settings['gloss_search_enabled'],
                           debug=settings['debug'],
                           subcorpus_selection=settings['search_meta'],
                           max_request_time=settings['query_timeout'] + 1,
                           locales=settings['interface_languages'],
                           random_seed=get_session_data('seed'))


@app.route('/search_sent_query/<int:page>')
@app.route('/search_sent_query')
@jsonp
def search_sent_query(page=0):
    if not settings['debug']:
        return jsonify({})
    if request.args and page <= 0:
        query = copy_request_args()
        page = 1
        change_display_options(query)
        set_session_data('last_query', query)
    else:
        query = get_session_data('last_query')
    set_session_data('page', page)
    wordConstraints = sc.qp.wr.get_constraints(query)
    # wordConstraintsPrint = {str(k): v for k, v in wordConstraints.items()}

    if 'para_ids' not in query:
        query, paraIDs = para_ids(query)
        if paraIDs is not None:
            query['para_ids'] = list(paraIDs)

    if (len(wordConstraints) > 0
            and get_session_data('distance_strict')
            and 'sent_ids' not in query
            and distance_constraints_too_complex(wordConstraints)):
        esQuery = sc.qp.html2es(query,
                                searchOutput='sentences',
                                query_size=1,
                                distances=wordConstraints)
        hits = sc.get_sentences(esQuery)
        if ('hits' not in hits
                or 'total' not in hits['hits']
                or hits['hits']['total'] > settings['max_distance_filter']):
            esQuery = {}
        else:
            esQuery = sc.qp.html2es(query,
                                    searchOutput='sentences',
                                    distances=wordConstraints)
    else:
        esQuery = sc.qp.html2es(query,
                                searchOutput='sentences',
                                sortOrder=get_session_data('sort'),
                                randomSeed=get_session_data('seed'),
                                query_size=get_session_data('page_size'),
                                page=get_session_data('page'),
                                distances=wordConstraints)
    return jsonify(esQuery)


def find_parallel_for_one_sent(sSource):
    """
    Retrieve all sentences in other languages which are aligned
    with the given sentence. Return the search results in JSON.
    """
    sids = set()
    for pa in sSource['para_alignment']:
        sids |= set(pa['sent_ids'])
    sids = list(sid for sid in sorted(sids))
    query = {'query': {'ids': {'values': sids}}}
    paraSentHits = sc.get_sentences(query)
    if 'hits' in paraSentHits and 'hits' in paraSentHits['hits']:
        return paraSentHits['hits']['hits']
    return []


def get_parallel_for_one_sent_html(sSource, numHit):
    """
    Iterate over HTML strings with sentences in other languages
    aligned with the given sentence.
    """
    curSentIDs = get_session_data('sentence_data')
    for s in find_parallel_for_one_sent(sSource):
        numSent = get_session_data('last_sent_num') + 1
        set_session_data('last_sent_num', numSent)
        add_sent_data_for_session(s, curSentIDs[numHit])
        langID = s['_source']['lang']
        lang = settings['languages'][langID]
        langView = lang
        if 'transVar' in s['_source']:
            langView += '_' + str(s['_source']['transVar'])
        sentHTML = sentView.process_sentence(s, numSent=numSent, getHeader=False, lang=lang, langView=langView,
                                             translit=get_session_data('translit'))['languages'][langView]['text']
        yield sentHTML, langView


def add_parallel(hits, htmlResponse):
    """
    Add HTML of fragments in other languages aligned with the current
    search results to the response.
    """
    addLanguages = set()
    for iHit in range(len(hits)):
        if ('para_alignment' not in hits[iHit]['_source']
                or len(hits[iHit]['_source']['para_alignment']) <= 0):
            continue
        for sentHTML, lang in get_parallel_for_one_sent_html(hits[iHit]['_source'], iHit):
            try:
                htmlResponse['contexts'][iHit]['languages'][lang]['text'] += ' ' + sentHTML
            except KeyError:
                htmlResponse['contexts'][iHit]['languages'][lang] = {'text': sentHTML}
                # Add new language names that could appear if there are several
                # translation variants for the same language. In this case, they
                # are named LANG_V, where LANG is the language name and V is the number
                # of the version.
                if lang not in addLanguages:
                    addLanguages.add(lang)
    if len(addLanguages) > 0 and 'languages' in htmlResponse:
        addLanguages -= set(htmlResponse['languages'])
        htmlResponse['languages'] += [l for l in sorted(addLanguages)]


def get_buckets_for_doc_metafield(fieldName, langID=-1, docIDs=None, maxBuckets=300):
    """
    Group all documents into buckets, each corresponding to one
    of the unique values for the fieldName metafield. Consider
    only top maxBuckets field values (in terms of document count).
    If langID is provided, count only data for a particular language.
    Return a dictionary with the values and corresponding document
    count.
    """
    if fieldName not in settings['search_meta']['stat_options'] or langID >= len(settings['languages']) > 1:
        return {}
    innerQuery = {'match_all': {}}
    if docIDs is not None:
        innerQuery = {'ids': {'type': 'doc', 'values': list(docIDs)}}
    if not fieldName.startswith('year'):
        queryFieldName = fieldName + '_kw'
    else:
        queryFieldName = fieldName
    if len(settings['languages']) == 1 or langID < 0:
        nWordsFieldName = 'n_words'
        nSentsFieldName = 'n_sents'
    else:
        nWordsFieldName = 'n_words_' + settings['languages'][langID]
        nSentsFieldName = 'n_sents_' + settings['languages'][langID]
    esQuery = {'query': innerQuery,
               'size': 0,
               'aggs': {'metafield':
                            {'terms':
                                 {'field': queryFieldName, 'size': maxBuckets},
                             'aggs':
                                 {'subagg_n_words': {'sum': {'field': nWordsFieldName}},
                                  'subagg_n_sents': {'sum': {'field': nSentsFieldName}}}
                             }
                        }
               }
    hits = sc.get_docs(esQuery)
    if 'aggregations' not in hits or 'metafield' not in hits['aggregations']:
        return {}
    buckets = []
    for bucket in hits['aggregations']['metafield']['buckets']:
        bucketListItem = {'name': bucket['key'],
                          'n_docs': bucket['doc_count'],
                          'n_words': bucket['subagg_n_words']['value']}
        buckets.append(bucketListItem)
    if not fieldName.startswith(('year', 'byear', 'birth_year')):
        buckets.sort(key=lambda b: (-b['n_words'], -b['n_docs'], b['name']))
    else:
        buckets.sort(key=lambda b: b['name'])
    if len(buckets) > 25 and not fieldName.startswith('year'):
        bucketsFirst = buckets[:25]
        lastBucket = {'name': '>>', 'n_docs': 0, 'n_words': 0}
        for i in range(25, len(buckets)):
            lastBucket['n_docs'] += buckets[i]['n_docs']
            lastBucket['n_words'] += buckets[i]['n_words']
        bucketsFirst.append(lastBucket)
        buckets = bucketsFirst
    return buckets


def get_buckets_for_sent_metafield(fieldName, langID=-1, docIDs=None, maxBuckets=300):
    """
    Group all sentences into buckets, each corresponding to one
    of the unique values for the fieldName metafield. Consider
    only top maxBuckets field values (in terms of document count).
    If langID is provided, count only data for a particular language.
    Return a dictionary with the values and corresponding sentence/word
    count.
    """
    if fieldName not in settings['search_meta']['stat_options'] or langID >= len(settings['languages']) > 1:
        return {}
    if langID >= 0:
        innerQuery = {'match': {'lang': langID}}
    else:
        innerQuery = {'match_all': {}}
    if docIDs is not None:
        innerQuery = {'ids': {'type': 'doc', 'values': list(docIDs)}}
    # if not fieldName.startswith('year'):
    #     queryFieldName = fieldName + '_kw'
    # else:
    #     queryFieldName = fieldName
    if not fieldName.startswith('meta.'):
        queryFieldName = 'meta.' + fieldName
    else:
        queryFieldName = fieldName
    if not queryFieldName.startswith('meta.year'):
        queryFieldName += '_kw'
    esQuery = {'query': innerQuery,
               'size': 0,
               'aggs': {'metafield':
                            {'terms':
                                 {'field': queryFieldName, 'size': maxBuckets},
                             'aggs':
                                 {'subagg_n_words': {'sum': {'field': 'n_words'}}}
                             }
                        }
               }
    hits = sc.get_sentences(esQuery)
    if 'aggregations' not in hits or 'metafield' not in hits['aggregations']:
        return {}
    buckets = []
    for bucket in hits['aggregations']['metafield']['buckets']:
        bucketListItem = {'name': bucket['key'],
                          'n_sents': bucket['doc_count'],
                          'n_words': bucket['subagg_n_words']['value']}
        buckets.append(bucketListItem)
    if not fieldName.startswith(('year', 'byear', 'birth_year')):
        buckets.sort(key=lambda b: (-b['n_words'], -b['n_sents'], b['name']))
    else:
        buckets.sort(key=lambda b: b['name'])
    if len(buckets) > 25 and not fieldName.startswith('year'):
        bucketsFirst = buckets[:25]
        lastBucket = {'name': '>>', 'n_sents': 0, 'n_words': 0}
        for i in range(25, len(buckets)):
            lastBucket['n_sents'] += buckets[i]['n_sents']
            lastBucket['n_words'] += buckets[i]['n_words']
        bucketsFirst.append(lastBucket)
        buckets = bucketsFirst
    return buckets


@app.route('/doc_stats/<metaField>')
def get_doc_stats(metaField):
    """
    Return JSON with basic statistics concerning the distribution
    of corpus documents by values of one metafield. This function
    can be used to visualise (sub)corpus composition.
    """
    if metaField not in settings['search_meta']['stat_options']:
        return jsonify({})
    query = copy_request_args()
    change_display_options(query)
    docIDs = subcorpus_ids(query)
    buckets = get_buckets_for_doc_metafield(metaField, langID=-1, docIDs=docIDs)
    return jsonify(buckets)


@app.route('/word_freq_stats/<searchType>')
def get_word_freq_stats(searchType='word'):
    """
    Return JSON with the distribution of a particular kind of words
    or lemmata by frequency rank. This function is used for visualisation.
    Currently, it can only return statistics for a context-insensitive
    query for the whole corpus (the subcorpus constraints are
    discarded from the query). Return a list which contains results
    for each of the query words (the corresponding lines are plotted
    in different colors). Maximum number of simultaneously queried words
    is 10. All words should be in the same language; the language of the
    first word is used.
    """
    htmlQuery = copy_request_args()
    change_display_options(htmlQuery)
    langID = 0
    nWords = 1
    if 'n_words' in htmlQuery and int(htmlQuery['n_words']) > 1:
        nWords = int(htmlQuery['n_words'])
        if nWords > 10:
            nWords = 10
    if searchType not in ('word', 'lemma'):
        searchType = 'word'
    if 'lang1' in htmlQuery and htmlQuery['lang1'] in settings['languages']:
        langID = settings['languages'].index(htmlQuery['lang1'])
    else:
        return jsonify([])
    results = []
    for iWord in range(1, nWords + 1):
        htmlQuery['lang' + str(iWord)] = htmlQuery['lang1']
        partHtmlQuery = sc.qp.swap_query_words(1, iWord, copy.deepcopy(htmlQuery))
        esQuery = sc.qp.word_freqs_query(partHtmlQuery, searchType=searchType)
        # return jsonify(esQuery)
        if searchType == 'word':
            hits = sc.get_words(esQuery)
        else:
            hits = sc.get_lemmata(esQuery)
        # return jsonify(hits)
        curFreqByRank = sentView.extract_cumulative_freq_by_rank(hits)
        buckets = []
        prevFreq = 0
        if searchType == 'lemma':
            freq_by_rank = lemma_freq_by_rank
        else:
            freq_by_rank = word_freq_by_rank
        for freqRank in sorted(freq_by_rank[langID]):
            bucket = {'name': freqRank, 'n_words': 0}
            if freqRank in curFreqByRank:
                bucket['n_words'] = curFreqByRank[freqRank] / freq_by_rank[langID][freqRank]
                prevFreq = curFreqByRank[freqRank]
            else:
                bucket['n_words'] = prevFreq / freq_by_rank[langID][freqRank]
            buckets.append(bucket)
        results.append(buckets)
    return jsonify(results)


def wilson_confidence_interval(p, n, multiplier, z=1.645):
    """
    Calculate the Wilson confidence interval for Binomial
    distribution, given n trials with p success rate.
    """
    # z: 1.96 for 95%
    # 1.645 for 90%
    center = (p + z * z / (2 * n)) / (1 + z * z / (2 * n))
    halfLength = (z / (1 + z * z / n)) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (center - halfLength) * multiplier, (center + halfLength) * multiplier


def get_word_buckets(searchType, metaField, nWords, htmlQuery,
                     queryWordConstraints, langID, searchIndex):
    """
    Perform an actual DB search for a request about the distribution
    of a word/context over the values of a document-level or a
    sentence-level metafield. 
    """
    bSentenceLevel = (metaField in settings['sentence_meta'])
    if bSentenceLevel:
        queryFieldName = 'sent_meta_' + metaField + '_kw1'
    elif metaField not in linePlotMetafields:
        queryFieldName = metaField + '_kw'
    else:
        queryFieldName = metaField
    docIDs = subcorpus_ids(htmlQuery)

    if bSentenceLevel:
        buckets = get_buckets_for_sent_metafield(metaField, langID=langID, docIDs=docIDs)
    else:
        buckets = get_buckets_for_doc_metafield(metaField, langID=langID, docIDs=docIDs)
    results = []
    if searchType == 'context':
        nWordsProcess = 1
    else:
        nWordsProcess = nWords
    for iWord in range(1, nWordsProcess + 1):
        curWordBuckets = []
        for bucket in buckets:
            if (bucket['name'] == '>>'
                    or (type(bucket['name']) == str and len(bucket['name']) <= 0)):
                continue
            newBucket = copy.deepcopy(bucket)
            if searchType == 'context':
                curHtmlQuery = copy.deepcopy(htmlQuery)
            else:
                curHtmlQuery = sc.qp.swap_query_words(1, iWord, copy.deepcopy(htmlQuery))
                curHtmlQuery = sc.qp.remove_non_first_words(curHtmlQuery)
                curHtmlQuery['lang1'] = htmlQuery['lang1']
                curHtmlQuery['n_words'] = 1
            # if metaField not in curHtmlQuery or len(curHtmlQuery[metaField]) <= 0:
            curHtmlQuery[queryFieldName] = bucket['name']
            # elif type(curHtmlQuery[metaField]) == str:
            #     curHtmlQuery[metaField] += ',' + bucket['name']
            if not bSentenceLevel:
                curHtmlQuery['doc_ids'] = subcorpus_ids(curHtmlQuery)
            query = sc.qp.html2es(curHtmlQuery,
                                  searchOutput=searchIndex,
                                  sortOrder='',
                                  query_size=1,
                                  distances=queryWordConstraints)
            if searchIndex == 'words' and newBucket['n_words'] > 0:
                hits = sc.get_word_freqs(query)
                if ('aggregations' not in hits
                    or 'agg_freq' not in hits['aggregations']
                    or 'agg_ndocs' not in hits['aggregations']
                    or hits['aggregations']['agg_ndocs']['value'] is None
                    or (hits['aggregations']['agg_ndocs']['value'] <= 0
                        and not metaField.startswith('year'))):
                    continue
                successRate = hits['aggregations']['agg_freq']['value'] / newBucket['n_words']
                newBucket['n_words_conf_int'] = wilson_confidence_interval(successRate,
                                                                           newBucket['n_words'],
                                                                           1000000)
                newBucket['n_words'] = successRate * 1000000
                newBucket['n_sents'] = hits['aggregations']['agg_ndocs']['value'] / newBucket['n_docs'] * 100
            elif searchIndex == 'sentences' and newBucket['n_words'] > 0:
                hits = sc.get_sentences(query)
                if ('aggregations' not in hits
                    or 'agg_nwords' not in hits['aggregations']
                    or 'agg_ndocs' not in hits['aggregations']
                    or hits['aggregations']['agg_ndocs']['value'] is None
                    or hits['aggregations']['agg_nwords']['sum'] is None
                    or (hits['aggregations']['agg_ndocs']['value'] <= 0
                        and not metaField.startswith('year'))):
                    continue
                successRate = hits['aggregations']['agg_nwords']['sum'] / newBucket['n_words']
                newBucket['n_words_conf_int'] = wilson_confidence_interval(successRate,
                                                                           newBucket['n_words'],
                                                                           1000000)
                newBucket['n_words'] = successRate * 1000000
                if nWords > 1:
                    newBucket['n_sents'] = hits['hits']['total']
                if not bSentenceLevel:
                    newBucket['n_docs'] = hits['aggregations']['agg_ndocs']['value'] / newBucket['n_docs'] * 100
                else:
                    newBucket['n_sents'] = hits['hits']['total'] / newBucket['n_sents'] * 100
            curWordBuckets.append(newBucket)
        results.append(curWordBuckets)
    return results


@app.route('/word_stats/<searchType>/<metaField>')
def get_word_stats(searchType, metaField):
    """
    Return JSON with basic statistics concerning the distribution
    of a particular word form by values of one metafield. This function
    can be used to visualise word distributions across genres etc.
    If searchType == 'context', take into account the whole query.
    If searchType == 'compare', treat the query as several sepearate
    one-word queries. If, in this case, the data is to be displayed
    on a bar plot, process only the first word of the query.
    Otherwise, return a list which contains results for each
    of the query words (the corresponding lines are plotted
    in different colors). Maximum number of simultaneously queried words
    is 10. All words should be in the same language; the language of the
    first word is used.
    If the metaField is a document-level field, first split
    the documents into buckets according to its values and then search
    inside each bucket. If it is a sentence-level field, do a single
    search in the sentence index with bucketing.
    """
    if metaField not in settings['search_meta']['stat_options']:
        return jsonify([])
    if searchType not in ('compare', 'context'):
        return jsonify([])

    htmlQuery = copy_request_args()
    change_display_options(htmlQuery)
    langID = -1
    if 'lang1' in htmlQuery and htmlQuery['lang1'] in settings['languages']:
        langID = settings['languages'].index(htmlQuery['lang1'])
    nWords = 1
    if 'n_words' in htmlQuery and int(htmlQuery['n_words']) > 1:
        nWords = int(htmlQuery['n_words'])
        if searchType == 'compare':
            if nWords > 10:
                nWords = 10
            if metaField not in linePlotMetafields:
                nWords = 1

    searchIndex = 'words'
    queryWordConstraints = None
    if (searchType == 'context' and nWords > 1) or metaField in settings['sentence_meta']:
        searchIndex = 'sentences'
        wordConstraints = sc.qp.wr.get_constraints(htmlQuery)
        set_session_data('word_constraints', wordConstraints)
        if (len(wordConstraints) > 0
                and get_session_data('distance_strict')):
            queryWordConstraints = wordConstraints
    elif searchType == 'context' and 'sentence_index1' in htmlQuery and len(htmlQuery['sentence_index1']) > 0:
        searchIndex = 'sentences'

    results = get_word_buckets(searchType, metaField, nWords, htmlQuery,
                               queryWordConstraints, langID, searchIndex)
    return jsonify(results)


def subcorpus_ids(htmlQuery):
    """
    Return IDs of the documents specified by the subcorpus selection
    fields in htmlQuery.
    """
    subcorpusQuery = sc.qp.subcorpus_query(htmlQuery, sortOrder='',
                                           exclude=get_session_data('excluded_doc_ids'))
    if subcorpusQuery is None or ('query' in subcorpusQuery and subcorpusQuery['query'] == {'match_all': {}}):
        return None
    iterator = sc.get_all_docs(subcorpusQuery)
    docIDs = []
    for doc in iterator:
        docIDs.append(doc['_id'])
    return docIDs


def para_ids(htmlQuery):
    """
    If the query contains parts for several languages, find para_ids associated
    with the sentences in non-first languages that conform to the corresponding
    parts of the query.
    Return the query for the first language and para_ids conforming to the other
    parts of the query.
    """
    langQueryParts = sc.qp.split_query_into_languages(htmlQuery)
    if langQueryParts is None or len(langQueryParts) <= 1:
        return htmlQuery, None
    paraIDs = None
    for i in range(1, len(langQueryParts)):
        lpHtmlQuery = langQueryParts[i]
        paraIDQuery = sc.qp.para_id_query(lpHtmlQuery)
        if paraIDQuery is None:
            return None
        curParaIDs = set()
        iterator = sc.get_all_sentences(paraIDQuery)
        for dictParaID in iterator:
            if '_source' not in dictParaID or 'para_ids' not in dictParaID['_source']:
                continue
            for paraID in dictParaID['_source']['para_ids']:
                curParaIDs.add(paraID)
        if paraIDs is None:
            paraIDs = curParaIDs
        else:
            paraIDs &= curParaIDs
        if len(paraIDs) <= 0:
            return langQueryParts[0], list(paraIDs)
    return langQueryParts[0], list(paraIDs)


def copy_request_args():
    """
    Copy the reauest arguments from request.args to a
    normal modifiable dictionary. Return the dictionary.
    If input method is specified, change the values using
    the relevant transliteration function.
    """
    query = {}
    if request.args is None or len(request.args) <= 0:
        return query
    input_translit_func = lambda f, t, l: t
    if 'input_method' in request.args and len(request.args['input_method']) > 0:
        translitFuncName = 'input_method_' + request.args['input_method']
        localNames = globals()
        if translitFuncName in localNames:
            input_translit_func = localNames[translitFuncName]
    for field, value in request.args.items():
        if type(value) != list or len(value) > 1:
            query[field] = copy.deepcopy(value)
            if type(value) == str:
                mFieldNum = sc.qp.rxFieldNum.search(field)
                if mFieldNum is None:
                    continue
                if 'lang' + mFieldNum.group(2) not in request.args:
                    continue
                lang = request.args['lang' + mFieldNum.group(2)]
                query[field] = input_translit_func(mFieldNum.group(1), query[field], lang)
        else:
            query[field] = copy.deepcopy(value[0])
    if 'sent_ids' in query:
        del query['sent_ids']  # safety
    return query


def count_occurrences(query, distances=None):
    esQuery = sc.qp.html2es(query,
                            searchOutput='sentences',
                            sortOrder='no',
                            query_size=1,
                            distances=distances)
    hits = sc.get_sentences(esQuery)
    if ('aggregations' in hits
            and 'agg_nwords' in hits['aggregations']
            and hits['aggregations']['agg_nwords']['sum'] is not None):
        return int(math.floor(hits['aggregations']['agg_nwords']['sum']))
    return 0


def distance_constraints_too_complex(wordConstraints):
    """
    Decide if the constraints on the distances between pairs
    of search terms are too complex, i. e. if there is no single word
    that all pairs include. If the constraints are too complex
    and the "distance requirements are strict" flag is set,
    the query will find some invalid results, so further (slow)
    post-filtering is needed.
    """
    if wordConstraints is None or len(wordConstraints) <= 0:
        return False
    commonTerms = None
    for wordPair in wordConstraints:
        if commonTerms is None:
            commonTerms = set(wordPair)
        else:
            commonTerms &= set(wordPair)
        if len(commonTerms) <= 0:
            return True
    return False


def find_sentences_json(page=0):
    """
    Find sentences and change current options using the query in request.args.
    """
    if request.args and page <= 0:
        query = copy_request_args()
        page = 1
        change_display_options(query)
        if get_session_data('sort') not in ('random', 'freq'):
            set_session_data('sort', 'random')
        set_session_data('last_query', query)
        wordConstraints = sc.qp.wr.get_constraints(query)
        set_session_data('word_constraints', wordConstraints)
    else:
        query = get_session_data('last_query')
        wordConstraints = get_session_data('word_constraints')
    set_session_data('page', page)

    nWords = 1
    negWords = []
    if 'n_words' in query:
        nWords = int(query['n_words'])
        if nWords > 0:
            for iQueryWord in range(1, nWords + 1):
                if 'negq' + str(iQueryWord) in query and query['negq' + str(iQueryWord)] == 'on':
                    negWords.append(iQueryWord)

    docIDs = None
    if 'doc_ids' not in query and 'sent_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs

    if 'para_ids' not in query:
        query, paraIDs = para_ids(query)
        if paraIDs is not None:
            query['para_ids'] = paraIDs
            nWords = query['n_words']
            for iQueryWord in range(2, nWords + 1):
                if 'lang' + str(iQueryWord) in query and query['lang' + str(iQueryWord)] != query['lang1']:
                    # print(negWords)
                    negWords.append(iQueryWord)

    if (len(wordConstraints) > 0
            and get_session_data('distance_strict')
            and 'sent_ids' not in query
            and distance_constraints_too_complex(wordConstraints)):
        esQuery = sc.qp.html2es(query,
                                searchOutput='sentences',
                                query_size=1,
                                distances=wordConstraints)
        hits = sc.get_sentences(esQuery)
        if ('hits' not in hits
                or 'total' not in hits['hits']
                or hits['hits']['total'] > settings['max_distance_filter']):
            query = {}
        else:
            esQuery = sc.qp.html2es(query,
                                    searchOutput='sentences',
                                    distances=wordConstraints)
            if '_source' not in esQuery:
                esQuery['_source'] = {}
            # esQuery['_source']['excludes'] = ['words.ana', 'words.wf']
            esQuery['_source'] = ['words.next_word', 'words.wtype']
            # TODO: separate threshold for this?
            iterator = sc.get_all_sentences(esQuery)
            query['sent_ids'] = sc.qp.filter_sentences(iterator, wordConstraints, nWords=nWords)
            set_session_data('last_query', query)

    queryWordConstraints = None
    if (len(wordConstraints) > 0
            and get_session_data('distance_strict')):
        queryWordConstraints = wordConstraints

    nOccurrences = 0
    if (get_session_data('sort') in ('random', 'freq')
            and (nWords == 1
                 or len(wordConstraints) <= 0
                 or not distance_constraints_too_complex(wordConstraints))):
        nOccurrences = count_occurrences(query, distances=queryWordConstraints)

    esQuery = sc.qp.html2es(query,
                            searchOutput='sentences',
                            sortOrder=get_session_data('sort'),
                            randomSeed=get_session_data('seed'),
                            query_size=get_session_data('page_size'),
                            page=get_session_data('page'),
                            distances=queryWordConstraints)

    # return esQuery
    hits = sc.get_sentences(esQuery)
    if nWords > 1 and 'hits' in hits and 'hits' in hits['hits']:
        for hit in hits['hits']['hits']:
            sentView.filter_multi_word_highlight(hit, nWords=nWords, negWords=negWords)
    if 'aggregations' in hits and 'agg_nwords' in hits['aggregations']:
        if nOccurrences > 0:
            hits['aggregations']['agg_nwords']['sum'] = nOccurrences
            # hits['aggregations']['agg_nwords']['count'] = 0
        elif ('n_words' in query and query['n_words'] == 1
              and 'sum' in hits['aggregations']['agg_nwords']):
            # only count number of occurrences for one-word queries
            hits['aggregations']['agg_nwords']['sum'] = 0
    if (len(wordConstraints) > 0
            and (not get_session_data('distance_strict')
                 or distance_constraints_too_complex(wordConstraints))
            and 'hits' in hits and 'hits' in hits['hits']):
        for hit in hits['hits']['hits']:
            hit['toggled_on'] = sc.qp.wr.check_sentence(hit, wordConstraints, nWords=nWords)
    if docIDs is not None and len(docIDs) > 0:
        hits['subcorpus_enabled'] = True
    return hits


def remove_sensitive_data(hits):
    """
    Remove data that should not be shown to the user, i.e. the ids
    of the sentences (the user can use this information to download 
    the whole corpus if the sentences are numbered consecutively,
    which is actually not the case, but still).
    Change the hits dictionary, do not return anything.
    """
    if type(hits) != dict or 'hits' not in hits or 'hits' not in hits['hits']:
        return
    for hit in hits['hits']['hits']:
        if '_id' in hit:
            del hit['_id']
        if '_source' in hit:
            if 'prev_id' in hit['_source']:
                del hit['_source']['prev_id']
            if 'next_id' in hit['_source']:
                del hit['_source']['next_id']


@app.route('/search_sent_json/<int:page>')
@app.route('/search_sent_json')
@jsonp
def search_sent_json(page=-1):
    if page < 0:
        set_session_data('page_data', {})
        page = 0
    hits = find_sentences_json(page=page)
    remove_sensitive_data(hits)
    return jsonify(hits)


@app.route('/search_sent/<int:page>')
@app.route('/search_sent')
@gzipped
def search_sent(page=-1):
    if page < 0:
        set_session_data('page_data', {})
        page = 0
    # try:
    hits = find_sentences_json(page=page)
    # except:
    #     return render_template('result_sentences.html', message='Request timeout.')
    add_sent_to_session(hits)
    hitsProcessed = sentView.process_sent_json(hits,
                                               translit=get_session_data('translit'))
    # hitsProcessed['languages'] = settings['languages']
    if len(settings['languages']) > 1 and 'hits' in hits and 'hits' in hits['hits']:
        add_parallel(hits['hits']['hits'], hitsProcessed)
    hitsProcessed['languages'].sort(key=lang_sorting_key)
    hitsProcessed['page'] = get_session_data('page')
    hitsProcessed['page_size'] = get_session_data('page_size')
    hitsProcessed['media'] = settings['media']
    hitsProcessed['subcorpus_enabled'] = False
    if 'subcorpus_enabled' in hits:
        hitsProcessed['subcorpus_enabled'] = True
    sync_page_data(hitsProcessed['page'], hitsProcessed)

    return render_template('result_sentences.html', data=hitsProcessed)


@app.route('/get_sent_context/<int:n>')
@jsonp
def get_sent_context(n):
    """
    Retrieve the neighboring sentences for the currently
    viewed sentence number n. Take into account how many
    times this particular context has been expanded and
    whether expanding it further is allowed.
    """
    if n < 0:
        return jsonify({})
    sentData = get_session_data('sentence_data')
    # return jsonify({"l": len(sentData), "i": sentData[n]})
    if sentData is None or n >= len(sentData) or 'languages' not in sentData[n]:
        return jsonify({})
    curSentData = sentData[n]
    if curSentData['times_expanded'] >= settings['max_context_expand'] >= 0:
        return jsonify({})
    context = {'n': n, 'languages': {lang: {} for lang in curSentData['languages']},
               'src_alignment': {}}
    neighboringIDs = {lang: {'next': -1, 'prev': -1} for lang in curSentData['languages']}
    for lang in curSentData['languages']:
        try:
            langID = settings['languages'].index(lang)
        except:
            # Language + number of the translation version: chop off the number
            langID = settings['languages'].index(re.sub('_[0-9]+$', '', lang))
        for side in ['next', 'prev']:
            curCxLang = context['languages'][lang]
            if side + '_id' in curSentData['languages'][lang]:
                curCxLang[side] = sc.get_sentence_by_id(curSentData['languages'][lang][side + '_id'])
            if (side in curCxLang
                    and len(curCxLang[side]) > 0
                    and 'hits' in curCxLang[side]
                    and 'hits' in curCxLang[side]['hits']
                    and len(curCxLang[side]['hits']['hits']) > 0):
                lastSentNum = get_session_data('last_sent_num') + 1
                curSent = curCxLang[side]['hits']['hits'][0]
                if '_source' in curSent and 'lang' not in curSent['_source']:
                    curCxLang[side] = ''
                    continue
                langReal = lang
                # lang is an identifier of the tier for parallel corpora, i.e.
                # the language of the original unexpanded sentence.
                # langReal is the real language of the expanded context.
                if '_source' in curSent and curSent['_source']['lang'] != langID:
                    langReal = settings['languages'][curSent['_source']['lang']]
                if '_source' in curSent and side + '_id' in curSent['_source']:
                    neighboringIDs[lang][side] = curSent['_source'][side + '_id']
                expandedContext = sentView.process_sentence(curSent,
                                                            numSent=lastSentNum,
                                                            getHeader=False,
                                                            lang=langReal,
                                                            translit=get_session_data('translit'))
                curCxLang[side] = expandedContext['languages'][langReal]['text']
                if settings['media']:
                    sentView.relativize_src_alignment(expandedContext, curSentData['src_alignment_files'])
                    context['src_alignment'].update(expandedContext['src_alignment'])
                set_session_data('last_sent_num', lastSentNum)
            else:
                curCxLang[side] = ''
    update_expanded_contexts(context, neighboringIDs)
    return jsonify(context)


@app.route('/search_lemma_query')
@jsonp
def search_lemma_query():
    return search_word_query(searchType='lemma')


@app.route('/search_word_query')
@jsonp
def search_word_query(searchType='word'):
    if not settings['debug']:
        return jsonify({})
    query = copy_request_args()
    change_display_options(query)
    if 'doc_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs
    else:
        docIDs = query['doc_ids']

    searchIndex = 'words'
    sortOrder = get_session_data('sort')
    queryWordConstraints = None
    nWords = 1
    if 'n_words' in query and int(query['n_words']) > 1:
        nWords = int(query['n_words'])
        searchIndex = 'sentences'
        sortOrder = 'random'  # in this case, the words are sorted after the search
        wordConstraints = sc.qp.wr.get_constraints(query)
        set_session_data('word_constraints', wordConstraints)
        if (len(wordConstraints) > 0
            and get_session_data('distance_strict')):
            queryWordConstraints = wordConstraints

    query = sc.qp.html2es(query,
                          searchOutput='words',
                          sortOrder=sortOrder,
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          distances=queryWordConstraints)
    if searchType == 'lemma':
        sc.qp.lemmatize_word_query(query)
    return jsonify(query)


@app.route('/search_lemma_json')
@jsonp
def search_lemma_json():
    return search_word_json(searchType='lemma')


@app.route('/search_word_json')
@jsonp
def search_word_json(searchType='word'):
    query = copy_request_args()
    change_display_options(query)
    if 'doc_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs
    else:
        docIDs = query['doc_ids']

    searchIndex = 'words'
    sortOrder = get_session_data('sort')
    queryWordConstraints = None
    nWords = 1
    if 'n_words' in query and int(query['n_words']) > 1:
        nWords = int(query['n_words'])
        searchIndex = 'sentences'
        sortOrder = 'random'  # in this case, the words are sorted after the search
        wordConstraints = sc.qp.wr.get_constraints(query)
        set_session_data('word_constraints', wordConstraints)
        if (len(wordConstraints) > 0
                and get_session_data('distance_strict')):
            queryWordConstraints = wordConstraints
    elif 'sentence_index1' in query and len(query['sentence_index1']) > 0:
        searchIndex = 'sentences'
        sortOrder = 'random'

    query = sc.qp.html2es(query,
                          searchOutput='words',
                          sortOrder=sortOrder,
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          distances=queryWordConstraints)

    hits = []
    if searchIndex == 'words':
        if docIDs is None:
            if searchType == 'lemma':
                sc.qp.lemmatize_word_query(query)
                hits = sc.get_lemmata(query)
            else:
                hits = sc.get_words(query)
        else:
            hits = sc.get_word_freqs(query)
    elif searchIndex == 'sentences':
        iSent = 0
        for hit in sc.get_all_sentences(query):
            if iSent >= 5:
                break
            iSent += 1
            hits.append(hit)

    return jsonify(hits)


@app.route('/search_lemma')
def search_lemma():
    return search_word(searchType='lemma')


@app.route('/search_word')
def search_word(searchType='word'):
    set_session_data('progress', 0)
    query = copy_request_args()
    change_display_options(query)
    if 'doc_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs
    else:
        docIDs = query['doc_ids']

    searchIndex = 'words'
    sortOrder = get_session_data('sort')
    wordConstraints = None
    queryWordConstraints = None
    constraintsTooComplex = False
    nWords = 1
    if 'n_words' in query and int(query['n_words']) > 1:
        nWords = int(query['n_words'])
        searchIndex = 'sentences'
        sortOrder = 'random'    # in this case, the words are sorted after the search
        wordConstraints = sc.qp.wr.get_constraints(query)
        set_session_data('word_constraints', wordConstraints)
        if (len(wordConstraints) > 0
                and get_session_data('distance_strict')):
            queryWordConstraints = wordConstraints
            if distance_constraints_too_complex(wordConstraints):
                constraintsTooComplex = True
    elif 'sentence_index1' in query and len(query['sentence_index1']) > 0:
        searchIndex = 'sentences'
        sortOrder = 'random'

    query = sc.qp.html2es(query,
                          searchOutput='words',
                          sortOrder=sortOrder,
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          distances=queryWordConstraints,
                          includeNextWordField=constraintsTooComplex)

    maxRunTime = time.time() + settings['query_timeout']
    hitsProcessed = {}
    if searchIndex == 'words':
        if docIDs is None:
            if searchType == 'lemma':
                sc.qp.lemmatize_word_query(query)
                hits = sc.get_lemmata(query)
            else:
                hits = sc.get_words(query)
            hitsProcessed = sentView.process_word_json(hits, docIDs,
                                                       searchType=searchType,
                                                       translit=get_session_data('translit'))
        else:
            hits = sc.get_word_freqs(query)
            hitsProcessed = sentView.process_word_subcorpus_json(hits, docIDs,
                                                                 translit=get_session_data('translit'))

    elif searchIndex == 'sentences':
        hitsProcessed = {'n_occurrences': 0, 'n_sentences': 0, 'n_docs': 0,
                         'total_freq': 0,
                         'words': [], 'doc_ids': set(), 'word_ids': {}}
        for hit in sc.get_all_sentences(query):
            if constraintsTooComplex:
                if not sc.qp.wr.check_sentence(hit, wordConstraints, nWords=nWords):
                    continue
            sentView.add_word_from_sentence(hitsProcessed, hit, nWords=nWords)
            if hitsProcessed['total_freq'] >= 2000 and time.time() > maxRunTime:
                hitsProcessed['timeout'] = True
                break
        hitsProcessed['n_docs'] = len(hitsProcessed['doc_ids'])
        if hitsProcessed['n_docs'] > 0:
            sentView.process_words_collected_from_sentences(hitsProcessed,
                                                            sortOrder=get_session_data('sort'),
                                                            pageSize=get_session_data('page_size'))

    hitsProcessed['media'] = settings['media']
    set_session_data('progress', 100)
    otherWordTableFields = []
    if 'word_table_fields' in settings and searchType == 'word':
        otherWordTableFields = settings['word_table_fields']
    displayFreqRank = True
    if 'display_freq_rank' in settings and not settings['display_freq_rank']:
        displayFreqRank = False
    return render_template('result_words.html', data=hitsProcessed,
                           word_table_fields=otherWordTableFields,
                           display_freq_rank=displayFreqRank)


@app.route('/search_doc_query')
@jsonp
def search_doc_query():
    if not settings['debug']:
        return jsonify({})
    query = copy_request_args()
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=settings['max_docs_retrieve'])
    return jsonify(query)


@app.route('/search_doc_json')
@jsonp
def search_doc_json():
    query = copy_request_args()
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=settings['max_docs_retrieve'])
    hits = sc.get_docs(query)
    return jsonify(hits)


@app.route('/search_doc')
@jsonp
def search_doc():
    query = copy_request_args()
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=settings['max_docs_retrieve'])
    hits = sc.get_docs(query)
    hitsProcessed = sentView.process_docs_json(hits,
                                               exclude=get_session_data('excluded_doc_ids'),
                                               corpusSize=corpus_size)
    hitsProcessed['media'] = settings['media']
    return render_template('result_docs.html', data=hitsProcessed)


@app.route('/get_word_fields')
def get_word_fields():
    """
    Return HTML with form inputs representing all additional
    word-level annotation fields.
    """
    result = ''
    wordFields = None
    sentMeta = None
    intMetaFields = None
    if 'word_fields' in settings and len(settings['word_fields']) > 0:
        wordFields = settings['word_fields']
    if 'sentence_meta' in settings and len(settings['sentence_meta']) > 0:
        sentMeta = settings['sentence_meta']
    if 'integer_meta_fields' in settings and len(settings['integer_meta_fields']) > 0:
        intMetaFields = settings['integer_meta_fields']
    result += render_template('common_additional_search_fields.html',
                              word_fields=wordFields,
                              sentence_meta=sentMeta,
                              int_meta_fields=intMetaFields,
                              ambiguous_analyses=settings['ambiguous_analyses'])
    return result


@app.route('/media/<path:path>')
def send_media(path):
    """
    Return the requested media file.
    """
    return send_from_directory(os.path.join('../media', corpus_name), path)


def prepare_results_for_download(pageData):
    """
    Return a list of search results in a format easily transformable
    to CSV/XLSX.
    """
    result = []
    for page in pageData:
        for sent in pageData[page]:
            if not sent['toggled_off']:
                result.append([sent['header_csv']] + sent['highlighted_text_csv'])
    return result


@app.route('/download_cur_results_csv')
@nocache
def download_cur_results_csv():
    """
    Write all sentences the user has already seen, except the
    toggled off ones, to a CSV file. Return the contents of the file. 
    """
    pageData = get_session_data('page_data')
    if pageData is None or len(pageData) <= 0:
        return ''
    result = prepare_results_for_download(pageData)
    return '\n'.join(['\t'.join(s) for s in result if len(s) > 0])


@app.route('/download_cur_results_xlsx')
@nocache
def download_cur_results_xlsx():
    """
    Write all sentences the user has already seen, except the
    toggled off ones, to an XSLX file. Return the file. 
    """
    pageData = get_session_data('page_data')
    if pageData is None or len(pageData) <= 0:
        return ''
    results = prepare_results_for_download(pageData)
    XLSXFilename = 'results-' + str(uuid.uuid4()) + '.xlsx'
    workbook = xlsxwriter.Workbook('tmp/' + XLSXFilename)
    worksheet = workbook.add_worksheet('Search results')
    for i in range(len(results)):
        for j in range(len(results[i])):
            worksheet.write(i, j, results[i][j])
    workbook.close()
    return send_from_directory('../tmp', XLSXFilename)


@app.route('/toggle_sentence/<int:sentNum>')
def toggle_sentence(sentNum):
    """
    Togle currently viewed sentence with the given number on or off.
    The sentences that have been switched off are not written to the
    CSV/XLSX when the user wants to download the search results.
    """
    pageData = get_session_data('page_data')
    page = get_session_data('page')
    if page is None or page == '':
        page = 0
    if pageData is None or page is None or page not in pageData:
        return json.dumps(pageData)
    if sentNum < 0 or sentNum >= len(pageData[page]):
        return ''
    pageData[page][sentNum]['toggled_off'] = not pageData[page][sentNum]['toggled_off']
    return ''


@app.route('/toggle_doc/<int:docID>')
def toggle_document(docID):
    """
    Togle given docID on or off. The documents that have been switched off
    are not included in the search.
    """
    excludedDocIDs = get_session_data('excluded_doc_ids')
    nWords = sc.get_n_words_in_document(docId=docID)
    sizePercent = round(nWords * 100 / corpus_size, 3)
    if docID in excludedDocIDs:
        excludedDocIDs.remove(docID)
        nDocs = 1
    else:
        excludedDocIDs.add(docID)
        nWords = -1 * nWords
        sizePercent = -1 * sizePercent
        nDocs = -1
    return jsonify({'n_words': nWords, 'n_docs': nDocs, 'size_percent': sizePercent})


@app.route('/clear_subcorpus')
def clear_subcorpus():
    """
    Flush the list of excluded document IDs.
    """
    set_session_data('excluded_doc_ids', set())
    return ''


@app.route('/get_gramm_selector/<lang>')
def get_gramm_selector(lang=''):
    """
    Return HTML of the grammatical tags selection dialogue for the given language.
    """
    if lang not in settings['lang_props'] or 'gramm_selection' not in settings['lang_props'][lang]:
        return ''
    grammSelection = settings['lang_props'][lang]['gramm_selection']
    return render_template('select_gramm.html', gramm=grammSelection)


@app.route('/get_gloss_selector/<lang>')
def get_gloss_selector(lang=''):
    """
    Return HTML of the gloss selection dialogue for the given language.
    """
    if lang not in settings['lang_props'] or 'gloss_selection' not in settings['lang_props'][lang]:
        return ''
    glossSelection = settings['lang_props'][lang]['gloss_selection']
    return render_template('select_gloss.html', glosses=glossSelection)


@app.route('/get_glossed_sentence/<int:n>')
def get_glossed_sentence(n):
    """
    Return a tab-delimited glossed sentence ready for insertion into
    a linguistic paper.
    """
    if n < 0:
        return ''
    sentData = get_session_data('sentence_data')
    if sentData is None or n >= len(sentData) or 'languages' not in sentData[n]:
        return ''
    curSentData = sentData[n]
    for langView in curSentData['languages']:
        lang = langView
        try:
            langID = settings['languages'].index(langView)
        except:
            # Language + number of the translation version: chop off the number
            langID = settings['languages'].index(re.sub('_[0-9]+$', '', langView))
            lang = settings['languages'][langID]
        if langID != 0:
            continue  # for now
        result = sentView.get_glossed_sentence(curSentData['languages'][langView]['source'], lang=lang)
        if type(result) == str:
            return result
        return ''
    return ''


@app.route('/set_locale/<lang>')
def set_locale(lang=''):
    if lang not in settings['interface_languages']:
        return
    set_session_data('locale', lang)
    return ''


@app.route('/help_dialogue')
def help_dialogue():
    l = get_locale()
    return render_template('help_dialogue_' + l + '.html',
                           media=settings['media'],
                           gloss_search_enabled=settings['gloss_search_enabled'])

from flask import Flask, request, after_this_request, render_template, session, jsonify, current_app, send_from_directory
import json
import gzip
import functools
from functools import wraps
import os
import copy
import random
import uuid
import math
import xlsxwriter
from search_engine.client import SearchClient
from .response_processors import SentenceViewer


SETTINGS_DIR = '../conf'
MAX_PAGE_SIZE = 100
f = open(os.path.join(SETTINGS_DIR, 'corpus.json'), 'r', encoding='utf-8')
settings = json.loads(f.read())
f.close()
f = open(os.path.join(SETTINGS_DIR, 'word_fields.json'), 'r', encoding='utf-8')
wordFields = json.loads(f.read())
f.close()
corpus_name = settings['corpus_name']
localizations = {}
supportedLocales = ['ru', 'en']
sc = SearchClient(SETTINGS_DIR, mode='test')
sentView = SentenceViewer(SETTINGS_DIR, sc)
random.seed()


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


app = Flask(__name__)
app.secret_key = 'kkj6hd)^js7#dFQ'
sessionData = {}    # session key -> dictionary with the data for current session


def initialize_session():
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
                                          'seed': random.randint(1, 1e6)}


def get_session_data(fieldName):
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
    elif fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']][fieldName] = ''
    try:
        dictCurData = sessionData[session['session_id']]
        requestedValue = dictCurData[fieldName]
        return requestedValue
    except KeyError:
        return None


def set_session_data(fieldName, value):
    global sessionData
    if 'session_id' not in session:
        initialize_session()
    if session['session_id'] not in sessionData:
        sessionData[session['session_id']] = {}
    sessionData[session['session_id']][fieldName] = value


def in_session(fieldName):
    global sessionData
    if 'session_id' not in session:
        return False
    return fieldName in sessionData[session['session_id']]


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
            pass
    if 'sort' in query:
        set_session_data('sort', query['sort'])
    if 'distance_strict' in query:
        set_session_data('distance_strict', True)
    else:
        set_session_data('distance_strict', False)


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
                         'src_alignment_files': []})
    langID = 0
    nextID = prevID = -1
    highlightedText = ''
    if '_source' in sent:
        if 'next_id' in sent['_source']:
            nextID = sent['_source']['next_id']
        if 'prev_id' in sent['_source']:
            prevID = sent['_source']['prev_id']
        if 'lang' in sent['_source']:
            langID = sent['_source']['lang']
            highlightedText = sentView.process_sentence_csv(sent, lang=settings['languages'][langID])
        lang = settings['languages'][langID]
        if lang not in sentData['languages']:
            sentData['languages'][lang] = {'id': sent['_id'],
                                           'next_id': nextID,
                                           'prev_id': prevID,
                                           'highlighted_text': highlightedText}
        else:
            if ('next_id' not in sentData['languages'][lang]
                    or nextID == -1
                    or nextID > sentData['languages'][lang]['next_id']):
                sentData['languages'][lang]['next_id'] = nextID
            if ('prev_id' not in sentData['languages'][lang]
                    or prevID < sentData['languages'][lang]['prev_id']):
                sentData['languages'][lang]['prev_id'] = prevID
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
    allLangSearch = settings['all_language_search_enabled']
    return render_template('index.html',
                           corpus_name=corpus_name,
                           languages=settings['languages'],
                           all_lang_search=allLangSearch,
                           media=settings['media'])


@app.route('/search_sent_query/<int:page>')
@app.route('/search_sent_query')
@jsonp
def search_sent_query(page=0):
    if request.args and page <= 0:
        query = copy_request_args()
        page = 1
        change_display_options(query)
        set_session_data('last_query', query)
    else:
        query = get_session_data('last_query')
    set_session_data('page', page)
    wordConstraints = sc.qp.wr.get_constraints(query)
    wordConstraints = {str(k): v for k, v in wordConstraints.items()}
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          page=get_session_data('page'))
    return jsonify([query, wordConstraints])


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
        sentHTML = sentView.process_sentence(s, numSent=numSent, getHeader=False, lang=lang)['languages'][lang]['text']
        yield sentHTML, lang


def add_parallel(hits, htmlResponse):
    """
    Add HTML of fragments in other languages aligned with the current
    search results to the response.
    """
    for iHit in range(len(hits)):
        if ('para_alignment' not in hits[iHit]['_source']
                or len(hits[iHit]['_source']['para_alignment']) <= 0):
            continue
        for sentHTML, lang in get_parallel_for_one_sent_html(hits[iHit]['_source'], iHit):
            try:
                htmlResponse['contexts'][iHit]['languages'][lang]['text'] += ' ' + sentHTML
            except KeyError:
                htmlResponse['contexts'][iHit]['languages'][lang] = {'text': sentHTML}


def subcorpus_ids(htmlQuery):
    """
    Return IDs of the documents specified by the subcorpus selection
    fields in htmlQuery.
    """
    subcorpusQuery = sc.qp.subcorpus_query(htmlQuery, sortOrder='')
    if subcorpusQuery is None:
        return None
    iterator = sc.get_all_docs(subcorpusQuery)
    docIDs = []
    for doc in iterator:
        docIDs.append(doc['_id'])
    return docIDs


def copy_request_args():
    query = {}
    if request.args is None or len(request.args) <= 0:
        return query
    for field, value in request.args.items():
        if type(value) != list or len(value) > 1:
            query[field] = copy.deepcopy(value)
        else:
            query[field] = copy.deepcopy(value[0])
    if 'sent_ids' in query:
        del query['sent_ids']  # safety
    return query


def count_occurrences(query):
    esQuery = sc.qp.html2es(query,
                            searchIndex='sentences',
                            sortOrder='no',
                            query_size=1)
    hits = sc.get_sentences(esQuery)
    if ('aggregations' in hits
            and 'agg_nwords' in hits['aggregations']
            and hits['aggregations']['agg_nwords']['sum'] is not None):
        return int(math.floor(hits['aggregations']['agg_nwords']['sum']))
    return 0


def find_sentences_json(page=0):
    """
    Find sentences and change current options using the query in request.args.
    """
    if request.args and page <= 0:
        query = copy_request_args()
        page = 1
        change_display_options(query)
        set_session_data('last_query', query)
        wordConstraints = sc.qp.wr.get_constraints(query)
        set_session_data('word_constraints', wordConstraints)
    else:
        query = get_session_data('last_query')
        wordConstraints = get_session_data('word_constraints')
    set_session_data('page', page)

    if 'doc_ids' not in query and 'sent_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs

    if (len(wordConstraints) > 0
            and get_session_data('distance_strict')
            and 'sent_ids' not in query):
        esQuery = sc.qp.html2es(query,
                                searchIndex='sentences',
                                query_size=1)
        hits = sc.get_sentences(esQuery)
        if ('hits' not in hits
                or 'total' not in hits['hits']
                or hits['hits']['total'] > settings['max_distance_filter']):
            query = {}
        else:
            esQuery = sc.qp.html2es(query,
                                    searchIndex='sentences')
            iterator = sc.get_all_sentences(esQuery)
            query['sent_ids'] = sc.qp.filter_sentences(iterator, wordConstraints)
            set_session_data('last_query', query)
    nOccurrences = 0
    if (get_session_data('sort') == 'random'
            and 'n_words' in query
            and query['n_words'] == '1'):
        nOccurrences = count_occurrences(query)
    esQuery = sc.qp.html2es(query,
                            searchIndex='sentences',
                            sortOrder=get_session_data('sort'),
                            randomSeed=get_session_data('seed'),
                            query_size=get_session_data('page_size'),
                            page=get_session_data('page'))
    hits = sc.get_sentences(esQuery)
    if 'aggregations' in hits and 'agg_nwords' in hits['aggregations']:
        if nOccurrences > 0:
            hits['aggregations']['agg_nwords']['sum'] = nOccurrences
            # hits['aggregations']['agg_nwords']['count'] = 0
        elif ('n_words' in query and query['n_words'] == 1
              and 'sum' in hits['aggregations']['agg_nwords']):
            # only count number of occurrences for one-word queries
            hits['aggregations']['agg_nwords']['sum'] = 0
    if (len(wordConstraints) > 0
            and not get_session_data('distance_strict')
            and 'hits' in hits and 'hits' in hits['hits']):
        for hit in hits['hits']['hits']:
            hit['relations_satisfied'] = sc.qp.wr.check_sentence(hit, wordConstraints)
    return hits


@app.route('/search_sent_json/<int:page>')
@app.route('/search_sent_json')
@jsonp
def search_sent_json(page=0):
    hits = find_sentences_json(page=page)
    return jsonify(hits)


@app.route('/search_sent/<int:page>')
@app.route('/search_sent')
@gzipped
def search_sent(page=0):
    hits = find_sentences_json(page=page)
    add_sent_to_session(hits)
    hitsProcessed = sentView.process_sent_json(hits)
    if len(settings['languages']) > 1 and 'hits' in hits and 'hits' in hits['hits']:
        add_parallel(hits['hits']['hits'], hitsProcessed)
    hitsProcessed['page'] = get_session_data('page')
    hitsProcessed['page_size'] = get_session_data('page_size')
    hitsProcessed['languages'] = settings['languages']
    hitsProcessed['media'] = settings['media']

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
    if curSentData['times_expanded'] >= settings['max_context_expand']:
        return jsonify({})
    context = {'n': n, 'languages': {lang: {} for lang in curSentData['languages']},
               'src_alignment': {}}
    neighboringIDs = {lang: {'next': -1, 'prev': -1} for lang in curSentData['languages']}
    for lang in curSentData['languages']:
        langID = settings['languages'].index(lang)
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
                if '_source' in curSent and ('lang' not in curSent['_source']
                                             or curSent['_source']['lang'] != langID):
                    curCxLang[side] = ''
                    continue
                if '_source' in curSent and side + '_id' in curSent['_source']:
                    neighboringIDs[lang][side] = curSent['_source'][side + '_id']
                expandedContext = sentView.process_sentence(curSent,
                                                            numSent=lastSentNum,
                                                            getHeader=False,
                                                            lang=lang)
                curCxLang[side] = expandedContext['languages'][lang]['text']
                sentView.relativize_src_alignment(expandedContext, curSentData['src_alignment_files'])
                context['src_alignment'].update(expandedContext['src_alignment'])
                set_session_data('last_sent_num', lastSentNum)
            else:
                curCxLang[side] = ''
    update_expanded_contexts(context, neighboringIDs)
    return jsonify(context)


@app.route('/search_word_query')
@jsonp
def search_word_query():
    query = copy_request_args()
    change_display_options(query)

    if 'doc_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs

    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    return jsonify(query)


@app.route('/search_word_json')
@jsonp
def search_word_json():
    query = copy_request_args()
    change_display_options(query)

    if 'doc_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs

    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_words(query)
    return jsonify(hits)


@app.route('/search_word')
def search_word():
    query = copy_request_args()
    change_display_options(query)
    if 'doc_ids' not in query:
        docIDs = subcorpus_ids(query)
        if docIDs is not None:
            query['doc_ids'] = docIDs
    else:
        docIDs = query['doc_ids']

    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_words(query)
    hitsProcessed = sentView.process_word_json(hits, docIDs)
    return render_template('result_words.html', data=hitsProcessed)


@app.route('/search_doc_query')
@jsonp
def search_doc_query():
    query = copy_request_args()
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=get_session_data('page_size'))
    return jsonify(query)


@app.route('/search_doc_json')
@jsonp
def search_doc_json():
    query = copy_request_args()
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=get_session_data('page_size'))
    hits = sc.get_docs(query)
    return jsonify(hits)


@app.route('/search_doc')
@jsonp
def search_doc():
    query = copy_request_args()
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=get_session_data('page_size'))
    hits = sc.get_docs(query)
    hitsProcessed = sentView.process_docs_json(hits)
    return render_template('result_docs.html', data=hitsProcessed)


@app.route('/get_word_fields')
def get_word_fields():
    result = '\n'.join(field + ': <input type="text" class="search_input" name="' + field +
                       '1" id="' + field + '1"><br>'
                       for field in wordFields)
    return result


@app.route('/media/<path:path>')
def send_media(path):
    return send_from_directory(os.path.join('../media', corpus_name), path)


def prepare_results_for_download(sentData):
    """
    Return a list of search results in a format easily transformable
    to csv/xlsx.
    """
    result = []
    for sent in sentData:
        header = ''
        sentCSV = []
        for lang in settings['languages']:
            if (lang not in sent['languages']
                    or 'highlighted_text' not in sent['languages'][lang]):
                sentCSV.append('')
                continue
            sentCSV.append(sent['languages'][lang]['highlighted_text'])
            langID = settings['languages'].index(lang)
            if 'id' in sent['languages'][lang] and len(header) <= 0:
                sentJSON = sc.get_sentence_by_id(sent['languages'][lang]['id'])
                if (len(sentJSON) > 0
                        and 'hits' in sentJSON
                        and 'hits' in sentJSON
                        and len(sentJSON['hits']['hits']) > 0):
                    sentJSON = sentJSON['hits']['hits'][0]
                    if '_source' in sentJSON and ('lang' not in sentJSON['_source']
                                                  or sentJSON['_source']['lang'] != langID):
                        continue
                    if len(header) <= 0:
                        header = sentView.process_sentence_header(sentJSON['_source'], format='csv')
        result.append([header] + sentCSV)
    return result


@app.route('/download_cur_results_csv')
def download_cur_results_csv():
    sentData = get_session_data('sentence_data')
    if sentData is None:
        return ''
    result = prepare_results_for_download(sentData)
    return '\n'.join(['\t'.join(s) for s in result if len(s) > 0])

@app.route('/download_cur_results_xlsx')
def download_cur_results_xlsx():
    sentData = get_session_data('sentence_data')
    if sentData is None:
        return None
    results = prepare_results_for_download(sentData)
    XLSXFilename = 'results-' + str(uuid.uuid4()) + '.xlsx'
    workbook = xlsxwriter.Workbook('tmp/' + XLSXFilename)
    worksheet = workbook.add_worksheet('Search results')
    for i in range(len(results)):
        for j in range(len(results[i])):
            worksheet.write(i, j, results[i][j])
    workbook.close()
    return send_from_directory('../tmp', XLSXFilename)

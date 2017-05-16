from flask import Flask, request, after_this_request, render_template, session, jsonify, current_app
import json
import gzip
import functools
from functools import wraps
import os
import copy
import random
import uuid
from search_engine.client import SearchClient
from search_engine.word_relations import WordRelations
from .response_processors import SentenceViewer


SETTINGS_DIR = '../conf'
MAX_PAGE_SIZE = 100
f = open(os.path.join(SETTINGS_DIR, 'corpus.json'), 'r', encoding='utf-8')
settings = json.loads(f.read())
f.close()
corpus_name = settings['corpus_name']
localizations = {}
supportedLocales = ['ru', 'en']
sc = SearchClient(SETTINGS_DIR, mode='test')
sentView = SentenceViewer(SETTINGS_DIR, sc)
wr = WordRelations(SETTINGS_DIR, sentView)


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
        nextID = prevID = docID = -1
        if '_source' in sent:
            if 'next_id' in sent['_source']:
                nextID = sent['_source']['next_id']
            if 'prev_id' in sent['_source']:
                prevID = sent['_source']['prev_id']
            docID = sent['_source']['doc_id']
        curSentIDs.append({'id': sent['_id'],
                           'doc_id': docID,
                           'next_id': nextID,
                           'prev_id': prevID,
                           'times_expanded': 0})
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
    for side in ['next', 'prev']:
        if side in context and len(context[side]) > 0:
            curSent[side + '_id'] = neighboringIDs[side]


@app.route('/search')
def search_page():
    return render_template('index.html', corpus_name=corpus_name)


@app.route('/search_sent_query/<int:page>')
@app.route('/search_sent_query')
@jsonp
def search_sent_query(page=0):
    if request.args and page <= 0:
        query = copy.deepcopy(request.args)
        page = 1
        change_display_options(query)
        set_session_data('last_query', query)
    else:
        query = get_session_data('last_query')
    set_session_data('page', page)
    wordConstraints = wr.get_constraints(query)
    wordConstraints = {str(k): v for k, v in wordConstraints.items()}
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          page=get_session_data('page'))
    return jsonify([query, wordConstraints])


@app.route('/search_sent_json/<int:page>')
@app.route('/search_sent_json')
@jsonp
def search_sent_json(page=0):
    if request.args and page <= 0:
        query = copy.deepcopy(request.args)
        page = 1
        change_display_options(query)
        set_session_data('last_query', query)
        wordConstraints = wr.get_constraints(query)
    else:
        query = get_session_data('last_query')
        wordConstraints = get_session_data('word_constraints')
    set_session_data('page', page)
    if len(wordConstraints) > 0:
        set_session_data('word_constraints', wordConstraints)
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          page=get_session_data('page'))
    hits = sc.get_sentences(query)
    if len(wordConstraints) > 0 and 'hits' in hits and 'hits' in hits['hits']:
        for hit in hits['hits']['hits']:
            hit['relations_satisfied'] = wr.check_sentence(hit, wordConstraints)
            # if wr.check_sentence(hit, wordConstraints):
            #     hit['relations_satisfied'] = True
            # else:
            #     hit['relations_satisfied'] = False
    return jsonify(hits)


@app.route('/search_sent/<int:page>')
@app.route('/search_sent')
def search_sent(page=0):
    if request.args and page <= 0:
        query = copy.deepcopy(request.args)
        page = 1
        change_display_options(query)
        set_session_data('last_query', query)
        wordConstraints = wr.get_constraints(query)
        set_session_data('word_constraints', wordConstraints)
    else:
        query = get_session_data('last_query')
        wordConstraints = get_session_data('word_constraints')
    set_session_data('page', page)
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          randomSeed=get_session_data('seed'),
                          query_size=get_session_data('page_size'),
                          page=get_session_data('page'))
    hits = sc.get_sentences(query)

    if len(wordConstraints) > 0 and get_session_data('distance_strict'):
        sc.qp.filter_sentences(hits, wordConstraints)
    elif len(wordConstraints) > 0 and 'hits' in hits and 'hits' in hits['hits']:
        for hit in hits['hits']['hits']:
            hit['relations_satisfied'] = wr.check_sentence(hit, wordConstraints)
    hitsProcessed = sentView.process_sent_json(hits)
    hitsProcessed['page'] = get_session_data('page')
    hitsProcessed['page_size'] = get_session_data('page_size')
    add_sent_to_session(hits)
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
    if sentData is None or n >= len(sentData):
        return jsonify({})
    curSentData = sentData[n]
    if curSentData['times_expanded'] >= settings['max_context_expand']:
        return jsonify({})
    context = {'n': n}
    neighboringIDs = {'next': -1, 'prev': -1}
    for side in ['next', 'prev']:
        if side + '_id' in curSentData:
            context[side] = sc.get_sentence_by_id(curSentData[side + '_id'])
        if (len(context[side]) > 0
                and 'hits' in context[side]
                and 'hits' in context[side]['hits']
                and len(context[side]['hits']['hits']) > 0):
            lastSentNum = get_session_data('last_sent_num') + 1
            curSent = context[side]['hits']['hits'][0]
            if '_source' in curSent and side + '_id' in curSent['_source']:
                neighboringIDs[side] = curSent['_source'][side + '_id']
            expandedContext = sentView.process_sentence(curSent,
                                                        numSent=lastSentNum,
                                                        getHeader=False)
            context[side] = expandedContext['text']
            set_session_data('last_sent_num', lastSentNum)
        else:
            context[side] = ''
    update_expanded_contexts(context, neighboringIDs)
    return jsonify(context)


@app.route('/search_word_query')
@jsonp
def search_word_query():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    return jsonify(query)


@app.route('/search_word_json')
@jsonp
def search_word_json():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_words(query)
    return jsonify(hits)


@app.route('/search_word')
def search_word():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_words(query)
    hitsProcessed = sentView.process_word_json(hits)
    return render_template('result_words.html', data=hitsProcessed)



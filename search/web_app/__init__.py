from flask import Flask, request, after_this_request, render_template, session, jsonify, current_app
import json
import gzip
import functools
from functools import wraps
import os
import copy
import uuid
from search_engine.client import SearchClient
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
sentView = SentenceViewer(SETTINGS_DIR)


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
                                          'login': False,
                                          'locale': 'en',
                                          'sort': ''}


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
    if u'session_id' not in session:
        return False
    return fieldName in sessionData[session[u'session_id']]


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


@app.route('/search')
def search_page():
    return render_template('index.html', corpus_name=corpus_name)


@app.route('/search_sent_query')
def search_sent_query():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    return jsonify(query)


@app.route('/search_sent_json')
def search_sent_json():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_sentences(query)
    return jsonify(hits)


@app.route('/search_sent')
def search_sent():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='sentences',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_sentences(query)

    # --- TEST ---
    # fTest = open('test_response.json', 'r', encoding='utf-8-sig')
    # testResponse = fTest.read()
    # fTest.close()
    # hits = json.loads(testResponse)
    # --- END OF TEST ---

    hitsProcessed = sentView.process_sent_json(hits)
    return render_template('result_sentences.html', data=hitsProcessed)


@app.route('/search_word_query')
def search_word_query():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    return jsonify(query)


@app.route('/search_word_json')
def search_word_json():
    query = copy.deepcopy(request.args)
    change_display_options(query)
    query = sc.qp.html2es(query,
                          searchIndex='words',
                          sortOrder=get_session_data('sort'),
                          query_size=get_session_data('page_size'))
    hits = sc.get_words(query)
    return jsonify(hits)



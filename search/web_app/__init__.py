from flask import Flask, request, after_this_request, render_template, session, jsonify, current_app
import json
import gzip
import functools
from functools import wraps
import os
import copy
from search_engine.client import SearchClient


SETTINGS_DIR = '../conf'
f = open(os.path.join(SETTINGS_DIR, 'corpus.json'), 'r', encoding='utf-8')
settings = json.loads(f.read())
f.close()
corpus_name = settings['corpus_name']
localizations = {}
supportedLocales = ['ru', 'en']
sc = SearchClient()


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


@app.route('/search')
def search_page():
    return render_template('index.html', corpus_name=corpus_name)


@app.route('/search_sent')
def search_sent():
    query = copy.deepcopy(request.args)
    result = query
    return jsonify(result)


@app.route('/search_word')
def search_word():
    query = copy.deepcopy(request.args)
    result = query
    return jsonify(result)

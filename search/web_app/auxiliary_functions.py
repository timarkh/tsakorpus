import gzip
from functools import wraps, update_wrapper
import copy
import math
import json
import time
from flask import request, current_app, after_this_request, make_response
from . import settings
from .transliteration import *


rxFieldNum = re.compile('^([^0-9]+)([0-9]+)$')


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
    @wraps(f)
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


def lang_sorting_key(lang):
    """
    Function for sorting language names in the output according
    to the general order provided by the settings.
    """
    if lang in settings.languages:
        return settings.languages.index(lang), -1, ''
    elif re.sub('_[0-9]+$', '', lang) in settings.languages:
        return (settings.languages.index(re.sub('_[0-9]+$', '', lang)),
                int(re.sub('^.*_', '', lang)), '')
    else:
        return len(settings.languages), 0, lang


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
                mFieldNum = rxFieldNum.search(field)
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


def wilson_confidence_interval(p, n, multiplier, z=1.644854):
    """
    Calculate the Wilson confidence interval for Binomial
    distribution, given n trials with p success rate.
    """
    # z: 1.96 for 95%
    # 1.645 for 90%
    if p > 1:
        p = 1.0
    elif p < 0:
        p = 0.0
    center = (p + z * z / (2 * n)) / (1 + z * z / (2 * n))
    halfLength = (z / (1 + z * z / n)) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lowerBound = min(p, (center - halfLength)) * multiplier
    upperBound = max(p, (center + halfLength)) * multiplier
    return lowerBound, upperBound


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


def log_query(queryType, args, fnameLog='query_log.txt'):
    """
    Log the query if the settings allow that.
    """
    if not settings.query_log:
        return
    logString = time.strftime('%Y-%m-%d %H:%M') + '\t' + queryType + '\t' \
                + json.dumps(args, indent=None, sort_keys=True, ensure_ascii=False) + '\n'
    with open(fnameLog, 'a', encoding='utf-8') as fLog:
        fLog.write(logString)

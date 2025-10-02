"""
Manage session data and cookies.
"""


from flask import session, after_this_request
import uuid
import json
import re
from datetime import datetime
from . import settings, sessionData, MAX_PAGE_SIZE
from .search_context import SearchContext


fields2cookies = {'locale', 'page_size', 'context_size', 'translit', 'hidden_tiers', 'enable_uri_links'}


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
                                          'context_size': 0,
                                          'enable_uri_links': False,
                                          'login': False,
                                          'locale': settings.default_locale,
                                          'sort': '',
                                          'distance_strict': False,
                                          'last_query': {},
                                          'seed': int(datetime.now().timestamp()),
                                          'excluded_doc_ids': set(),
                                          'invert_subcorpus': False,    # if True, then excluded_doc_ids actually contain selected doc IDs
                                          'hidden_tiers': [],
                                          'progress': 100,
                                          'search_context': SearchContext(curLocale=settings.default_locale)}


def get_session_data(fieldName):
    """
    Get the value of the fieldName parameter for the current session.
    If the session has not yet been initialized, initialize it first.
    If the parameter is supported, but not in the session dictionary,
    initialize the parameter first.
    """
    global sessionData
    if ('session_id' not in session
            or session['session_id'] not in sessionData
            or 'search_context' not in sessionData[session['session_id']]):
        initialize_session()

    if fieldName == 'login' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['login'] = False
    elif fieldName == 'locale' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['locale'] = 'en'
    elif fieldName == 'page_size' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['page_size'] = 10
    elif fieldName == 'context_size' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['context_size'] = 0
    elif fieldName == 'last_sent_num' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['last_sent_num'] = -1
    elif fieldName == 'seed' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['seed'] = int(datetime.now().timestamp())
    elif fieldName == 'excluded_doc_ids' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['excluded_doc_ids'] = set()
    elif fieldName == 'invert_subcorpus' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['invert_subcorpus'] = False
    elif fieldName == 'hidden_tiers' and fieldName not in sessionData[session['session_id']]:
        sessionData[session['session_id']]['hidden_tiers'] = []
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


def add_cookie(fieldName, value):
    if type(value) in (list, dict):
        value = json.dumps(value, indent=-1, sort_keys=True, ensure_ascii=False)
    elif type(value) != str:
        value = str(value)

    @after_this_request
    def add_cookie_to_response(response):
        response.set_cookie(fieldName, value, samesite='Strict', max_age=90 * 60 * 60 * 24)
        return response


def set_session_data(fieldName, value, setCookie=True):
    """
    Set the value of the fieldName parameter for the current session.
    If the session has not yet been initialized, initialize it first.
    If setCookie == True and a parameter values should be stored in a
    cookie, add a cookie to the current request.
    """
    global sessionData
    if ('session_id' not in session
            or session['session_id'] not in sessionData
            or 'search_context' not in sessionData[session['session_id']]):
        initialize_session()

    if fieldName == 'page_size':
        if value > MAX_PAGE_SIZE:
            value = MAX_PAGE_SIZE
        elif value < 1:
            value = 1

    if fieldName == 'context_size':
        value = int(value)
        if value > settings.max_context_expand:
            value = settings.max_context_expand
        elif value < 0:
            value = 0

    if fieldName == 'translit':
        sessionData[session['session_id']]['search_context'].translit = value
    else:
        sessionData[session['session_id']][fieldName] = value

    if fieldName == 'locale':
        sessionData[session['session_id']]['search_context'].locale = value     # Stored in two places

    if setCookie and fieldName in fields2cookies:
        add_cookie(fieldName, value)


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


def cur_search_context():
    return get_session_data('search_context')


def change_display_options(query):
    """
    Remember the new display options provided in the query.
    """
    searchContext = cur_search_context()
    searchContext.after_key = None

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

    if 'context_size' in query:
        try:
            cs = int(query['context_size'])
            if cs > settings.max_context_expand:
                cs = settings.max_context_expand
            elif cs < 0:
                cs = 0
            set_session_data('context_size', cs)
        except:
            set_session_data('context_size', 0)

    if 'sort' in query:
        set_session_data('sort', query['sort'])

    if 'distance_strict' in query:
        set_session_data('distance_strict', True)
    else:
        set_session_data('distance_strict', False)

    if 'enable_uri_links' in query:
        set_session_data('enable_uri_links', True)
    else:
        set_session_data('enable_uri_links', False)

    if 'translit' in query:
        searchContext.translit = query['translit']
        add_cookie('translit', query['translit'])
    else:
        searchContext.translit = None

    if ('random_seed' in query
            and re.search('^[1-9][0-9]*', query['random_seed']) is not None
            and 0 < int(query['random_seed']) < 1000000):
        set_session_data('seed', int(query['random_seed']))

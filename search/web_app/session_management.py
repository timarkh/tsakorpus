"""
Manage session data and cookies.
"""


from flask import session
import uuid
import random
import re
from . import settings, sessionData, MAX_PAGE_SIZE
from .search_context import SearchContext


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
                                          'locale': settings.default_locale,
                                          'sort': '',
                                          'distance_strict': False,
                                          'last_query': {},
                                          'seed': random.randint(1, 1000000),
                                          'excluded_doc_ids': set(),
                                          'progress': 100,
                                          'search_context': SearchContext()}


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
    if 'sort' in query:
        set_session_data('sort', query['sort'])
    if 'distance_strict' in query:
        set_session_data('distance_strict', True)
    else:
        set_session_data('distance_strict', False)
    if 'translit' in query:
        searchContext.translit = query['translit']
    else:
        searchContext.translit = None
    if ('random_seed' in query
            and re.search('^[1-9][0-9]*', query['random_seed']) is not None
            and 0 < int(query['random_seed']) < 1000000):
        set_session_data('seed', int(query['random_seed']))

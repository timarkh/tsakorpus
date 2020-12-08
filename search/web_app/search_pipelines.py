"""
High-level functions that handle user queries by transforming
them into series of ES queries using the query parser and
processing the hits using response_processors.
"""


import copy
import math
from flask import request
from . import sc, sentView, settings
from .session_management import set_session_data, get_session_data, get_locale, change_display_options, cur_search_context
from .auxiliary_functions import jsonp, gzipped, nocache, lang_sorting_key, copy_request_args,\
    wilson_confidence_interval, distance_constraints_too_complex


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
    curSearchContext = cur_search_context()
    for s in find_parallel_for_one_sent(sSource):
        curSearchContext.last_sent_num += 1
        curSearchContext.add_sent_data_for_session(s, curSearchContext.sentence_data[numHit])
        langID = s['_source']['lang']
        lang = settings.languages[langID]
        langView = lang
        if 'transVar' in s['_source']:
            langView += '_' + str(s['_source']['transVar'])
        sentHTML = sentView.process_sentence(s,
                                             numSent=curSearchContext.last_sent_num,
                                             getHeader=False,
                                             lang=lang,
                                             langView=langView,
                                             translit=curSearchContext.translit)['languages'][langView]['text']
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
    if fieldName not in settings.search_meta['stat_options'] or langID >= len(settings.languages) > 1:
        return {}
    innerQuery = {'match_all': {}}
    if docIDs is not None:
        innerQuery = {'ids': {'type': 'doc', 'values': list(docIDs)}}
    if not fieldName.startswith('year'):
        queryFieldName = fieldName + '_kw'
    else:
        queryFieldName = fieldName
    if len(settings.languages) == 1 or langID < 0:
        nWordsFieldName = 'n_words'
        nSentsFieldName = 'n_sents'
    else:
        nWordsFieldName = 'n_words_' + settings.languages[langID]
        nSentsFieldName = 'n_sents_' + settings.languages[langID]
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
    if fieldName not in settings.search_meta['stat_options'] or langID >= len(settings.languages) > 1:
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


def get_word_buckets(searchType, metaField, nWords, htmlQuery,
                     queryWordConstraints, langID, searchIndex):
    """
    Perform an actual DB search for a request about the distribution
    of a word/context over the values of a document-level or a
    sentence-level metafield.
    """
    bSentenceLevel = (metaField in settings.sentence_meta)
    if bSentenceLevel:
        queryFieldName = 'sent_meta_' + metaField + '_kw1'
    elif metaField not in settings.line_plot_meta:
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
                                  searchType='words',
                                  sortOrder='',
                                  query_size=1,
                                  distances=queryWordConstraints)
            if searchIndex == 'words' and newBucket['n_words'] > 0:
                hits = sc.get_words(query)
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
                    newBucket['n_sents'] = hits['hits']['total']['value']
                if not bSentenceLevel:
                    newBucket['n_docs'] = hits['aggregations']['agg_ndocs']['value'] / newBucket['n_docs'] * 100
                else:
                    newBucket['n_sents'] = hits['hits']['total']['value'] / newBucket['n_sents'] * 100
            curWordBuckets.append(newBucket)
        results.append(curWordBuckets)
    return results

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


def count_occurrences(query, distances=None):
    esQuery = sc.qp.html2es(query,
                            searchOutput='sentences',
                            sortOrder='no',
                            query_size=1,
                            distances=distances)
    hits = sc.get_sentences(esQuery)
    # print(hits)
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
                or hits['hits']['total']['value'] > settings.max_distance_filter):
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


import re
import os
import json
import random
from .word_relations import WordRelations


class InterfaceQueryParser:
    rxParentheses = re.compile('[()]')
    rxStars = re.compile('^(\\**|(\\.\\*)*|\\^(\\.\\*)+\\$)$')
    rxGlossQueryQuant = re.compile('^\\(([^()]+)\\)([*+?])$')
    rxGlossQuerySrc = re.compile('^([^{}]*)\\{([^{}]*)\\}$')
    rxFieldNum = re.compile('^([^0-9]+)([0-9]+)$')
    rxNumber = re.compile('^(?:0|-?[1-9][0-9]*)$')
    maxQuerySize = 500  # maximum number of hits to be requested

    dictOperators = {',': 'must',
                     '&': 'must',
                     '|': 'should'}

    def __init__(self, settings_dir, settings, rp=None):
        with open(os.path.join(settings_dir, 'categories.json'),
                  'r', encoding='utf-8-sig') as fIn:
            self.gramDict = json.loads(fIn.read())
        self.settings = settings

        self.rxSimpleText = re.compile('^[^\\[\\]()*\\\\{}^$.?+~|,&]*$')
        self.rxBooleanText = re.compile('^[^\\[\\]()\\\\{}^$.+|]*$')
        if self.settings.regex_simple_search is not None and len(self.settings.regex_simple_search) > 0:
            self.rxSimpleText = re.compile(self.settings.regex_simple_search)
        self.wordFields = self.settings.word_fields
        self.wr = WordRelations(settings_dir, rp=rp)
        self.docMetaFields = ['author', 'title', 'genre']
        self.docMetaFields += [f for f in self.settings.viewable_meta
                               if f not in self.docMetaFields and f != 'filename'
                               and f not in settings.sentence_meta]
        self.docMetaFields += [f for f in self.settings.search_meta['stat_options']
                               if f not in self.docMetaFields and f != 'filename'
                               and f not in settings.sentence_meta]
        kwMetaFields = [f + '_kw' for f in self.docMetaFields
                        if not f.startswith('year')
                        and f not in self.settings.integer_meta_fields]
        self.docMetaFields += kwMetaFields
        self.rp = rp    # ResponseProcessor instance
        # for g in self.gramDict:
        #     self.gramDict[g] = 'ana.gr.' + self.gramDict[g]

        self.maxFreqRank = 10000    # Number of buckets for queries with rank aggregation

    @staticmethod
    def find_operator(strQuery, start=0, end=-1, glossField=False):
        if end == -1:
            end = len(strQuery) - 1
        if strQuery[start] == '~':
            return start, '~'
        parenthBalance = 0
        inCurlyBrackets = False
        for i in range(start, end):
            if glossField:
                if inCurlyBrackets:
                    if strQuery[i] == '}':
                        inCurlyBrackets = False
                    continue
                if strQuery[i] == '{':
                    inCurlyBrackets = True
                    continue
            if strQuery[i] == '(':
                parenthBalance += 1
            elif strQuery[i] == ')':
                parenthBalance -= 1
            elif parenthBalance == 0 and strQuery[i] in ',&|':
                return i, strQuery[i]
        return -1, ''

    def make_gloss_query_src_part(self, text, lang):
        """
        Make the part of the gloss query which is inside the curly brackets.
        Basically, it means checking that all regular expressions within them
        do not eat anything outside of them.
        """
        result = ''
        inBrackets = False
        prevBackslash = False
        for c in text:
            if prevBackslash:
                result += c
                prevBackslash = False
                continue
            if c == '\\':
                result += c
                prevBackslash = True
                continue
            if c == '[':
                inBrackets = True
            elif c == ']':
                inBrackets = False
            elif c == '.' and not inBrackets:
                c = '[^{}]'
            result += c
        return result

    def make_gloss_query_part(self, text, lang):
        """
        Return a regexp for a single gloss part of a gloss query.
        """
        text = text.lower()
        if text == '*':
            return '(.+[\\-=<>])?'
        elif text == '+':
            return '([^\\-=<>].*[\\-=<>])'
        elif text == '?':
            return '([^\\-=<>{}]+\\{[^{}]+\\}[\\-=<>])'
        mQuant = self.rxGlossQueryQuant.search(text)
        if mQuant is not None:
            glossBody, quantifier = self.make_gloss_query_part(mQuant.group(1), lang), mQuant.group(2)
            return '(' + glossBody + ')' + quantifier
        mSrc = self.rxGlossQuerySrc.search(text)
        if mSrc is not None:
            glossTag, glossSrc = mSrc.group(1), mSrc.group(2)
            if len(glossTag) <= 0:
                return '[^{}]*\\{(' + self.make_gloss_query_src_part(glossSrc, lang) + ')\\}[\\-=<>]'
            return '(' + glossTag + ')\\{(' + self.make_gloss_query_src_part(glossSrc, lang) + ')\\}[\\-=<>]'
        if (lang in self.settings.lang_props
                and 'gloss_shortcuts' in self.settings.lang_props[lang]
                and text in self.settings.lang_props[lang]['gloss_shortcuts']):
            text = self.settings.lang_props[lang]['gloss_shortcuts'][text]
            return '(' + text + ')\\{[^{}]+\\}[\\-=<>]'
        return '(' + text.replace('.', '\\.') + ')\\{[^{}]+\\}[\\-=<>]'

    def make_simple_gloss_query(self, text, lang):
        """
        Return a regexp for an entire gloss query.
        """
        qStart, qEnd = '(.*[\\-=<>])?', '.*'
        if text.startswith('#'):
            qStart = ''
            text = text[1:]
        if text.endswith('#'):
            qEnd = ''
            text = text[:-1]
        parts = text.split('-')
        result = ''.join(self.make_gloss_query_part(part, lang)
                         for part in parts if len(part) > 0)
        return qStart + result + qEnd

    def make_simple_term_query(self, text, field, lang, keyword_query=False):
        """
        Make a term query that will become one of the inner parts
        of the compound bool query. Recognize simple wildcards and regexps.
        If the field is "ana.gr", find categories for every gramtag. If no
        category is available for some tag, return empty query.
        """
        if type(text) == str and len(text) <= 0:
            return {}
        if field == 'ana.gloss_index' or field.endswith('.ana.gloss_index'):
            # return {'regexp': {field: text}}
            return {'regexp': {field: self.make_simple_gloss_query(text, lang)}}
        elif keyword_query:
            return {'match': {field: text}}
        elif not (field == 'ana.gr' or field.endswith('.ana.gr')):
            if field in self.settings.viewable_meta:
                text = text.lower()
            elif field == 'w_id':
                field = '_id'   # search for word ID: _id in words index, but words.w_id in sentences index
            if self.rxStars.search(text) is not None:
                return {'match_all': {}}
            elif self.rxSimpleText.search(text) is not None:
                return {'match': {field: text}}
            elif self.rxBooleanText.search(text) is not None:
                return {'wildcard': {field: text}}
            else:
                if text.startswith('^'):
                    text = text[1:]
                if text.endswith('$'):
                    text = text[:-1]
                return {'regexp': {field: text}}
        try:
            field += '.' + self.gramDict[lang][text]
            return {'match': {field: text}}
        except KeyError:
            if (lang in self.settings.lang_props
                    and 'gramm_shortcuts' in self.settings.lang_props[lang]
                    and text in self.settings.lang_props[lang]['gramm_shortcuts']):
                text = self.settings.lang_props[lang]['gramm_shortcuts'][text]
                return self.make_bool_query(text, field, lang, keyword_query=keyword_query)
        return {'match_none': {}}

    def make_bool_query(self, strQuery, field, lang, start=0, end=-1, keyword_query=False):
        """
        Make a bool elasticsearch query from a string like (XXX|Y*Z),~ABC.
        If the field is "ana.gr", find categories for every gramtag. If no
        category is available for some tag, return empty query.
        The function is recursive and only looks at the part of the string
        delimited by start and end parameters.
        """
        if end == -1:
            if type(strQuery) == int:
                return self.make_simple_term_query(strQuery, field, lang, keyword_query=True)
            if not keyword_query:
                if self.settings.search_remove_whitespaces:
                    strQuery = strQuery.replace(' ', '')
            else:
                strQuery = strQuery.strip()
                if '|' not in strQuery and '~' not in strQuery:
                    # Metadata query: metafields can contain commas and parentheses
                    return self.make_simple_term_query(strQuery, field, lang, keyword_query=keyword_query)
            end = len(strQuery)
            if end == 0:
                return {'match_none': {}}
            if not (field == 'ana.gr' or field.endswith('.ana.gr')) and self.rxSimpleText.search(strQuery) is not None:
                return self.make_simple_term_query(strQuery, field, lang)
            if strQuery.count('(') != strQuery.count(')'):
                return {'match_none': {}}
        if len(strQuery) <= 0 or start >= end:
            return {'match_none': {}}
        glossField = field.endswith('gloss_index')
        iOpPos, strOp = self.find_operator(strQuery, start, end, glossField)
        if iOpPos == -1:
            if strQuery[start] == '(' and strQuery[end - 1] == ')':
                return self.make_bool_query(strQuery, field, lang, start=start + 1, end=end - 1)
            else:
                return self.make_simple_term_query(strQuery[start:end], field, lang)
        if strOp in ',|&':
            resultLeft = self.make_bool_query(strQuery, field, lang, start=start, end=iOpPos)
            resultRight = self.make_bool_query(strQuery, field, lang, start=iOpPos + 1, end=end)
            if len(resultLeft) <= 0 or len(resultRight) <= 0:
                return {}
            return {'bool': {self.dictOperators[strOp]: [resultLeft, resultRight]}}
        elif strOp == '~':
            rest = strQuery[start + 1:end]
            if InterfaceQueryParser.rxParentheses.search(rest) is None:
                mustNotClause = [self.make_simple_term_query(t, field, lang)
                                 for t in rest.split('|')]
            else:
                mustNotClause = self.make_bool_query(strQuery, field, lang,
                                                     start=start+1, end=end)
            return {
                'bool': {
                    'must_not': mustNotClause
                }
            }
        return {}

    def make_range_query(self, listQuery, field):
        """
        Make a range elasticsearch query from a list with two integer values.
        """
        if type(listQuery) not in (list, tuple) or len(listQuery) != 2:
            return {'match_all': {}}
        if listQuery[0] is not None and type(listQuery[0]) == str:
            try:
                listQuery[0] = int(listQuery[0])
            except:
                listQuery[0] = None
        if listQuery[1] is not None and type(listQuery[1]) == str:
            try:
                listQuery[1] = int(listQuery[1])
            except:
                listQuery[1] = None
        query = {'range': {field: {}}}
        if listQuery[0] is not None:
            query['range'][field]['gte'] = listQuery[0]
        if listQuery[1] is not None:
            query['range'][field]['lte'] = listQuery[1]
        return query

    def make_n_ana_query(self, strQuery, field):
        """
        Make a simple bool query for the n_ana field, recognizing one of
        the several available options in strQuery.
        """
        if strQuery == 'nonambiguous':
            return {'match': {field: 1}}
        elif strQuery == 'none':
            return {'match': {field: 0}}
        elif strQuery == 'analyzed':
            return {'range': {field: {'gte': 1}}}
        elif strQuery == 'ambiguous':
            return {'range': {field: {'gte': 2}}}
        return {}

    def parse_word_query(self, word, field, lang):
        if self.rxSimpleText.search(word) is not None:
            return {'term': {field: word}}
        elif self.rxBooleanText.search(word) is not None:
            return self.make_bool_query(word, field, lang)
        else:
            return {'regexp': {field: word}}

    def make_nested_query(self, query, nestedPath, queryName='', highlightFields=None,
                          sortOrder='', searchOutput='sentences', constantScore=None):
        if constantScore is None:
            if sortOrder != 'random':
                esQuery = {'nested': {'path': nestedPath,
                                      'query': {'constant_score': {'filter': query, 'boost': 1}},
                                      'score_mode': 'sum'}}
            else:
                esQuery = {'nested': {'path': nestedPath,
                                      'query': query}}
        else:
            esQuery = {'nested': {'path': nestedPath,
                                  'query': {'constant_score': {'filter': query, 'boost': constantScore}},
                                  'score_mode': 'sum'}}
        if highlightFields is not None and len(highlightFields) > 0:
            esQuery['nested']['inner_hits'] = {'highlight':
                                               {'fields':
                                                {f: {'number_of_fragments': 100,
                                                     'fragment_size': 2048}
                                                 for f in highlightFields}},
                                               'size': 50}
            if len(queryName) > 0:
                esQuery['nested']['inner_hits']['name'] = queryName
        return esQuery

    def prepare_word_order_subquery(self, sortOrder='random',
                                    groupBy='word', subcorpus=False):
        """
        Return a dictionary containing a part of a word query
        responsible for sorting of the hits and, if needed, relevant
        subaggregations. Different search types (lemma vs. word,
        entire corpus vs. subcorpus) use different methods
        (simple search, bucketing, or subaggregations) and
        therefore require different types of ordering conditions.
        If no ordering clause is required, return None.
        """
        order = None
        subAggregations = None
        if subcorpus:
            subAggregations = {'subagg_freq': {'sum': {'field': 'freq'}},
                               'subagg_nforms': {'cardinality': {'field': 'w_id'}}}
            if sortOrder == 'wf':
                subAggregations['subagg_wf'] = {'max': {'field': 'wf_order'}}
                order = {'subagg_wf': 'asc'}
            elif sortOrder == 'lemma':
                subAggregations['subagg_lemma'] = {'max': {'field': 'l_order'}}
                order = {'subagg_lemma': 'asc'}
            elif sortOrder == 'freq':
                order = {'subagg_freq': 'desc'}
        else:
            if groupBy == 'word':
                if sortOrder == 'wf':
                    order = {'wf_order': {'order': 'asc'}}
                elif sortOrder == 'lemma':
                    order = {'l_order': {'order': 'asc'}}
                elif sortOrder == 'freq':
                    order = {'freq': {'order': 'desc'}}
            elif groupBy == 'lemma':
                subAggregations = {'subagg_freq': {'sum': {'field': 'freq'}},
                                   'subagg_nforms': {'cardinality': {'field': 'w_id'}}}
                if sortOrder in ('wf', 'lemma'):
                    order = {'l_order': {'terms': {'field': 'l_order'}}}
                elif sortOrder == 'freq':
                    order = {'lemma_freq': {'terms': {'field': 'lemma_freq', 'order': 'desc'}}}
        return order, subAggregations

    def composite_agg_word(self, query_size, order=None, groupBy='lemma', after_key=None):
        """
        Return a composite aggregation whose buckets should correspond
        to words or lemmata. (For now, we use this only for lemma queries
        in the entire corpus.)
        """
        agg = None
        if groupBy == 'lemma':
            agg = {
                'composite': {
                    'size': query_size,
                    'sources': [
                        {
                            'l_id': {
                                'terms': {
                                    'field': 'l_id'
                                }
                            }
                        }
                    ]
                }
            }
            if after_key is not None:
                # For pagination
                agg['composite']['after'] = after_key
            if order is not None:
                agg['composite']['sources'].insert(0, order)
        return agg

    def wrap_inner_word_query(self, innerQuery, query_from=0, query_size=10,
                              sortOrder='random', randomSeed=None, docIDs=None,
                              groupBy='word', after_key=None):
        """
        Make a full-fledged Elasticsearch word query out of the contents
        of the "query" parameter and additional options. Specifically,
        turn the query into a word[wtype=word_freq] query with necessary aggregations
        if the search is limited to a subcorpus (i.e. docIDs is not None).
        Return the Elasticsearch query.
        """
        subcorpus = (docIDs is not None)
        order, subAggregations = self.prepare_word_order_subquery(sortOrder, groupBy, subcorpus)
        if subcorpus or groupBy == 'lemma':
            # We need the buckets, not the hits
            query_from = 0

        if not subcorpus:
            if sortOrder == 'random':
                innerQuery = self.make_random(innerQuery, randomSeed=randomSeed)
            esQuery = {
                'query': innerQuery,
                'size': query_size,
                'from': query_from,
                '_source': {'excludes': ['sids']}
            }
            esQuery['aggs'] = {
                'agg_ndocs': {'cardinality': {'field': 'dids'}},
                'agg_freq': {'sum': {'field': 'freq'}},
                'agg_noccurrences': {'value_count': {'field': '_id'}}
            }
            if groupBy == 'lemma':
                esQuery['size'] = 0
                esQuery['aggs']['agg_noccurrences'] = {'cardinality': {'field': 'l_id'}}
                esQuery['aggs']['agg_group_by_word'] = self.composite_agg_word(query_size, order, groupBy, after_key)
                if subAggregations is not None:
                    esQuery['aggs']['agg_group_by_word']['aggs'] = subAggregations
            elif groupBy == 'word' and order is not None:
                esQuery['sort'] = order
        else:
            hasParentQuery = {'parent_type': 'word', 'score': True, 'query': innerQuery}
            innerWordFreqQuery = {
                'bool': {
                    'must': [
                        {'has_parent': hasParentQuery},
                        {'term': {'wtype': 'word_freq'}}
                    ],
                    'filter': [{
                        'terms': {'d_id': docIDs}
                    }]
                }
            }
            if sortOrder == 'random':
                innerWordFreqQuery = self.make_random(innerWordFreqQuery, randomSeed=randomSeed)
            mainAgg = {'agg_freq': {'sum': {'field': 'freq'}},
                       'agg_ndocs': {'cardinality': {'field': 'd_id'}}}
            if groupBy == 'word':
                mainAgg['agg_group_by_word'] = {
                    'terms': {
                        'field': 'w_id',
                        'size': query_size
                    }
                }
                mainAgg['agg_noccurrences'] = {'cardinality': {'field': 'w_id'}}
            elif groupBy == 'lemma':
                mainAgg['agg_group_by_word'] = {
                    'terms': {
                        'field': 'l_id',
                        'size': query_size
                    }
                }
                mainAgg['agg_noccurrences'] = {'cardinality': {'field': 'l_id'}}
            if subAggregations is not None:
                mainAgg['agg_group_by_word']['aggs'] = subAggregations
            if order is not None:
                mainAgg['agg_group_by_word']['terms']['order'] = order
            esQuery = {'query': innerWordFreqQuery, 'size': 0, 'aggs': mainAgg}
        # print(esQuery)
        return esQuery

    def full_word_query(self, queryDict, query_from=0, query_size=10, sortOrder='random',
                        randomSeed=None, lang=-1, groupBy='word', after_key=None):
        """
        Make a full ES query for the words index out of a dictionary
        with bool queries.
        If groupBy == 'word', search for words (objects with wtype='word'),
        if groupBy == 'lemma', search for lemmata.
        """
        wordAnaFields = {'ana.lex', 'ana.gr', 'ana.gloss_index'}
        for field in self.wordFields:
            wordAnaFields.add('ana.' + field)

        if 'doc_ids' in queryDict:
            docIDs = queryDict['doc_ids']
        else:
            docIDs = None

        # Use only the information from the first word box
        # (other cases require searching in the sentences index
        # and are processed in another function).
        if 'words' not in queryDict or len(queryDict['words']) <= 0:
            return {'query': {'match_none': {}}}
        queryDict, negQuery = queryDict['words'][0]

        if negQuery:
            mustWord = 'must_not'
        else:
            mustWord = 'must'

        queryDict = {k: queryDict[k] for k in queryDict
                     if queryDict[k] is not None and queryDict[k] != {}}
        queryDictWords, queryDictWordsAna = {}, {}
        for k, v in queryDict.items():
            if k in wordAnaFields:
                queryDictWordsAna[k] = v
            else:
                if k == 'w_id':
                    k = '_id'
                queryDictWords[k] = v
        if len(queryDict) <= 0:
            query = {'match_none': {}}
        else:
            query = []
            if len(queryDictWordsAna) > 0:
                if len(queryDictWordsAna) == 1:
                    queryWordsAna = list(queryDictWordsAna.values())[0]
                else:
                    queryWordsAna = {'bool': {'must': list(queryDictWordsAna.values())}}
                query.append(self.make_nested_query(queryWordsAna, nestedPath='ana',
                                                    sortOrder=sortOrder,
                                                    searchOutput='words'
                                                    ))
            if len(queryDictWords) > 0:
                if len(queryDictWords) == 1:
                    queryWords = list(queryDictWords.values())[0]
                else:
                    queryWords = {'bool': {'must': list(queryDictWords.values())}}
                query.append(queryWords)
            query = {'bool': {mustWord: query}}
            if lang >= 0:
                if 'must' not in query['bool']:
                    query['bool']['must'] = [{'term': {'lang': lang}}]
                else:
                    query['bool']['must'].append({'term': {'lang': lang}})
            # Do not look for the empty word or empty lemma, which have indexes of w0 and l0
            emptyItem = 'w0'    # for words
            idField = 'w_id'
            if groupBy == 'lemma':
                emptyItem = 'l0'
                idField = 'l_id'
            if 'must_not' not in query['bool']:
                query['bool']['must_not'] = [{'term': {idField: emptyItem}}]
            else:
                query['bool']['must_not'].append({'term': {idField: emptyItem}})
            # if docIDs is not None:
            #     if 'filter' not in query['bool']:
            #         query['bool']['filter'] = [{'terms': {'dids': docIDs}}]
            #     else:
            #         query['bool']['filter'].append({'terms': {'dids': docIDs}})
        esQuery = self.wrap_inner_word_query(query, query_from=query_from,
                                             query_size=query_size, sortOrder=sortOrder,
                                             randomSeed=randomSeed,
                                             docIDs=docIDs,
                                             groupBy=groupBy,
                                             after_key=after_key)
        return esQuery

    def sentence_index_query(self, sentIndex, mustNot=False, countFromEnd=False):
        """
        Make a part of the word query responsible for the index
        that the word has in the sentence. If mustNot is True,
        revert the query. sentIndex may be a non-negative integer
        or a list with two non-negative integers (range).
        If countFromEnd == True, use sentence_index_neg property,
        i.e. count indices starting from the end of the sentence.
        (The latter option actually is not supposed to be used here,
        but who knows.)
        """
        propName = 'sentence_index'
        if countFromEnd:
            propName = 'sentence_index_neg'
        if sentIndex is None:
            return {}
        query = {}
        if type(sentIndex) == list and len(sentIndex) == 2:
            if sentIndex[0] < 0 and sentIndex[1] >= 0:
                sentIndex[0] = 0
            if sentIndex[0] == sentIndex[1]:
                sentIndex = sentIndex[0]
        if type(sentIndex) == int:
            if not mustNot:
                query = {'match': {'words.' + propName: sentIndex}}
            else:
                query = {'bool':
                             {'must_not':
                                  {'term':
                                       {'words.' + propName: sentIndex}
                                   }
                              }
                         }
        elif type(sentIndex) == list and len(sentIndex) == 2:
            query = {'range':
                        {'words.' + propName:
                            {
                                'gte': sentIndex[0],
                                'lte': sentIndex[1]
                            }
                        }
                    }
        return query

    def single_word_sentence_query(self, queryDict, queryWordNum, sortOrder,
                                   negative=False, sentIndexQuery=None,
                                   highlightedWordSubindex=None,
                                   searchOutput='sentences'):
        """
        Make a part of the full sentence query that contains
        a query for a single word, taking a dictionary with
        bool queries as input.
        sentIndexQuery may be None (no restriction on the index the
        word should have in the sentence), non-negative integer
        (match sentence index), or a list with two non-negative integers.
        If searchOutput is 'words', highlight only the first word.
        """

        wordAnaFields = {'words.ana.lex', 'words.ana.gr', 'words.ana.gloss_index'}
        for field in self.wordFields:
            wordAnaFields.add('words.ana.' + field)
        wordFields = {'words.wf', 'words.wtype', 'words.n_ana', 'words.sentence_index',
                      'words.sentence_index_neg', 'words.w_id', 'words.l_id'}
        queryDict = {k: queryDict[k] for k in queryDict
                     if queryDict[k] is not None and queryDict[k] != {}}
        queryDictWords, queryDictWordsAna = {}, {}
        for k, v in queryDict.items():
            if k in wordAnaFields:
                queryDictWordsAna[k] = v
            elif k in wordFields:
                queryDictWords[k] = v
        if not negative and sentIndexQuery is not None:
            if 'words.sentence_index' not in queryDictWords:
                queryDictWords['words.sentence_index'] = sentIndexQuery
            else:
                queryDictWords['words.sentence_index'] = {
                    'bool': {
                        'must': [
                            queryDictWords['words.sentence_index'],
                            sentIndexQuery
                        ]
                    }
                }
        if (len(queryDictWords) <= 0
                and len(queryDictWordsAna) <= 0):
            return []

        query = []
        queryName = 'w' + str(queryWordNum)
        if queryWordNum > 1:
            constantScore = 0
        else:
            constantScore = 1
        if not negative and highlightedWordSubindex is not None:
            queryName += '_' + str(highlightedWordSubindex)
        if len(queryDictWordsAna) > 0:
            if len(queryDictWordsAna) == 1:
                queryWordsAna = list(queryDictWordsAna.values())[0]
            else:
                queryWordsAna = {'bool': {'must': list(queryDictWordsAna.values())}}
            if len(queryDictWords) > 0:
                queryDictWords['words.ana'] = self.make_nested_query(queryWordsAna,
                                                                     nestedPath='words.ana',
                                                                     queryName=queryName,
                                                                     highlightFields=['words.ana'],
                                                                     sortOrder=sortOrder,
                                                                     searchOutput=searchOutput)
            else:
                query.append(self.make_nested_query(queryWordsAna,
                                                    nestedPath='words.ana',
                                                    queryName=queryName,
                                                    highlightFields=['words.ana'],
                                                    sortOrder=sortOrder,
                                                    searchOutput=searchOutput,
                                                    constantScore=constantScore))
        if len(queryDictWords) > 0:
            if len(queryDictWords) == 1:
                queryWords = list(queryDictWords.values())[0]
            else:
                queryWords = {'bool': {'must': list(queryDictWords.values())}}
            query.append(self.make_nested_query(queryWords,
                                                nestedPath='words',
                                                queryName=queryName,
                                                highlightFields=['words'],
                                                sortOrder=sortOrder,
                                                searchOutput=searchOutput,
                                                constantScore=constantScore
                                                ))
        if negative:
            return [{'bool': {'must_not': query}}]
        return query

    def multiple_words_sentence_query(self, queryDict, sortOrder='random', distances=None,
                                      searchOutput='sentences'):
        """
        Build the main part of a sentence query. If the query is multi-word,
        call single word query maker for each word and combine single word
        queries taking the distance constraints into account.
        """
        distanceQueryTuples = []
        if len(queryDict['words']) <= 1:
            wordDesc, negQuery = queryDict['words'][0]
            return self.single_word_sentence_query(wordDesc, 1, sortOrder,
                                                   negative=negQuery,
                                                   searchOutput=searchOutput)
        else:
            nPivotalTerm, constraints = self.wr.find_pivotal_term(distances)
            for pivotalTermIndex in range(self.settings.max_words_in_sentence):
                distanceQueryTuple = []
                for iQueryWord in range(len(queryDict['words'])):
                    wordDesc, negQuery = queryDict['words'][iQueryWord]
                    curSentIndex = None
                    # print(iQueryWord, wordDesc)
                    if iQueryWord == nPivotalTerm - 1:  # nPivotalTerm is 1-based
                        if ('words.sentence_index' in wordDesc
                                and 'match' in wordDesc['words.sentence_index']
                                and 'words.sentence_index' in wordDesc['words.sentence_index']['match']):
                            # The pivotal word has a "position in sentence" constraint,
                            # which makes life easier (no need to search for combinations
                            # where the pivotal word is not in its prescribed place)
                            if (pivotalTermIndex != wordDesc['words.sentence_index']['match']['words.sentence_index']
                                    and 0 <= wordDesc['words.sentence_index']['match']['words.sentence_index'] < self.settings.max_words_in_sentence):
                                distanceQueryTuple = []
                                break
                        curSentIndex = self.sentence_index_query(pivotalTermIndex)
                        # print(curSentIndex)
                    elif iQueryWord + 1 in constraints:
                        for wordPair in constraints[iQueryWord + 1]:
                            if nPivotalTerm not in wordPair:
                                continue
                            negateDistances = (iQueryWord + 1 == wordPair[1])
                            constraint = distances[wordPair]
                            sentIndexFrom, sentIndexTo = constraint['from'], constraint['to']
                            if negateDistances:
                                sentIndexFrom, sentIndexTo = -sentIndexTo, -sentIndexFrom
                            sentIndexFrom = max(0, sentIndexFrom + pivotalTermIndex)
                            sentIndexTo = sentIndexTo + pivotalTermIndex
                            curSentIndex = self.sentence_index_query([sentIndexFrom, sentIndexTo])
                            break
                    else:
                        curSentIndex = self.sentence_index_query(pivotalTermIndex, mustNot=True)
                    distanceQueryTuple += self.single_word_sentence_query(wordDesc, iQueryWord + 1, sortOrder,
                                                                          negative=negQuery,
                                                                          sentIndexQuery=curSentIndex,
                                                                          highlightedWordSubindex=pivotalTermIndex,
                                                                          searchOutput=searchOutput)
                if len(distanceQueryTuple) > 0:
                    distanceQueryTuples.append(distanceQueryTuple)
            if len(distanceQueryTuples) == 1:
                return distanceQueryTuples[0]
            else:
                return [{'bool': {'should': [{'bool': {'must': dqt}} for dqt in distanceQueryTuples]}}]

    def full_sentence_query(self, queryDict, query_from=0, query_size=10,
                            sortOrder='random', randomSeed=None, lang=0,
                            searchOutput='sentences', distances=None,
                            includeNextWordField=False,
                            highlight=True):
        """
        Make a full ES query for the sentences index out of a dictionary
        with bool queries.
        searchOutput is either "sentences" (make normal query) or "words"
        (only highlight the first word; omit everything but the words).
        """
        topLevelFields = {'text'}
        queryDict = {k: queryDict[k] for k in queryDict
                     if queryDict[k] is not None and queryDict[k] != {}}
        queryDictTop = {}
        for k, v in queryDict.items():
            if k in topLevelFields:
                queryDictTop[k] = v
        if (len(topLevelFields) <= 0
                and len(queryDict['words']) <= 0):
            query = {'match_none': {}}
        else:
            query = []
            if lang >= 0:
                queryFilter = [{'term': {'lang': {'value': lang}}}]
            else:
                queryFilter = []

            # Add all word requirements to the query:
            query += self.multiple_words_sentence_query(queryDict, sortOrder=sortOrder, distances=distances,
                                                        searchOutput=searchOutput)

            # Add sentence-level requirements to the query:
            query += list(queryDictTop.values())
            if 'sent_ids' in queryDict:
                queryFilter.append({'ids': {'values': queryDict['sent_ids']}})
            elif 'doc_ids' in queryDict:
                queryFilter.append({'terms': {'doc_id': queryDict['doc_ids']}})
            if 'para_ids' in queryDict:
                queryFilter.append({'terms': {'para_ids': queryDict['para_ids']}})

            for k, v in queryDict.items():
                if k.startswith('sent_meta_'):
                    k = 'meta.' + k[10:]
                    if k.endswith('_kw'):
                        boolQuery = self.make_bool_query(v, k, lang=lang, keyword_query=True)
                    elif (k.endswith('__to')
                          and k[5:len(k)-3] in self.settings.integer_meta_fields):
                        boolQuery = self.make_range_query([None, v], k[:-3])
                    elif (k.endswith('__from')
                          and k[5:len(k)-3] in self.settings.integer_meta_fields):
                        boolQuery = self.make_range_query([v, None], k[:-3])
                    else:
                        boolQuery = self.make_bool_query(v, k, lang=lang)
                    if 'match_none' not in boolQuery:
                        queryFilter.append(boolQuery)

            # Combine the query with the filters:
            query = {'bool': {'must': query, 'filter': queryFilter}}

        if sortOrder in ('random', 'year'):
            query = self.make_random(query, randomSeed)
        elif sortOrder not in ('sent_id', 'no'):
            query = self.make_half_random(query, randomSeed)

        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        if sortOrder == 'year':
            esQuery['sort'] = [
                {
                    'meta.year': {
                        "order": "desc"
                    }
                },
                '_score'
            ]
        if sortOrder == 'sent_id':
            esQuery['sort'] = [
                {
                    'sent_id': {
                        "order": "asc"
                    }
                },
                '_score'
            ]
        if searchOutput == 'words':
            esQuery['_source'] = ['doc_id', 'lang']
            if includeNextWordField:
                esQuery['_source'] += ['words.wtype', 'words.next_word']
        esQuery['aggs'] = {'agg_ndocs': {'cardinality': {'field': 'doc_id'}},
                           'agg_nwords': {'stats': {'script': '_score'}}}
        if len(queryDictTop) > 0 and highlight:
            esQuery['highlight'] = {'fields': {f: {'number_of_fragments': 100,
                                                   'fragment_size': 2048}
                                               for f in queryDictTop}}
        # if sortOrder in self.sortOrders:
        return esQuery

    def make_random(self, query, randomSeed=None):
        """
        Add random ordering to the ES query.
        """
        query = {'function_score': {'query': query,
                                    'boost_mode': 'replace',
                                    'random_score': {}}}

        if randomSeed is not None:
            query['function_score']['random_score']['seed'] = str(randomSeed)
        return query

    def make_half_random(self, query, randomSeed=None):
        """
        Add random ordering to the ES query while preserving the ordering
        by number of terms found.
        """
        query = {'function_score': {'query': query,
                                    'boost_mode': 'sum',
                                    'random_score': {}}}
        if randomSeed is not None:
            query['function_score']['random_score']['seed'] = str(randomSeed)
        return query

    def subcorpus_query(self, htmlQuery, query_from=0, query_size=10,
                        sortOrder='random', randomSeed=None,
                        exclude=None):
        """
        Make an ES query to the docs index based on subcorpus selection
        fields in htmlQuery.
        """
        queryParts = []
        rangeQueriesFrom = {}
        rangeQueriesTo = {}
        for field in self.docMetaFields:
            if field in ('year_from', 'year_to'):
                continue
            elif field in htmlQuery and (type(htmlQuery[field]) == int or len(htmlQuery[field]) > 0):
                queryParts.append(self.make_bool_query(htmlQuery[field], field, 'all', keyword_query=True))
            elif (field + '__from' in htmlQuery
                  and (type(htmlQuery[field + '__from']) == int
                       or len(htmlQuery[field + '__from']) > 0)):
                rangeQueriesFrom[field] = htmlQuery[field]
            elif (field + '__to' in htmlQuery
                  and (type(htmlQuery[field + '__to']) == int
                       or len(htmlQuery[field + '__to']) > 0)):
                rangeQueriesTo[field] = htmlQuery[field]
        # Deal with year range queries (this can be tricky because the lower bound
        # has to be compared to year_from, but the upper bound has to be compared
        # to year_to in case there are two fields for the approximate date of creation)
        yearFrom, yearTo = None, None
        if 'year_from' in htmlQuery and (type(htmlQuery['year_from']) == int or len(htmlQuery['year_from']) > 0):
            yearFrom = htmlQuery['year_from']
        if 'year_to' in htmlQuery and (type(htmlQuery['year_to']) == int or len(htmlQuery['year_to']) > 0):
            yearTo = htmlQuery['year_to']
        if yearFrom is not None or yearTo is not None:
            if 'year_from' in self.docMetaFields and 'year_to' in self.docMetaFields:
                if yearFrom is not None:
                    queryParts.append(self.make_range_query([yearFrom, None], 'year_from'))
                if yearTo is not None:
                    queryParts.append(self.make_range_query([None, yearTo], 'year_to'))
            elif 'year' in self.docMetaFields:
                queryParts.append(self.make_range_query([yearFrom, yearTo], 'year'))
        # Now deal with the rest of ranged fields (...__from and ...__to in the HTML query)
        for field in set(f for f in rangeQueriesFrom) | set(f for f in rangeQueriesTo):
            if field in rangeQueriesFrom:
                if field in rangeQueriesTo:
                    queryParts.append(self.make_range_query([rangeQueriesFrom[field], rangeQueriesTo[field]], field))
                else:
                    queryParts.append(self.make_range_query([rangeQueriesFrom[field], None], field))
            else:
                queryParts.append(self.make_range_query([None, rangeQueriesTo[field]], field))
        # Remove manually excluded documents by ID
        if exclude is not None and len(exclude) > 0:
            queryParts.append({'bool': {'must_not': [{'terms': {'_id': list(exclude)}}]}})
        if len(queryParts) > 0:
            query = {'bool': {'must': queryParts}}
            if sortOrder == 'random':
                query = self.make_random(query, randomSeed)
        else:
            query = {'match_all': {}}

        aggNWords = {'agg_nwords': {'sum': {'field': 'n_words'}}}
        esQuery = {'query': query, 'from': query_from, 'size': query_size,
                   '_source': {'excludes': ['filename']},
                   'aggs': aggNWords}
        if sortOrder in self.docMetaFields:
            esQuery['sort'] = {sortOrder: {'order': 'asc'}}
        return esQuery

    def split_query_into_languages(self, htmlQuery):
        """
        Split single query into language parts, i. e. subqueries that
        refer to one language each.
        Return list of single-language queries. 
        """
        langQueryParts = {}     # langID -> query
        usedLangIDs = []        # langIDs of the query parts in the order of their appearance
        if 'n_words' not in htmlQuery:
            return None
        for iWord in range(int(htmlQuery['n_words'])):
            strWordNum = str(iWord + 1)
            if ('lang' + strWordNum not in htmlQuery
                    or htmlQuery['lang' + strWordNum] not in self.settings.languages):
                return None
            else:
                lang = htmlQuery['lang' + strWordNum]
                langID = str(self.settings.languages.index(lang))
            if langID not in langQueryParts:
                langQueryParts[langID] = {k: v for k, v in htmlQuery.items()
                                          if self.rxFieldNum.search(k) is None}
                langQueryParts[langID]['lang'] = lang
                usedLangIDs.append(langID)
            curWordNums = set()
            for k in langQueryParts[langID]:
                m = self.rxFieldNum.search(k)
                if m is not None:
                    curWordNums.add(int(m.group(2)))
            if len(curWordNums) <= 0:
                newWordNum = '1'
            else:
                newWordNum = str(max(curWordNums) + 1)
            langQueryParts[langID]['n_words'] = int(newWordNum)
            for k in htmlQuery:
                m = self.rxFieldNum.search(k)
                if m is not None and m.group(2) == strWordNum:
                    langQueryParts[langID][m.group(1) + newWordNum] = htmlQuery[k]
        return [langQueryParts[langID] for langID in usedLangIDs]

    def para_id_query(self, htmlQuery):
        """
        Make an ES query to the sentences index that only retrieves paraIDs.
        """
        esQuery = self.html2es(htmlQuery, sortOrder='')
        esQuery['_source'] = 'para_ids'
        return esQuery

    def remove_nonsense(self, htmlQuery):
        """
        Remove parameters that are logically impossible in the given context.
        """
        # No distance requirements for negative word queries
        for iWord in range(int(htmlQuery['n_words'])):
            strWordNum = str(iWord + 1)
            if 'negq' + strWordNum in htmlQuery:
                for k in [_ for _ in htmlQuery.keys()]:
                    if k.startswith(('word_rel_' + strWordNum + '_',
                                     'word_dist_from_' + strWordNum + '_',
                                     'word_dist_to_' + strWordNum + '_')):
                        del htmlQuery[k]

    def check_html_parameters(self, htmlQuery, page=1, query_size=10, searchOutput='sentences'):
        """
        Check if HTML query is valid. If so, calculate and return a number
        of parameters for subsequent insertion into the ES query.
        Return None otherwise.
        """
        if len(htmlQuery) <= 0 or 'n_words' not in htmlQuery:
            return None, None, None, None
        query_from = (page - 1) * query_size
        if 'lang1' not in htmlQuery or htmlQuery['lang1'] not in self.settings.languages:
            if self.settings.all_language_search_enabled:
                lang = 'all'
                langID = -1
            else:
                return None, None, None, None
        else:
            lang = htmlQuery['lang1']
            langID = self.settings.languages.index(lang)
        if int(htmlQuery['n_words']) > 1:
            searchIndex = 'sentences'
        elif ('sentence_index1' in htmlQuery
                and len(htmlQuery['sentence_index1']) > 0
                and self.rxNumber.search(htmlQuery['sentence_index1']) is not None
                and int(htmlQuery['sentence_index1']) != 0):
            searchIndex = 'sentences'
        elif any(k.startswith('sent_meta_')
                 and len(htmlQuery[k]) > 0 and htmlQuery[k] not in ('*', '.*')
                 for k in htmlQuery):
            searchIndex = 'sentences'
        else:
            searchIndex = searchOutput
        # searchIndex is the name of the ES index where the search is performed.
        # searchOutput is either "sentences" or "words", depending on how the results
        # will be viewed.
        return query_from, langID, lang, searchIndex

    def html2es(self, htmlQuery, page=1, query_size=10, sortOrder='random',
                randomSeed=None, searchOutput='sentences', groupBy='word',
                distances=None, includeNextWordField=False,
                after_key=None, highlight=True):
        """
        Make and return a ES query out of the HTML form data.
        """
        query_from, langID, lang, searchIndex =\
            self.check_html_parameters(htmlQuery, page, query_size, searchOutput)
        if query_from is None:
            return {'query': {'match_none': ''}}

        self.remove_nonsense(htmlQuery)
        # print(htmlQuery)

        prelimQuery = {'words': []}
        if searchIndex == 'sentences':
            pathPfx = 'words.'
            if 'sent_ids' in htmlQuery:
                prelimQuery['sent_ids'] = htmlQuery['sent_ids']
            # if 'wf1' not in htmlQuery or len(htmlQuery['wf1']) <= 0:
            #     htmlQuery['wf1'] = '*'
        else:
            pathPfx = ''

        if 'doc_ids' in htmlQuery:
            prelimQuery['doc_ids'] = [int(did) for did in htmlQuery['doc_ids']]
        if searchIndex == 'sentences' and 'para_ids' in htmlQuery:
            prelimQuery['para_ids'] = htmlQuery['para_ids']

        if self.settings.detect_lemma_queries:
            # Check if this is a query which means "Find all forms
            # of a particular lemma (possibly with additional constraints".
            # If it is, remove the cap on the number of forms found.
            if (searchOutput == 'words'
                and int(htmlQuery['n_words']) == 1
                and 'lex1' in htmlQuery
                and len(htmlQuery['lex1']) > 0
                and self.rxSimpleText.search(htmlQuery['lex1']) is not None):
                    query_size = self.maxQuerySize

        for iWord in range(int(htmlQuery['n_words'])):
            curPrelimQuery = {}
            strWordNum = str(iWord + 1)
            negQuery = ('negq' + strWordNum in htmlQuery)
            if searchIndex == 'sentences':
                curPrelimQuery[pathPfx + 'wtype'] = self.make_bool_query('word',
                                                                         pathPfx + 'wtype', lang)
            elif searchIndex == 'words':
                curWtype = 'word'
                if 'wtype' + strWordNum in htmlQuery:
                    curWtype = htmlQuery['wtype' + strWordNum]
                curPrelimQuery[pathPfx + 'wtype'] = self.make_bool_query(curWtype,
                                                                         pathPfx + 'wtype', lang)
            for field in ['wf', 'w_id', 'l_id']:
                if field + strWordNum in htmlQuery and len(htmlQuery[field + strWordNum]) > 0:
                    curPrelimQuery[pathPfx + field] = self.make_bool_query(htmlQuery[field + strWordNum],
                                                                           pathPfx + field, lang)
            if ('sentence_index' + strWordNum in htmlQuery
                    and len(htmlQuery['sentence_index' + strWordNum]) > 0
                    and self.rxNumber.search(htmlQuery['sentence_index' + strWordNum]) is not None
                    and int(htmlQuery['sentence_index' + strWordNum]) != 0):
                if int(htmlQuery['sentence_index' + strWordNum]) > 0:
                    sentIndex = int(htmlQuery['sentence_index' + strWordNum]) - 1
                    curPrelimQuery[pathPfx + 'sentence_index'] = self.make_bool_query(sentIndex,
                                                                                      pathPfx + 'sentence_index', lang)
                elif int(htmlQuery['sentence_index' + strWordNum]) < 0:
                    sentIndex = -int(htmlQuery['sentence_index' + strWordNum]) - 1
                    curPrelimQuery[pathPfx + 'sentence_index_neg'] = self.make_bool_query(sentIndex,
                                                                                          pathPfx + 'sentence_index_neg', lang)
            if groupBy == 'lemma':
                # only look for words with analyses
                curPrelimQuery[pathPfx + 'n_ana'] = self.make_n_ana_query('analyzed',
                                                                          pathPfx + 'n_ana')
            if 'n_ana' + strWordNum in htmlQuery and htmlQuery['n_ana' + strWordNum] != 'any':
                if groupBy != 'lemma' or htmlQuery['n_ana' + strWordNum] != 'none':
                    curPrelimQuery[pathPfx + 'n_ana'] = self.make_n_ana_query(htmlQuery['n_ana' + strWordNum],
                                                                              pathPfx + 'n_ana')
            for anaField in ['lex', 'gr', 'gloss_index'] + self.wordFields:
                if (anaField + strWordNum in htmlQuery
                        and len(htmlQuery[anaField + strWordNum]) > 0):
                    boolQuery = self.make_bool_query(htmlQuery[anaField + strWordNum],
                                                     pathPfx + 'ana.' + anaField, lang)
                    curPrelimQuery[pathPfx + 'ana.' + anaField] = boolQuery
            # if 'gr' + strWordNum in htmlQuery and len(htmlQuery['gr' + strWordNum]) > 0:
            #     curPrelimQuery[pathPfx + 'ana.gr'] = self.make_bool_query(htmlQuery['gr' + strWordNum],
            #                                                               pathPfx + 'ana.gr')
            if len(curPrelimQuery) > 0:
                prelimQuery['words'].append((curPrelimQuery, negQuery))
            for k, v in htmlQuery.items():
                mFieldNum = self.rxFieldNum.search(k)
                if mFieldNum is not None:
                    fieldName = mFieldNum.group(1)
                    if (fieldName.startswith('sent_meta_')
                            and type(v) != str or self.rxStars.search(v) is None):
                        prelimQuery[mFieldNum.group(1)] = v
        if searchIndex == 'sentences' and 'txt' in htmlQuery and len(htmlQuery['txt']) > 0:
            if 'precise' in htmlQuery and htmlQuery['precise'] == 'on':
                prelimQuery['text'] = {'match_phrase': {'text': htmlQuery['txt']}}
            else:
                prelimQuery['text'] = {'match': {'text': htmlQuery['txt']}}
        if searchIndex == 'sentences':
            queryDict = self.full_sentence_query(prelimQuery, query_from,
                                                 query_size, sortOrder,
                                                 randomSeed,
                                                 lang=langID,
                                                 searchOutput=searchOutput,
                                                 distances=distances,
                                                 includeNextWordField=includeNextWordField,
                                                 highlight=highlight)
        elif searchIndex == 'words':
            queryDict = self.full_word_query(prelimQuery, query_from, query_size, sortOrder,
                                             randomSeed, lang=langID, groupBy=groupBy,
                                             after_key=after_key)
        else:
            queryDict = {'query': {'match_none': ''}}
        return queryDict

    def word_freqs_query(self, htmlQuery, searchType='word'):
        """
        Make an ES query for obtaining the frequency data bucketed
        by frequency rank. Subcorpus and all non-first words in the
        query are ignored.
        """
        htmlQuery['n_words'] = 1
        wfFields = False
        # wfFields tells if the query contains fields that can
        # have different values for different forms of the same
        # lexeme. If it does and searchType == 'lemma', join
        # has to be used.
        for k in [_ for _ in htmlQuery.keys()]:
            if k not in ('n_words', 'lang', 'lang1') and re.search('[^0-9]1$', k) is None:
                del htmlQuery[k]
            elif re.search('^sentence_index', k) is not None:
                del htmlQuery[k]
            elif k not in ('n_words', 'lang', 'lang1', 'lex1'):
                if k == 'n_ana1' and htmlQuery[k] in ('any', 'analyzed'):
                    continue
                if k == 'wf1' and htmlQuery[k] in ('*', '.*'):
                    continue
                wfFields = True
        if searchType == 'word' or wfFields:
            htmlQuery['wtype1'] = 'word'
        else:
            htmlQuery['wtype1'] = 'lemma'
        esQuery = self.html2es(htmlQuery, query_size=0, sortOrder='', searchOutput='words')
        if searchType == 'lemma':
            esQuery['query']['bool']['must_not'].append({'term': {'l_id': 'l0'}})
        if searchType == 'lemma' and wfFields:
            esQuery['aggs'] = {
                'agg_rank': {
                    'terms': {
                        'field': 'lemma_rank_true',
                        'order': {'_key': 'asc'},
                        'size': self.maxFreqRank
                    },
                    'aggs': {
                        'subagg_nlemmata': {
                            'cardinality': {'field': 'l_id'}
                        }
                    }
                }
            }
        else:
            esQuery['aggs'] = {
                'agg_rank': {
                    'terms': {
                        'field': 'rank_true',
                        'order': {'_key': 'asc'},
                        'size': self.maxFreqRank
                    }
                }
            }
        return esQuery

    def filter_sentences(self, iterSent, constraints, nWords=1):
        """
        Remove sentences that do not satisfy the word relation constraints.
        """
        goodSentIDs = []
        for sent in iterSent:
            # sent['inner_hits'] = s
            if self.wr.check_sentence(sent, constraints, nWords=nWords):
                goodSentIDs.append(sent['_id'])
        return goodSentIDs

    def swap_query_words(self, w1, w2, htmlQuery):
        """
        Swap query words with numbers w1 and w2 in the HTML query.
        """
        if w1 == w2:
            return htmlQuery
        newQuery = {}
        for k, v in htmlQuery.items():
            mNum = self.rxFieldNum.search(k)
            if mNum is None:
                newQuery[k] = v
                continue
            curWordNum = int(mNum.group(2))
            fieldBase = mNum.group(1)
            if curWordNum == w1:
                newQuery[fieldBase + str(w2)] = v
            elif curWordNum == w2:
                newQuery[fieldBase + str(w1)] = v
            else:
                newQuery[k] = v
        return newQuery

    def remove_non_first_words(self, htmlQuery):
        """
        Remove all words except the first one from the HTML query.
        """
        newQuery = {}
        for k, v in htmlQuery.items():
            mNum = self.rxFieldNum.search(k)
            if mNum is None:
                newQuery[k] = v
                continue
            curWordNum = int(mNum.group(2))
            if curWordNum == 1:
                newQuery[k] = v
        return newQuery


if __name__ == '__main__':
    iqp = InterfaceQueryParser('../../conf')
    print(json.dumps(iqp.make_bool_query('(A|B|C*D),~Z', 'asd', 'all')))
    print(json.dumps(iqp.make_bool_query('~(A|(B.*[abc]|C*D))', 'asd', 'all')))

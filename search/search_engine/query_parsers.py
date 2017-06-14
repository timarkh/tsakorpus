import re
import os
import json
import random
from .word_relations import WordRelations


class InterfaceQueryParser:
    rxSimpleText = re.compile('^[^\\[\\]()*\\\\{}^$.?+~|]*$')
    rxBooleanText = re.compile('^[^\\[\\]()\\\\{}^$.+|]*$')
    rxParentheses = re.compile('[()]')
    rxStars = re.compile('^\\**$')
    rxGlossQueryQuant = re.compile('^\\(([^()]+)\\)([*+?])$')
    rxGlossQuerySrc = re.compile('^([^{}]*)\\{([^{}]*)\\}$')

    dictOperators = {',': 'must',
                     '&': 'must',
                     '|': 'should'}

    def __init__(self, settings_dir):
        f = open(os.path.join(settings_dir, 'categories.json'),
                 'r', encoding='utf-8-sig')
        self.gramDict = json.loads(f.read())
        f.close()
        f = open(os.path.join(settings_dir, 'corpus.json'),
                 'r', encoding='utf-8-sig')
        self.settings = json.loads(f.read())
        f.close()
        f = open(os.path.join(settings_dir, 'word_fields.json'),
                 'r', encoding='utf-8-sig')
        self.wordFields = json.loads(f.read())
        f.close()
        self.wr = WordRelations(settings_dir)
        self.docMetaFields = ['author', 'title', 'year1', 'year2', 'genre']
        if 'viewable_meta' in self.settings:
            self.docMetaFields += [f for f in self.settings['viewable_meta']
                                   if f not in self.docMetaFields and f != 'filename']
        # for g in self.gramDict:
        #     self.gramDict[g] = 'ana.gr.' + self.gramDict[g]

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
        if ('lang_props' in self.settings and lang in self.settings['lang_props']
                and 'gloss_shortcuts' in self.settings['lang_props'][lang]
                and text in self.settings['lang_props'][lang]['gloss_shortcuts']):
            text = self.settings['lang_props'][lang]['gloss_shortcuts'][text]
            return '(' + text + ')\\{[^{}]+\\}[\\-=<>]'
        return '(' + text.replace('.', '\\.') + ')\\{[^{}]+\\}[\\-=<>]'

    def make_simple_gloss_query(self, text, lang):
        """
        Return a regexp for an entire gloss query.
        """
        qStart, qEnd = '.*', '.*'
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

    def make_simple_term_query(self, text, field, lang):
        """
        Make a term query that will become one of the inner parts
        of the compound bool query. Recognize simple wildcards and regexps.
        If the field is "ana.gr", find categories for every gramtag. If no
        category is available for some tag, return empty query.
        """
        if len(text) <= 0:
            return {}
        if field == 'ana.gloss_index' or field.endswith('.ana.gloss_index'):
            # return {'regexp': {field: text}}
            return {'regexp': {field: self.make_simple_gloss_query(text, lang)}}
        elif not (field == 'ana.gr' or field.endswith('.ana.gr')):
            if InterfaceQueryParser.rxStars.search(text) is not None:
                return {'match_all': {}}
            elif InterfaceQueryParser.rxSimpleText.search(text) is not None:
                return {'match': {field: text}}
            elif InterfaceQueryParser.rxBooleanText.search(text) is not None:
                return {'wildcard': {field: text}}
            else:
                return {'regexp': {field: text}}
        try:
            field += '.' + self.gramDict[lang][text]
            return {'match': {field: text}}
        except KeyError:
            return {}

    def make_bool_query(self, strQuery, field, lang, start=0, end=-1):
        """
        Make a bool elasticsearch query from a string like (XXX|Y*Z),~ABC.
        If the field is "ana.gr", find categories for every gramtag. If no
        category is available for some tag, return empty query.
        The function is recursive and only looks at the part of the string
        delimited by start and end parameters.
        """
        if end == -1:
            strQuery = strQuery.replace(' ', '')
            end = len(strQuery)
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
        if strOp in u',|&':
            resultLeft = self.make_bool_query(strQuery, field, lang, start=start, end=iOpPos)
            resultRight = self.make_bool_query(strQuery, field, lang, start=iOpPos + 1, end=end)
            if len(resultLeft) <= 0 or len(resultRight) <= 0:
                return {}
            return {'bool': {self.dictOperators[strOp]: [resultLeft, resultRight]}}
        elif strOp == u'~':
            rest = strQuery[start + 1:end]
            if InterfaceQueryParser.rxParentheses.search(rest) is None:
                mustNotClause = [self.make_simple_term_query(t, field, lang)
                                 for t in rest.split('|')]
            else:
                mustNotClause = self.make_bool_query(strQuery, field, lang,
                                                     start=start+1, end=end)
            return {'bool': {'must_not': mustNotClause}}
        return {}

    def parse_word_query(self, word, field, lang):
        if InterfaceQueryParser.rxSimpleText.search(word) is not None:
            return {'term': {field: word}}
        elif InterfaceQueryParser.rxBooleanText.search(word) is not None:
            return self.make_bool_query(word, field, lang)
        else:
            return {'regexp': {field: word}}

    def make_nested_query(self, query, nestedPath, queryName='', highlightFields=None,
                          sortOrder=''):
        if sortOrder != 'random':
            esQuery = {'nested': {'path': nestedPath,
                                  'query': {'constant_score': {'query': query, 'boost': 1}},
                                  'score_mode': 'sum'}}
        else:
            esQuery = {'nested': {'path': nestedPath,
                                  'query': query}}
        if highlightFields is not None:
            esQuery['nested']['inner_hits'] = {'highlight':
                                               {'fields':
                                                {f: {'number_of_fragments': 50,
                                                     'fragment_size': 2048}
                                                 for f in highlightFields}},
                                               'size': 50}
            if len(queryName) > 0:
                esQuery['nested']['inner_hits']['name'] = queryName
        return esQuery

    def full_word_query(self, queryDict, query_from=0, query_size=10, sortOrder='random',
                        lang=-1):
        """
        Make a full ES query for the words index out of a dictionary
        with bool queries.
        """
        wordAnaFields = {'ana.lex', 'ana.gr', 'ana.gloss_index'}
        for field in self.wordFields:
            wordAnaFields.add('ana.' + field)

        if 'doc_ids' in queryDict:
            docIDs = queryDict['doc_ids']
        else:
            docIDs = None

        # for the time being, use only the information from the first word box
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
                                                    sortOrder=sortOrder))
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
            if docIDs is not None:
                if 'must' not in query['bool']:
                    query['bool']['must'] = [{'terms': {'dids': docIDs}}]
                else:
                    query['bool']['must'].append({'terms': {'dids': docIDs}})
        if sortOrder == 'random':
            query = self.make_random(query)
        esQuery = {'query': query, 'size': query_size, 'from': query_from,
                   '_source': {'excludes': ['sids']}}
        esQuery['aggs'] = {'agg_ndocs': {'cardinality': {'field': 'dids'}}}
        if sortOrder == 'wf':
            esQuery['sort'] = {'wf': {'order': 'asc'}}
        elif sortOrder == 'freq':
            esQuery['sort'] = {'freq': {'order': 'desc'}}
        # if sortOrder in self.sortOrders:
        return esQuery

    def single_word_sentence_query(self, queryDict, queryWordNum, sortOrder, negative=False):
        """
        Make a part of the full sentence query that contains
        a query for a single word, taking a dictionary with
        bool queries as input.
        """

        wordAnaFields = {'words.ana.lex', 'words.ana.gr', 'words.ana.gloss_index'}
        for field in self.wordFields:
            wordAnaFields.add('words.ana.' + field)
        wordFields = {'words.wf'}
        queryDict = {k: queryDict[k] for k in queryDict
                     if queryDict[k] is not None and queryDict[k] != {}}
        queryDictWords, queryDictWordsAna = {}, {}
        for k, v in queryDict.items():
            if k in wordAnaFields:
                queryDictWordsAna[k] = v
            elif k in wordFields:
                queryDictWords[k] = v
        if (len(queryDictWords) <= 0
                and len(queryDictWordsAna) <= 0):
            return []

        query = []
        queryName = 'w' + str(queryWordNum)
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
                                                                     sortOrder=sortOrder)
            else:
                query.append(self.make_nested_query(queryWordsAna,
                                                    nestedPath='words.ana',
                                                    queryName=queryName,
                                                    highlightFields=['words.ana'],
                                                    sortOrder=sortOrder))
        if len(queryDictWords) > 0:
            if len(queryDictWords) == 1:
                queryWords = list(queryDictWords.values())[0]
            else:
                queryWords = {'bool': {'must': list(queryDictWords.values())}}
            query.append(self.make_nested_query(queryWords,
                                                nestedPath='words',
                                                queryName=queryName,
                                                highlightFields=['words'],
                                                sortOrder=sortOrder))
        if negative:
            return [{'bool': {'must_not': query}}]
        return query

    def full_sentence_query(self, queryDict, query_from=0, query_size=10,
                            sortOrder='random', randomSeed=None, lang=0):
        """
        Make a full ES query for the sentences index out of a dictionary
        with bool queries.
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
            if lang >= 0:
                query = [{'term': {'lang': {'value': lang, 'boost': 0}}}]
            else:
                query = []
            for iQueryWord in range(len(queryDict['words'])):
                wordDesc, negQuery = queryDict['words'][iQueryWord]
                query += self.single_word_sentence_query(wordDesc, iQueryWord + 1, sortOrder,
                                                         negative=negQuery)
            query += list(queryDictTop.values())
            if 'sent_ids' in queryDict:
                query.append({'ids': {'values': queryDict['sent_ids']}})
            elif 'doc_ids' in queryDict:
                query.append({'terms': {'doc_id': queryDict['doc_ids']}})
            query = {'bool': {'must': query}}
        if sortOrder == 'random':
            query = self.make_random(query, randomSeed)
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        esQuery['aggs'] = {'agg_ndocs': {'cardinality': {'field': 'doc_id'}},
                           'agg_nwords': {'stats': {'script': '_score'}}}
        if len(queryDictTop) >= 0:
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

    def subcorpus_query(self, htmlQuery, query_from=0, query_size=10,
                        sortOrder='random', randomSeed=None):
        """
        Make an ES query to the docs index based on subcorpus selection
        fields in htmlQuery.
        """
        queryParts = []
        for field in self.docMetaFields:
            if field in htmlQuery and len(htmlQuery[field]) > 0:
                queryParts.append(self.make_bool_query(htmlQuery[field], field, 'all'))
        if len(queryParts) <= 0:
            return None
        query = {'bool': {'must': queryParts}}
        if sortOrder == 'random':
            query = self.make_random(query, randomSeed)

        addNWords = {'aggs': {'agg_nwords': {'stat': {'sum': 'n_words'}}}}
        # TODO: add n_words property in the indexator and then add this aggregation

        esQuery = {'query': query, 'from': query_from, 'size': query_size,
                   '_source': {'excludes': ['filename']}}
        if sortOrder in self.docMetaFields:
            esQuery['sort'] = {sortOrder: {'order': 'asc'}}
        return esQuery

    def html2es(self, htmlQuery, page=1, query_size=10, sortOrder='random',
                randomSeed=None, searchIndex='sentences'):
        """
        Make and return a ES query out of the HTML form data.
        """
        if len(htmlQuery) <= 0:
            return {'query': {'match_none': ''}}
        query_from = (page - 1) * query_size

        if 'lang' not in htmlQuery or htmlQuery['lang'] not in self.settings['languages']:
            if self.settings['all_language_search_enabled']:
                lang = 'all'
                langID = -1
            else:
                return {'query': {'match_none': ''}}
        else:
            lang = htmlQuery['lang']
            langID = self.settings['languages'].index(lang)

        prelimQuery = {'words': []}
        if searchIndex == 'sentences':
            pathPfx = 'words.'
            if 'sent_ids' in htmlQuery:
                prelimQuery['sent_ids'] = htmlQuery['sent_ids']
            if 'wf1' not in htmlQuery or len(htmlQuery['wf1']) <= 0:
                htmlQuery['wf1'] = '*'
        else:
            pathPfx = ''

        if 'doc_ids' in htmlQuery:
            prelimQuery['doc_ids'] = htmlQuery['doc_ids']

        if 'n_words' not in htmlQuery:
            return {'query': {'match_none': ''}}
        for iWord in range(int(htmlQuery['n_words'])):
            curPrelimQuery = {}
            strWordNum = str(iWord + 1)
            negQuery = ('negq' + strWordNum in htmlQuery)
            if 'wf' + strWordNum in htmlQuery and len(htmlQuery['wf' + strWordNum]) > 0:
                curPrelimQuery[pathPfx + 'wf'] = self.make_bool_query(htmlQuery['wf' + strWordNum],
                                                                      pathPfx + 'wf', lang)
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
        if searchIndex == 'sentences' and 'txt' in htmlQuery and len(htmlQuery['txt']) > 0:
            if 'precise' in htmlQuery and htmlQuery['precise'] == 'on':
                prelimQuery['text'] = {'match_phrase': {'text': htmlQuery['txt']}}
            else:
                prelimQuery['text'] = {'match': {'text': htmlQuery['txt']}}
        if searchIndex == 'sentences':
            queryDict = self.full_sentence_query(prelimQuery, query_from,
                                                 query_size, sortOrder,
                                                 randomSeed,
                                                 lang=langID)
        elif searchIndex == 'words':
            queryDict = self.full_word_query(prelimQuery, query_from, query_size, sortOrder,
                                             lang=langID)
        else:
            queryDict = {'query': {'match_none': ''}}
        return queryDict

    def filter_sentences(self, iterSent, constraints):
        """
        Remove sentences that do not satisfy the word relation constraints.
        """
        goodSentIDs = []
        for sent in iterSent:
            if self.wr.check_sentence(sent, constraints):
                goodSentIDs.append(sent['_id'])
        return goodSentIDs


if __name__ == '__main__':
    iqp = InterfaceQueryParser('../../conf')
    print(json.dumps(iqp.make_bool_query('(A|B|C*D),~Z', 'asd', 'all')))
    print(json.dumps(iqp.make_bool_query('~(A|(B.*[abc]|C*D))', 'asd', 'all')))

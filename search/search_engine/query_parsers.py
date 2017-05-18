import re
import os
import json
import random
from .word_relations import WordRelations


class InterfaceQueryParser:
    rxSimpleText = re.compile('^[^\\[\\]()*\\\\{}^$.?+~|]*$')
    rxBooleanText = re.compile('^[^\\[\\]\\\\{}^$.+]*$')
    rxParentheses = re.compile('[()]')

    dictOperators = {',': 'must',
                     '&': 'must',
                     '|': 'should'}

    def __init__(self, settings_dir):
        f = open(os.path.join(settings_dir, 'categories.json'),
                 'r', encoding='utf-8-sig')
        self.gramDict = json.loads(f.read())
        f.close()
        f = open(os.path.join(settings_dir, 'word_fields.json'),
                 'r', encoding='utf-8-sig')
        self.wordFields = json.loads(f.read())
        f.close()
        self.wr = WordRelations(settings_dir)
        # for g in self.gramDict:
        #     self.gramDict[g] = 'ana.gr.' + self.gramDict[g]

    @staticmethod
    def find_operator(strQuery, start=0, end=-1):
        if end == -1:
            end = len(strQuery) - 1
        if strQuery[start] == '~':
            return start, '~'
        parenthBalance = 0
        for i in range(start, end):
            if strQuery[i] == '(':
                parenthBalance += 1
            elif strQuery[i] == ')':
                parenthBalance -= 1
            elif parenthBalance == 0 and strQuery[i] in ',&|':
                return i, strQuery[i]
        return -1, ''

    def make_simple_term_query(self, text, field):
        """
        Make a term query that will become one of the inner parts
        of the compound bool query. Recognize simple wildcards and regexps.
        If the field is "ana.gr", find categories for every gramtag. If no
        category is available for some tag, return empty query.
        """
        if len(text) <= 0:
            return {}
        if not (field == 'ana.gr' or field.endswith('.ana.gr')):
            if InterfaceQueryParser.rxSimpleText.search(text) is not None:
                return {'match': {field: text}}
            elif InterfaceQueryParser.rxBooleanText.search(text) is not None:
                return {'wildcard': {field: text}}
            else:
                return {'regexp': {field: text}}
        try:
            field += '.' + self.gramDict[text]
            return {'match': {field: text}}
        except KeyError:
            return {}

    def make_bool_query(self, strQuery, field, start=0, end=-1):
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
        iOpPos, strOp = self.find_operator(strQuery, start, end)
        if iOpPos == -1:
            if strQuery[start] == '(' and strQuery[end - 1] == ')':
                return self.make_bool_query(strQuery, field, start + 1, end - 1)
            else:
                return self.make_simple_term_query(strQuery[start:end], field)
        if strOp in u',|&':
            resultLeft = self.make_bool_query(strQuery, field, start, iOpPos)
            resultRight = self.make_bool_query(strQuery, field, iOpPos + 1, end)
            if len(resultLeft) <= 0 or len(resultRight) <= 0:
                return {}
            return {'bool': {self.dictOperators[strOp]: [resultLeft, resultRight]}}
        elif strOp == u'~':
            rest = strQuery[start + 1:end]
            if InterfaceQueryParser.rxParentheses.search(rest) is None:
                mustNotClause = [self.make_simple_term_query(t, field)
                                 for t in rest.split('|')]
            else:
                mustNotClause = self.make_bool_query(strQuery, field,
                                                     start=start+1, end=end)
            return {'bool': {'must_not': mustNotClause}}
        return {}

    def parse_word_query(self, word, field):
        if InterfaceQueryParser.rxSimpleText.search(word) is not None:
            return {'term': {field: word}}
        elif InterfaceQueryParser.rxBooleanText.search(word) is not None:
            return self.make_bool_query(word, field)
        else:
            return {'regexp': {field: word}}

    def make_nested_query(self, query, nestedPath, queryName='', highlightFields=None,
                          sortOrder=''):
        esQuery = {'nested': {'path': nestedPath, 'query': query}}
        if highlightFields is not None:
            esQuery['nested']['inner_hits'] = {'highlight':
                                               {'fields':
                                                {f: {'number_of_fragments': 100,
                                                     'fragment_size': 2048}
                                                 for f in highlightFields}}}
            if len(queryName) > 0:
                esQuery['nested']['inner_hits']['name'] = queryName
        return esQuery

    def full_word_query(self, queryDict, query_from=0, query_size=10, sortOrder='random'):
        """
        Make a full ES query for the words index out of a dictionary
        with bool queries.
        """
        wordAnaFields = {'ana.lex', 'ana.gr'}
        for field in self.wordFields:
            wordAnaFields.add('ana.' + field)

        # for the time being, use only the information from the first word box
        if 'words' not in queryDict or len(queryDict['words']) <= 0:
            return {'query': {'match_none': {}}}
        queryDict = queryDict['words'][0]

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
                query.append(self.make_nested_query(queryWordsAna, nestedPath='ana'))
            if len(queryDictWords) > 0:
                if len(queryDictWords) == 1:
                    queryWords = list(queryDictWords.values())[0]
                else:
                    queryWords = {'bool': {'must': list(queryDictWords.values())}}
                query.append(queryWords)
            query = {'bool': {'must': query}}
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

    def single_word_sentence_query(self, queryDict, queryWordNum, sortOrder):
        """
        Make a part of the full sentence query that contains
        a query for a single word, taking a dictionary with
        bool queries as input.
        """
        wordAnaFields = {'words.ana.lex', 'words.ana.gr'}
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
                                                                     highlightFields=['words.ana'])
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
        return query

    def full_sentence_query(self, queryDict, query_from=0, query_size=10,
                            sortOrder='random', randomSeed=None):
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
            query = []
            for iQueryWord in range(len(queryDict['words'])):
                wordDesc = queryDict['words'][iQueryWord]
                query += self.single_word_sentence_query(wordDesc, iQueryWord + 1, sortOrder)
            query += list(queryDictTop.values())
            if 'sent_ids' in queryDict:
                query.append({'ids': {'values': queryDict['sent_ids']}})
            query = {'bool': {'must': query}}
        if sortOrder == 'random':
            query = self.make_random(query, randomSeed)
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        esQuery['aggs'] = {'agg_ndocs': {'cardinality': {'field': 'doc_id'}}}
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
            query['function_score']['random_score']['seed'] = randomSeed
        return query

    def html2es(self, htmlQuery, page=1, query_size=10, sortOrder='random',
                randomSeed=None, searchIndex='sentences'):
        """
        Make and return a ES query out of the HTML form data.
        """
        query_from = (page - 1) * query_size

        prelimQuery = {'words': []}
        if searchIndex == 'sentences':
            pathPfx = 'words.'
            if 'sent_ids' in htmlQuery:
                prelimQuery['sent_ids'] = htmlQuery['sent_ids']
        else:
            pathPfx = ''
        if 'n_words' not in htmlQuery:
            return {'query': {'match_none': ''}}
        for iWord in range(int(htmlQuery['n_words'])):
            curPrelimQuery = {}
            strWordNum = str(iWord + 1)
            if 'wf' + strWordNum in htmlQuery and len(htmlQuery['wf' + strWordNum]) > 0:
                curPrelimQuery[pathPfx + 'wf'] = self.make_bool_query(htmlQuery['wf' + strWordNum],
                                                                      pathPfx + 'wf')
            for anaField in ['lex', 'gr'] + self.wordFields:
                if (anaField + strWordNum in htmlQuery
                        and len(htmlQuery[anaField + strWordNum]) > 0):
                    boolQuery = self.make_bool_query(htmlQuery[anaField + strWordNum],
                                                     pathPfx + 'ana.' + anaField)
                    curPrelimQuery[pathPfx + 'ana.' + anaField] = boolQuery
            # if 'gr' + strWordNum in htmlQuery and len(htmlQuery['gr' + strWordNum]) > 0:
            #     curPrelimQuery[pathPfx + 'ana.gr'] = self.make_bool_query(htmlQuery['gr' + strWordNum],
            #                                                               pathPfx + 'ana.gr')
            if len(curPrelimQuery) > 0:
                prelimQuery['words'].append(curPrelimQuery)
        if searchIndex == 'sentences' and 'txt' in htmlQuery and len(htmlQuery['txt']) > 0:
            if 'precise' in htmlQuery and htmlQuery['precise'] == 'on':
                prelimQuery['text'] = {'match_phrase': {'text': htmlQuery['txt']}}
            else:
                prelimQuery['text'] = {'match': {'text': htmlQuery['txt']}}
        if searchIndex == 'sentences':
            queryDict = self.full_sentence_query(prelimQuery, query_from,
                                                 query_size, sortOrder,
                                                 randomSeed)
        elif searchIndex == 'words':
            queryDict = self.full_word_query(prelimQuery, query_from, query_size, sortOrder)
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
    print(json.dumps(iqp.make_bool_query('(A|B|C*D),~Z', 'asd')))
    print(json.dumps(iqp.make_bool_query('~(A|(B.*[abc]|C*D))', 'asd')))

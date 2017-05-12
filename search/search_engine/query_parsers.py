import re
import os
import json


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

    def make_nested_query(self, query, nestedPath, highlightFields=None):
        esQuery = {'nested': {'path': nestedPath, 'query': query}}
        if highlightFields is not None:
            esQuery['nested']['inner_hits'] = {'highlight':
                                               {'fields':
                                                {f: {'number_of_fragments': 100}
                                                 for f in highlightFields}}}
        return esQuery

    def full_word_query(self, queryDict, query_from=0, query_size=10, sortOrder='random'):
        """
        Make a full ES query for the words index out of a dictionary
        with bool queries.
        """
        wordAnaFields = {'ana.lex', 'ana.gr'}
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
            query = {'function_score': {'query': query,
                                        'boost_mode': 'replace',
                                        'random_score': {}}}
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        # if sortOrder in self.sortOrders:
        return esQuery

    def full_sentence_query(self, queryDict, query_from=0, query_size=10, sortOrder='random'):
        """
        Make a full ES query for the sentences index out of a dictionary
        with bool queries.
        """
        wordAnaFields = {'words.ana.lex', 'words.ana.gr'}
        wordFields = {'words.wf'}
        topLevelFields = {'text'}
        queryDict = {k: queryDict[k] for k in queryDict
                     if queryDict[k] is not None and queryDict[k] != {}}
        queryDictWords, queryDictWordsAna, queryDictTop = {}, {}, {}
        for k, v in queryDict.items():
            if k in wordAnaFields:
                queryDictWordsAna[k] = v
            elif k in wordFields:
                queryDictWords[k] = v
            elif k in topLevelFields:
                queryDictTop[k] = v
        if (len(queryDictWords) <= 0
                and len(queryDictWordsAna) <= 0
                and len(topLevelFields) <= 0):
            query = {'match_none': {}}
        else:
            query = []
            if len(queryDictWordsAna) > 0:
                if len(queryDictWordsAna) == 1:
                    queryWordsAna = list(queryDictWordsAna.values())[0]
                else:
                    queryWordsAna = {'bool': {'must': list(queryDictWordsAna.values())}}
                if len(queryDictWords) > 0:
                    queryDictWords['words.ana'] = self.make_nested_query(queryWordsAna,
                                                                         nestedPath='words.ana',
                                                                         highlightFields=['words.ana'])
                else:
                    query.append(self.make_nested_query(queryWordsAna, nestedPath='words.ana',
                                                        highlightFields=['words.ana']))
            if len(queryDictWords) > 0:
                if len(queryDictWords) == 1:
                    queryWords = list(queryDictWords.values())[0]
                else:
                    queryWords = {'bool': {'must': list(queryDictWords.values())}}
                query.append(self.make_nested_query(queryWords, nestedPath='words',
                                                    highlightFields=['words']))
            query += list(queryDictTop.values())
            query = {'bool': {'must': query}}
        if sortOrder == 'random':
            query = {'function_score': {'query': query,
                                        'boost_mode': 'replace',
                                        'random_score': {}}}
        esQuery = {'query': query, 'size': query_size, 'from': query_from}
        if len(queryDictTop) >= 0:
            esQuery['highlight'] = {'fields': {f: {'number_of_fragments': 100,
                                                   'fragment_size': 2048}
                                               for f in queryDictTop}}
        # if sortOrder in self.sortOrders:
        return esQuery

    def html2es(self, htmlQuery, query_from=0, query_size=10, sortOrder='random',
                searchIndex='sentences'):
        """
        Make and return a dict of bool queries out of the HTML form data.
        """
        prelimQuery = {}
        if searchIndex == 'sentences':
            pathPfx = 'words.'
        else:
            pathPfx = ''
        if 'wf' in htmlQuery and len(htmlQuery['wf']) > 0:
            prelimQuery[pathPfx + 'wf'] = self.make_bool_query(htmlQuery['wf'], pathPfx + 'wf')
        if 'l' in htmlQuery and len(htmlQuery['l']) > 0:
            prelimQuery[pathPfx + 'ana.lex'] = self.make_bool_query(htmlQuery['l'], pathPfx + 'ana.lex')
        if 'gr' in htmlQuery and len(htmlQuery['gr']) > 0:
            prelimQuery[pathPfx + 'ana.gr'] = self.make_bool_query(htmlQuery['gr'], pathPfx + 'ana.gr')
        if searchIndex == 'sentences' and 'txt' in htmlQuery and len(htmlQuery['txt']) > 0:
            if 'precise' in htmlQuery and htmlQuery['precise'] == 'on':
                prelimQuery['text'] = {'match_phrase': {'text': htmlQuery['txt']}}
            else:
                prelimQuery['text'] = {'match': {'text': htmlQuery['txt']}}
        if searchIndex == 'sentences':
            queryDict = self.full_sentence_query(prelimQuery, query_from, query_size, sortOrder)
        elif searchIndex == 'words':
            queryDict = self.full_word_query(prelimQuery, query_from, query_size, sortOrder)
        else:
            queryDict = {'query': {'match_none': ''}}
        return queryDict


if __name__ == '__main__':
    iqp = InterfaceQueryParser('../../conf')
    print(json.dumps(iqp.make_bool_query('(A|B|C*D),~Z', 'asd')))
    print(json.dumps(iqp.make_bool_query('~(A|(B.*[abc]|C*D))', 'asd')))

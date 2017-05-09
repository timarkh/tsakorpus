import re
import os
import json


class InterfaceQueryParser:
    rxSimpleText = re.compile('^[^\\[\\]()*\\\\{}^$.?+~|]*$')
    rxBooleanText = re.compile('^[^\\[\\]\\\\{}^$.+]*$')
    rxParentheses = re.compile('[()]')

    dictOperators = {u',': u'must',
                     u'&': u'must',
                     u'|': u'should'}

    def __init__(self, settings_dir):
        f = open(os.path.join(settings_dir, 'categories.json'),
                 'r', encoding='utf-8-sig')
        self.gramDict = json.loads(f.read())
        f.close()
        for g in self.gramDict:
            self.gramDict[g] = u'gr.' + self.gramDict[g]

    @staticmethod
    def find_operator(strQuery, start=0, end=-1):
        if end == -1:
            end = len(strQuery) - 1
        if strQuery[start] == u'~':
            return start, u'~'
        parenthBalance = 0
        for i in range(start, end):
            if strQuery[i] == u'(':
                parenthBalance += 1
            elif strQuery[i] == u')':
                parenthBalance -= 1
            elif parenthBalance == 0 and strQuery[i] in u',&|':
                return i, strQuery[i]
        return -1, u''

    def make_simple_term_query(self, text, field):
        """
        Make a term query that will become one of the inner parts
        of the compound bool query. If the field is "ana.gr", find
        categories for every gramtag. If no category is available
        for some tag, return {}.
        """
        if len(text) <= 0:
            return {}
        if field != 'ana.gr':
            if InterfaceQueryParser.rxSimpleText.search(text) is not None:
                return {'term': {field: text}}
            elif InterfaceQueryParser.rxBooleanText.search(text) is not None:
                return {'wildcard': {field: text}}
            else:
                return {'regexp': {field: text}}
        try:
            field += '.' + self.gramDict['text']
            return {'term': {field: text}}
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

if __name__ == '__main__':
    iqp = InterfaceQueryParser('../../conf')
    print(json.dumps(iqp.make_bool_query('(A|B|C*D),~Z', 'asd')))

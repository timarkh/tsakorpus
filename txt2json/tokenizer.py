import re
import copy


class Tokenizer:
    """
    Tokenizes strings into JSON objects.
    It is assumed that tokenization is language dependent.
    """

    rxPunc = re.compile('[^\\w ]')

    def __init__(self, settings):
        self.settings = copy.deepcopy(settings)

    def join_tokens(self, tokenL, tokenR):
        """
        Join tokenR to tokenL and make it a word.
        """
        tokenL['wf'] += tokenR['wf']
        tokenL['off_end'] = tokenR['off_end']
        tokenL['wtype'] = 'word'

    def join_hyphens(self, tokens):
        """
        Take the list of tokens and join token segments like W-W.
        """
        if len(tokens) <= 0:
            return tokens
        joinedTokens = []
        for i in range(len(tokens)):
            token = copy.deepcopy(tokens[i])
            if len(joinedTokens) <= 0:
                joinedTokens.append(token)
                continue
            if (token['wtype'] == 'word'
                    and joinedTokens[-1]['wtype'] == 'word'
                    and joinedTokens[-1]['off_end'] == token['off_start']):
                self.join_tokens(joinedTokens[-1], token)
            elif (i < len(tokens) - 1 and
                  token['wtype'] == 'punct' and
                  token['wf'] != '\\n' and
                  joinedTokens[-1]['wtype'] == 'word' and
                  tokens[i+1]['wtype'] == 'word' and
                  tokens[i]['off_start'] == joinedTokens[-1]['off_end'] and
                  tokens[i]['off_end'] == tokens[i+1]['off_start']):
                self.join_tokens(joinedTokens[-1], token)
            else:
                joinedTokens.append(token)
        return joinedTokens

    def tokenize(self, text):
        tokens = []
        curToken = {}
        for i in range(len(text)):
            c = text[i]
            if c == ' ' and curToken != {}:
                curToken['off_end'] = i
                tokens.append(curToken)
                curToken = {}
                continue
            if c == '\n':
                if curToken != {}:
                    curToken['off_end'] = i
                    tokens.append(curToken)
                    curToken = {}
                curToken['wtype'] = 'punct'
                curToken['off_start'] = i
                curToken['off_end'] = i + 1
                curToken['wf'] = '\\n'
                tokens.append(curToken)
                curToken = {}
                continue
            if curToken == {}:
                curToken['off_start'] = i
                curToken['wf'] = c
                if self.rxPunc.search(c) is not None:
                    curToken['wtype'] = 'punct'
                else:
                    curToken['wtype'] = 'word'
                continue
            bPunc = self.rxPunc.search(c) is not None
            if ((bPunc and curToken['wtype'] == 'word') or
                    (not bPunc and curToken['wtype'] == 'punct')):
                curToken['off_end'] = i
                tokens.append(curToken)
                curToken = {'off_start': i, 'wf': c}
                if bPunc:
                    curToken['wtype'] = 'punct'
                else:
                    curToken['wtype'] = 'word'
                continue
            curToken['wf'] += c
        return self.join_hyphens(tokens)

import re
import copy


class Tokenizer:
    """
    Tokenizes strings into JSON objects.
    It is assumed that tokenization is language dependent.
    """

    rxPunc = re.compile('[^\\w ]')
    rxOnlyPunc = re.compile('^[^\\w ]*$')

    def __init__(self, settings):
        self.settings = copy.deepcopy(settings)
        if 'non_word_internal_punct' not in self.settings:
            self.settings['non_word_internal_punct'] = ['\n', '\\n']
        self.tokenSplitRegexes = []
        self.specialTokenRegexes = []
        self.add_split_token_regexes()
        self.add_special_token_regexes()

    def add_split_token_regexes(self):
        """
        Add regexes that break certain spaceless tokens into parts.
        """
        if 'split_tokens' not in self.settings:
            return
        for strRx in self.settings['split_tokens']:
            if not strRx.startswith('^'):
                strRx = '^' + strRx
            if not strRx.endswith('$'):
                strRx += '$'
            try:
                self.tokenSplitRegexes.append(re.compile(strRx))
            except:
                print('Error when compiling a regex: ' + strRx)

    def add_special_token_regexes(self):
        """
        Add regexes that recognize certain special tokens,
        such as email addresses or text-based smileys.
        """
        if 'special_tokens' not in self.settings:
            return
        for strRx in self.settings['special_tokens']:
            try:
                self.specialTokenRegexes.append({'regex': re.compile(strRx),
                                                 'token': self.settings['special_tokens'][strRx]})
            except:
                print('Error when compiling a regex: ' + strRx)

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
                    and joinedTokens[-1]['off_end'] == token['off_start']
                    and (len(self.tokenSplitRegexes) <= 0
                         or joinedTokens[-1]['wf'].endswith('-'))):
                self.join_tokens(joinedTokens[-1], token)
            elif (i < len(tokens) - 1 and
                  token['wtype'] == 'punct' and
                  token['wf'] not in self.settings['non_word_internal_punct'] and
                  (len(token['wf']) <= 0 or all(c not in self.settings['non_word_internal_punct']
                                                for c in token['wf'])) and
                  joinedTokens[-1]['wtype'] == 'word' and
                  tokens[i+1]['wtype'] == 'word' and
                  tokens[i]['off_start'] == joinedTokens[-1]['off_end'] and
                  tokens[i]['off_end'] == tokens[i+1]['off_start']):
                self.join_tokens(joinedTokens[-1], token)
            else:
                joinedTokens.append(token)
        return joinedTokens

    def add_token(self, tokens, token):
        """
        Add one new token to the token list, taking into account that
        the settings may require splitting it into several parts.
        """
        if ('wtype' in token and token['wtype'] != 'word') or 'wf' not in token:
            tokens.append(token)
            return
        for r in self.tokenSplitRegexes:
            m = r.search(token['wf'])
            if m is not None:
                # print(token['wf'])
                for iGroup in range(1, 1 + len(m.groups())):
                    group = m.group(iGroup)
                    offStart, offEnd = m.span(iGroup)
                    if group is not None and len(group) > 0 and offStart >= 0 and offEnd >= 0:
                        newToken = copy.deepcopy(token)
                        newToken['off_end'] = newToken['off_start'] + offEnd
                        newToken['off_start'] += offStart
                        newToken['wf'] = group
                        tokens.append(newToken)
                return
        tokens.append(token)

    def tokenize(self, text):
        tokens = []
        curToken = {}
        i = -1
        while i < len(text) - 1:
            i += 1
            c = text[i]
            if c == ' ':
                if curToken != {}:
                    curToken['off_end'] = i
                    self.add_token(tokens, curToken)
                    curToken = {}
                continue
            if c == '\n':
                if curToken != {}:
                    curToken['off_end'] = i
                    self.add_token(tokens, curToken)
                    curToken = {}
                curToken['wtype'] = 'punct'
                curToken['off_start'] = i
                curToken['off_end'] = i + 1
                curToken['wf'] = '\\n'
                self.add_token(tokens, curToken)
                curToken = {}
                continue
            bSpecialTokenFound = False
            for rx in self.specialTokenRegexes:
                m = rx['regex'].match(text, pos=i)
                if m is not None:
                    if curToken != {}:
                        curToken['off_end'] = i
                        self.add_token(tokens, curToken)
                    curToken = copy.deepcopy(rx['token'])
                    if 'wtype' not in curToken:
                        curToken['wtype'] = 'word'
                    wf = m.group(0)
                    if 'wf' not in curToken:
                        curToken['wf'] = wf
                    curToken['off_start'] = i
                    curToken['off_end'] = i + len(wf)
                    i += len(wf) - 1
                    self.add_token(tokens, curToken)
                    curToken = {}
                    bSpecialTokenFound = True
                    break
            if bSpecialTokenFound:
                continue
            if curToken == {}:
                curToken['off_start'] = i
                curToken['wf'] = c
                if self.rxPunc.search(c) is not None:
                    curToken['wtype'] = 'punct'
                else:
                    curToken['wtype'] = 'word'
                continue
            bPunc = (self.rxPunc.search(c) is not None) or (c in self.settings['non_word_internal_punct'])
            if ((bPunc and curToken['wtype'] == 'word') or
                    (not bPunc and curToken['wtype'] == 'punct')):
                curToken['off_end'] = i
                self.add_token(tokens, curToken)
                curToken = {'off_start': i, 'wf': c}
                if bPunc:
                    curToken['wtype'] = 'punct'
                else:
                    curToken['wtype'] = 'word'
                continue
            curToken['wf'] += c
        if curToken != {}:
            curToken['off_end'] = len(text)
            self.add_token(tokens, curToken)
        return self.join_hyphens(tokens)

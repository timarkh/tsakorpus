import re
import copy


class Splitter:
    """
    Contains methods for splitting list of tokens
    into sentences.
    It is assumed that splitting is language dependent.
    """

    dictRxPunctClasses = {'comma': re.compile('[,，、]'),
                          'parenth': re.compile('[\\(\\)（）]'),
                          'fullstop': re.compile('[.։。]'),
                          'quest_mark': re.compile('[?;？]'),
                          'excl_point': re.compile('[!！]'),
                          'colon': re.compile('[:：]'),
                          'quote': re.compile('["«»‘’“”„‟『』《》]'),
                          'semicolon': re.compile('[;；]'),
                          'dash': re.compile('[‒–—―-]')}

    def __init__(self, settings):
        self.settings = copy.deepcopy(settings)
        try:
            self.rxSentEnd = re.compile(self.settings['sent_end_punc'])
        except:
            print('Please check your sentence end regexp.')
            self.rxSentEnd = re.compile('[.?!]')
        try:
            self.rxSentStart = re.compile(self.settings['sent_start'])
        except:
            print('Please check your sentence start regexp.')
            self.rxSentStart = re.compile('[A-ZА-ЯЁ]')

    def join_sentences(self, sentenceL, sentenceR):
        """
        Add the words and the text of sentenceR to sentenceL.
        """
        if len(sentenceR['words']) <= 0:
            return
        nSpacesBetween = sentenceR['words'][0]['off_start'] - sentenceL['words'][-1]['off_end']
        sentenceL['words'] += sentenceR['words']
        sentenceL['text'] += ' ' * nSpacesBetween + sentenceR['text']

    def append_sentence(self, sentences, s, text):
        """
        Append a sentence to the list of sentences. If it is
        not a real sentences, just add all of its tokens to the
        last sentence of the list.
        """
        if len(s['words']) == 0:
            s['text'] = ''
        else:
            startOffset = s['words'][0]['off_start']
            endOffset = s['words'][-1]['off_end']
            s['text'] = text[startOffset:endOffset]
        if len(s['words']) == 0:
            return
        if len(sentences) > 0 and all(w['wtype'] == 'punct'
                                      for w in s['words']):
            self.join_sentences(sentences[-1], s)
        else:
            sentences.append(s)

    def next_word(self, tokens, startNum):
        """
        Find the nearest wordform to the right of startNum,
        including startNum itself. Return its string value.
        """
        for i in range(startNum, len(tokens)):
            if tokens[i]['wtype'] == 'word':
                return tokens[i]['wf']
        return ''

    def recalculate_offsets_sentence(self, s):
        """
        Recalculate offsets in a single sentence
        so that they start at the beginning of the sentence.
        """
        if len(s['words']) <= 0:
            return
        startOffset = s['words'][0]['off_start']
        for w in s['words']:
            w['off_start'] -= startOffset
            w['off_end'] -= startOffset

    def recalculate_offsets(self, sentences):
        """
        Recalculate offsets so that they always start at the
        beginning of the sentence.
        """
        for s in sentences:
            self.recalculate_offsets_sentence(s)

    def add_next_word_id_sentence(self, s):
        """
        Insert the ID of the next word in a single sentence. (This is important for
        the sentences that can have multiple tokenization variants.)
        """
        if len(s['words']) <= 0:
            return
        words = s['words']
        leadingPunct = 0
        wordsStarted = False
        for i in range(len(words)):
            if not wordsStarted:
                if words[i]['wtype'] != 'word':
                    leadingPunct += 1
                else:
                    wordsStarted = True
            if words[i]['wtype'] not in ['style_span']:
                words[i]['next_word'] = i + 1
            if wordsStarted and not (all(words[j]['wtype'] != 'word' for j in range(i, len(words)))):
                words[i]['sentence_index'] = i - leadingPunct

    def add_next_word_id(self, sentences):
        """
        Insert the ID of the next word. (This is important for
        the sentences that can have multiple tokenization variants.)
        """
        for s in sentences:
            self.add_next_word_id_sentence(s)

    def add_contextual_flags_sentence(self, s):
        """
        Insert additional information about the context of the words in
        a sentence. This includes repetition of lemmata, grammatical
        categories, bordering a punctuation mark, etc.
        Put the information as tags in the "flags" list of the word
        objects. Do not return anything.
        """
        if len(s['words']) <= 0:
            return
        words = s['words']
        for i in range(len(words)):
            if words[i]['wtype'] != 'word':
                continue
            flags = set()
            if i < len(words) - 1:
                if words[i + 1]['wtype'] == 'punct' and len(words[i + 1]['wf']) > 0:
                    for punctClass in self.dictRxPunctClasses:
                        if self.dictRxPunctClasses[punctClass].search(words[i + 1]['wf'][-1]) is not None:
                            flags.add('b:' + punctClass)
                            flags.add('b:punct')
            if i > 0:
                if words[i - 1]['wtype'] == 'punct' and len(words[i - 1]['wf']) > 0:
                    for punctClass in self.dictRxPunctClasses:
                        if self.dictRxPunctClasses[punctClass].search(words[i - 1]['wf'][-1]) is not None:
                            flags.add('a:' + punctClass)
                            flags.add('a:punct')
                if 'ana' in words[i]:
                    for ana in words[i]['ana']:
                        flagsAna = set()
                        if 'ana' in words[i - 1]:
                            for k, v in ana.items():
                                if not k.startswith('gr.') and k != 'lex':
                                    continue
                                if any(k in anaPrev and anaPrev[k] == v
                                       for anaPrev in words[i - 1]['ana']):
                                    flagsAna.add('rep:' + k)
                        if len(flags) > 0 or len(flagsAna) > 0:
                            if 'flags' not in ana:
                                ana['flags'] = []
                            ana['flags'] += [flag for flag in sorted(flags | flagsAna)]

    def add_contextual_flags(self, sentences):
        """
        Insert contextual flags in each sentence.
        """
        for s in sentences:
            self.add_contextual_flags_sentence(s)

    def split(self, tokens, text):
        """
        Split the text into sentences by packing tokens into
        separate sentence JSON objects.
        Return the resulting list of sentences.
        """
        sentences = []
        curSentence = {'words': []}
        for i in range(len(tokens)):
            wf = tokens[i]['wf']
            curSentence['words'].append(tokens[i])
            if tokens[i]['wtype'] == 'punct':
                if (i == len(tokens) - 1
                        or (self.settings['newline_ends_sent'] and wf == '\\n')
                        or (self.rxSentEnd.search(wf) is not None
                            and i > 0
                            and tokens[i - 1]['wf'] not in self.settings['abbreviations']
                            and self.rxSentStart.search(self.next_word(tokens, i + 1)) is not None)):
                    self.append_sentence(sentences, curSentence, text)
                    curSentence = {'words': []}
                    continue
        self.recalculate_offsets(sentences)
        self.add_next_word_id(sentences)
        return sentences

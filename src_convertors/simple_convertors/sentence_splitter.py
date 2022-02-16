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
        # "Transparent punctuation" is punctuation that should not be counted
        # when calculating distances between words.
        if 'transparent_punctuation' in self.settings:
            try:
                self.rxPuncTransparent = re.compile(self.settings['transparent_punctuation'])
            except:
                print('Please check your transparent punctuation regexp.')
                self.rxPuncTransparent = re.compile('^ *$')
        else:
            self.rxPuncTransparent = re.compile('^ *$')

    def join_sentences(self, sentenceL, sentenceR, absoluteOffsets=False):
        """
        Add the words and the text of sentenceR to sentenceL.
        If absoluteOffsets == True, treat all start and end offsets as referring
        to the whole text rather than to the corresponding sentences.
        The operation may change sentenceR (it is assumed that sentenceR
        is not used anymore after this function has been called).
        """
        if len(sentenceR['words']) <= 0:
            return
        if absoluteOffsets:
            nSpacesBetween = sentenceR['words'][0]['off_start'] - sentenceL['words'][-1]['off_end']
            startOffsetShiftR = 0
        else:
            nSpacesBetween = 1  # Default: one space between sentences
            startOffsetShiftR = len(sentenceL['text']) + 1
            for word in sentenceR['words']:
                word['off_start'] += startOffsetShiftR
                word['off_end'] += startOffsetShiftR
        sentenceL['words'] += sentenceR['words']
        sentenceL['text'] += ' ' * nSpacesBetween + sentenceR['text']

        # Now, shift all character offsets in source alignment etc.
        for segType in ['src_alignment', 'para_alignment', 'style_spans']:
            if segType in sentenceR:
                if segType not in sentenceL:
                    sentenceL[segType] = []
                for seg in sentenceR[segType]:
                    for key in ['off_start', 'off_end', 'off_start_sent', 'off_end_sent']:
                        if key in seg:
                            seg[key] += startOffsetShiftR
                    sentenceL[segType].append(seg)

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
            self.join_sentences(sentences[-1], s, absoluteOffsets=True)
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
        Assign both forward and backward numbers.
        """
        if len(s['words']) <= 0:
            return
        words = s['words']
        # Forward numbering and next word ID (LTR)
        leadingPunct = 0
        maxWordNum = 0
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
                if words[i]['wtype'] == 'word' or self.rxPuncTransparent.search(words[i]['wf']) is None:
                    words[i]['sentence_index'] = i - leadingPunct
                    maxWordNum = i - leadingPunct
                else:
                    leadingPunct += 1

        # Backward numbering
        if maxWordNum > 0:
            for i in range(len(words)):
                if 'sentence_index' in words[i]:
                    words[i]['sentence_index_neg'] = maxWordNum - words[i]['sentence_index']

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

    def resegment_sentences(self, sentences):
        """
        Join adjacent sentences that look like parts of the same
        sentence. This function is used in ELAN conversion, where
        a sentence might be split into several alignment units.
        This is best done if the sentence are sorted by speaker
        and then by their time offset.
        """
        if ('sentence_segmentation' not in self.settings
                or not self.settings['sentence_segmentation']
                or 'sent_end_punc' not in self.settings):
            return
        langs2resegment = [i for i in range(len(self.settings['languages']))]
        if 'sentence_segmentation_languages' in self.settings:
            langs2resegment = [i for i in range(len(self.settings['languages']))
                               if self.settings['languages'][i] in self.settings['sentence_segmentation_languages']]
        langs2resegment = set(langs2resegment)
        for i in range(len(sentences) - 1, 0, -1):
            sentenceR = sentences[i]
            sentenceL = sentences[i - 1]
            if 'lang' not in sentenceL or 'lang' not in sentenceR:
                continue
            if sentenceL['lang'] not in langs2resegment:
                continue
            if sentenceR['lang'] not in langs2resegment:
                continue
            if ('text' in sentenceL
                    and not self.rxSentEnd.search(sentenceL['text'])
                    and sentenceL['lang'] == sentenceR['lang']
                    and ('meta' not in sentenceL or 'speaker' not in sentenceL['meta']
                         or sentenceL['meta']['speaker'] == sentenceR['meta']['speaker'])):
                self.join_sentences(sentenceL, sentenceR, absoluteOffsets=False)
                sentences.pop(i)

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
            elif i == len(tokens) - 1:
                self.append_sentence(sentences, curSentence, text)
        self.recalculate_offsets(sentences)
        self.add_next_word_id(sentences)
        return sentences

    def capitalize_sentences(self, sentences):
        """
        Capitalize first letter of the first word in each sentence.
        Change sentences, do not return anything.
        """
        for s in sentences:
            if 'words' not in s:
                continue
            for w in s['words']:
                if w['wtype'] != 'word' or len(w['wf']) <= 0:
                    continue
                w['wf'] = w['wf'][0].upper() + w['wf'][1:]
                s['text'] = s['text'][:w['off_start']] \
                            + s['text'][w['off_start']].upper() \
                            + s['text'][w['off_start'] + 1:]
                break

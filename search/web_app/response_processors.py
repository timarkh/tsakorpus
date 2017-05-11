import json
import re
import os


class SentenceViewer:
    """
    Contains methods for turning the JSON response of ES into
    viewable html.
    """

    def __init__(self, settings_dir):
        self.settings_dir = settings_dir
        f = open(os.path.join(self.settings_dir, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.sentence_props = ['text']

    def prepare_analyses(self, words, indexes):
        """
        Generate viewable analyses for the words with given indexes.
        """
        result = '---------\n'
        for i in indexes:
            if i < 0 or i >= len(words):
                continue
            word = words[i]
            if 'wf' in word:
                result += word['wf'] + '\n'
            if 'ana' in word:
                for iAna in range(len(word['ana'])):
                    result += 'Analysis #' + str(iAna + 1) + '.\n'
                    result += json.dumps(word['ana'][iAna], ensure_ascii=False, indent=2)
                    result += ' \n'
        result = result.replace('\n', '\\n').replace('"', "'")
        return result

    def build_span(self, sentSrc, numSent, curWords, matchWordOffsets):
        dataAna = self.prepare_analyses(sentSrc['words'], curWords)

        def highlightClass(nWord):
            if nWord in matchWordOffsets:
                return ' match'
            return ''

        spanStart = '<span class="word ' + \
                    ' '.join('w' + str(numSent) + '_' + str(n) + highlightClass(n)
                             for n in curWords) + '" data-ana="' + dataAna + '">'
        return spanStart

    def process_sentence(self, s, numSent=1):
        """
        Process one sentence taken from response['hits']['hits'].
        """
        if '_source' not in s:
            return ''
        matchWordOffsets = self.retrieve_highlighted_words(s)
        sSource = s['_source']
        if 'text' not in sSource or len(sSource['text']) <= 0:
            return ''
        if 'words' not in sSource:
            return sSource['text']
        chars = list(sSource['text'])
        offStarts, offEnds = {}, {}
        for iWord in range(len(sSource['words'])):
            try:
                if sSource['words'][iWord]['wtype'] != 'word':
                    continue
                offStart, offEnd = sSource['words'][iWord]['off_start'], sSource['words'][iWord]['off_end']
            except KeyError:
                continue
            try:
                offStarts[offStart].add(iWord)
            except KeyError:
                offStarts[offStart] = {iWord}
            try:
                offEnds[offEnd].add(iWord)
            except KeyError:
                offEnds[offEnd] = {iWord}
        curWords = set()
        for i in range(len(chars)):
            if i not in offStarts and i not in offEnds:
                continue
            addition = ''
            if len(curWords) > 0:
                addition = '</span>'
                if i in offEnds:
                    curWords -= offEnds[i]
            newWord = False
            if i in offStarts:
                curWords |= offStarts[i]
                newWord = True
            if len(curWords) > 0 and (len(addition) > 0 or newWord):
                addition += self.build_span(sSource, numSent, curWords, matchWordOffsets)
            chars[i] = addition + chars[i]
        if len(curWords) > 0:
            chars[-1] += '</span>'
        return ''.join(chars)

    def retrieve_highlighted_words(self, sentence):
        """
        Explore the inner_hits part of the response to find the
        offsets of the words that matched the query. Search for
        word offsets recursively, so that the procedure does not
        depend excatly on the response structure.
        """
        if 'inner_hits' in sentence:
            return self.retrieve_highlighted_words(sentence['inner_hits'])
        offsets = set()
        if type(sentence) == list:
            for el in sentence:
                offsets |= self.retrieve_highlighted_words(el)
            return offsets
        elif type(sentence) == dict:
            if 'field' in sentence and sentence['field'] == 'words':
                if 'offset' in sentence:
                    offsets.add(sentence['offset'])
                return offsets
            for k, v in sentence.items():
                if type(v) in [dict, list]:
                    offsets |= self.retrieve_highlighted_words(v)
        return offsets

    def process_sent_json(self, response):
        result = {'n_occurrences': 0, 'n_sentences': 0,
                  'n_docs': 0, 'message': 'Nothing found.'}
        if 'hits' not in response or 'total' not in response['hits']:
            return result
        result['message'] = ''
        result['n_sentences'] = response['hits']['total']
        result['contexts'] = []
        for iHit in range(len(response['hits']['hits'])):
            result['contexts'].append(self.process_sentence(response['hits']['hits'][iHit], iHit))
        return result

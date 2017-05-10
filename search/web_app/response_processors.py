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

    def process_sentence(self, s, numSent=1):
        """
        Process one sentence taken from response['hits']['hits'].
        """
        if '_source' not in s:
            return ''
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
                dataAna = self.prepare_analyses(sSource['words'], curWords)
                addition += '<span class="word ' +\
                            ' '.join('w' + str(numSent) + '_' + str(n)
                                     for n in curWords) + '" data-ana="' + dataAna + '">'
            chars[i] = addition + chars[i]
        if len(curWords) > 0:
            chars[-1] += '</span>'
        return ''.join(chars)

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

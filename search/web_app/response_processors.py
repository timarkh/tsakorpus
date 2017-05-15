import json
import re
import os


class SentenceViewer:
    """
    Contains methods for turning the JSON response of ES into
    viewable html.
    """

    rxWordNo = re.compile('^w[0-9]+_([0-9]+)$')

    def __init__(self, settings_dir, search_client):
        self.settings_dir = settings_dir
        f = open(os.path.join(self.settings_dir, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.sentence_props = ['text']
        self.sc = search_client

    def build_ana_popup(self, word):
        """
        Build a string for a popup with the word and its analyses. 
        """
        popup = ''
        if 'wf' in word:
            popup += word['wf'] + '\n'
        if 'ana' in word:
            for iAna in range(len(word['ana'])):
                popup += 'Analysis #' + str(iAna + 1) + '.\n'
                popup += json.dumps(word['ana'][iAna], ensure_ascii=False, indent=2)
                popup += ' \n'
        return popup

    def prepare_analyses(self, words, indexes):
        """
        Generate viewable analyses for the words with given indexes.
        """
        result = '---------\n'
        for i in indexes:
            mWordNo = self.rxWordNo.search(i)
            if mWordNo is None:
                continue
            i = int(mWordNo.group(1))
            if i < 0 or i >= len(words):
                continue
            word = words[i]
            result += self.build_ana_popup(word)
        result = result.replace('\n', '\\n').replace('"', "'")
        return result

    def build_span(self, sentSrc, curWords, matchWordOffsets):
        dataAna = self.prepare_analyses(sentSrc['words'], curWords)

        def highlightClass(nWord):
            if nWord in matchWordOffsets:
                return ' wmatch'
            return ''

        spanStart = '<span class="word ' + \
                    ' '.join(wn + highlightClass(wn)
                             for wn in curWords) + '" data-ana="' + dataAna + '">'
        return spanStart

    def add_highlighted_offsets(self, offStarts, offEnds, text):
        """
        Find highlighted fragments in source text of the sentence
        and store their offsets in the respective lists.
        """
        indexSubtr = 0  # <em>s that appeared due to highlighting should be subtracted
        for i in range(len(text) - 4):
            if text[i] != '<':
                continue
            if text[i:i+4] == '<em>':
                try:
                    offStarts[i - indexSubtr].add('smatch')
                except KeyError:
                    offStarts[i - indexSubtr] = {'smatch'}
                indexSubtr += 4
            elif text[i:i+5] == '</em>':
                try:
                    offEnds[i - indexSubtr].add('smatch')
                except KeyError:
                    offEnds[i - indexSubtr] = {'smatch'}
                indexSubtr += 5

    def process_sentence_header(self, sentSource):
        """
        Retrieve the metadata of the document the sentence
        belongs to. Return an HTML string with this data that
        can serve as a header for the context on the output page.
        """
        result = '<span class="context_header" data-meta="">'
        docID = sentSource['doc_id']
        meta = self.sc.get_doc_by_id(docID)
        if (meta is None
                or 'hits' not in meta
                or 'hits' not in meta['hits']
                or len(meta['hits']['hits']) <= 0):
            return result + '</span>'
        meta = meta['hits']['hits'][0]
        if '_source' not in meta:
            return result + '</span>'
        meta = meta['_source']
        if 'title' in meta:
            result += '<span class="ch_title">' + meta['title'] + '</span>'
        else:
            result += '<span class="ch_title">-</span>'
        if 'author' in meta:
            result += '<span class="ch_author">' + meta['author'] + '</span>'
        if 'issue' in meta and len(meta['issue']) > 0:
            result += '<span class="ch_date">' + meta['issue'] + '</span>'
        if 'year1' in meta and 'year2' in meta:
            dateDisplayed = str(meta['year1'])
            if meta['year2'] != meta['year1']:
                dateDisplayed += '&ndash;' + str(meta['year2'])
            result += '<span class="ch_date">' + dateDisplayed + '</span>'
        dataMeta = ''
        for metaField in self.settings['viewable_meta']:
            try:
                metaValue = meta[metaField]
                dataMeta += metaField + ': ' + metaValue + '\\n'
            except KeyError:
                pass
        dataMeta = dataMeta.replace('"', '&quot;')
        if len(dataMeta) > 0:
            result = result.replace('data-meta=""', 'data-meta="' + dataMeta + '"')
        return result + '</span>'

    def process_sentence(self, s, numSent=1, getHeader=False):
        """
        Process one sentence taken from response['hits']['hits'].
        If getHeader is True, retrieve the metadata from the database.
        Return dictionary {'header': document header HTML,
                           'text': sentence HTML}.
        """
        if '_source' not in s:
            return ''
        matchWordOffsets = self.retrieve_highlighted_words(s, numSent)
        sSource = s['_source']
        if 'text' not in sSource or len(sSource['text']) <= 0:
            return ''

        header = {}
        if getHeader:
            header = self.process_sentence_header(sSource)
        if 'highlight' in s and 'text' in s['highlight']:
            highlightedText = s['highlight']['text']
            if type(highlightedText) == list:
                if len(highlightedText) > 0:
                    highlightedText = highlightedText[0]
                else:
                    highlightedText = sSource['text']
        else:
            highlightedText = sSource['text']
        if 'words' not in sSource:
            return highlightedText
        chars = list(sSource['text'])
        offStarts, offEnds = {}, {}
        self.add_highlighted_offsets(offStarts, offEnds, highlightedText)
        for iWord in range(len(sSource['words'])):
            try:
                if sSource['words'][iWord]['wtype'] != 'word':
                    continue
                offStart, offEnd = sSource['words'][iWord]['off_start'], sSource['words'][iWord]['off_end']
            except KeyError:
                continue
            wn = 'w' + str(numSent) + '_' + str(iWord)
            try:
                offStarts[offStart].add(wn)
            except KeyError:
                offStarts[offStart] = {wn}
            try:
                offEnds[offEnd].add(wn)
            except KeyError:
                offEnds[offEnd] = {wn}
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
                addition += self.build_span(sSource, curWords, matchWordOffsets)
            chars[i] = addition + chars[i]
        if len(curWords) > 0:
            chars[-1] += '</span>'
        return {'header': header, 'text': ''.join(chars)}

    def process_word(self, w):
        """
        Process one word taken from response['hits']['hits'].
        """
        if '_source' not in w:
            return ''
        wSource = w['_source']
        word = '<tr><td><span class="word" data-ana="' +\
               self.build_ana_popup(wSource).replace('\n', '\\n').replace('"', "'") +\
               '">' + wSource['wf'] +\
               '</span></td><td>' + str(wSource['freq']) +\
               '</td><td>' + str(len(wSource['sids'])) +\
               '</td><td><span class="search_w" data-wf="' +\
               wSource['wf'] + '">&gt;&gt; GO!</td></tr>'
        return word

    def retrieve_highlighted_words(self, sentence, numSent):
        """
        Explore the inner_hits part of the response to find the
        offsets of the words that matched the word-level query.
        Search for word offsets recursively, so that the procedure
        does not depend excatly on the response structure.
        """
        if 'inner_hits' in sentence:
            return self.retrieve_highlighted_words(sentence['inner_hits'], numSent)
        offsets = set()
        if type(sentence) == list:
            for el in sentence:
                offsets |= self.retrieve_highlighted_words(el, numSent)
            return offsets
        elif type(sentence) == dict:
            if 'field' in sentence and sentence['field'] == 'words':
                if 'offset' in sentence:
                    offsets.add('w' + str(numSent) + '_' + str(sentence['offset']))
                return offsets
            for k, v in sentence.items():
                if type(v) in [dict, list]:
                    offsets |= self.retrieve_highlighted_words(v, numSent)
        return offsets

    def process_sent_json(self, response):
        result = {'n_occurrences': 0, 'n_sentences': 0,
                  'n_docs': 0, 'message': 'Nothing found.'}
        if 'hits' not in response or 'total' not in response['hits']:
            return result
        result['message'] = ''
        result['n_sentences'] = response['hits']['total']
        result['contexts'] = []
        if 'aggregations' in response and 'agg_ndocs' in response['aggregations']:
            result['n_docs'] = response['aggregations']['agg_ndocs']['value']
        for iHit in range(len(response['hits']['hits'])):
            result['contexts'].append(self.process_sentence(response['hits']['hits'][iHit],
                                                            numSent=iHit,
                                                            getHeader=True))
        return result

    def process_word_json(self, response):
        result = {'n_occurrences': 0, 'n_sentences': 0, 'message': 'Nothing found.'}
        if 'hits' not in response or 'total' not in response['hits']:
            return result
        result['message'] = ''
        result['n_occurrences'] = response['hits']['total']
        result['words'] = []
        for iHit in range(len(response['hits']['hits'])):
            result['words'].append(self.process_word(response['hits']['hits'][iHit]))
        return result

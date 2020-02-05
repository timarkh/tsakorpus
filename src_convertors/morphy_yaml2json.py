import os
import re
import copy
import html
import json
from lxml import etree
from txt2json import Txt2JSON


class Morphy_YAML2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from texts
    annotated in the Morphy interface and stored in a YAML-like format,
    and a csv with metadata.
    """

    rxObjectHeaders = re.compile('^-(word|part|line|punc|page|fragment|document|year):\\s+(.*?)\\s*$', flags=re.DOTALL)
    rxAllHeaders = re.compile('^ *(-?)([^:]+):\\s+(.*?)\\s*$', flags=re.DOTALL)
    rxSpaces = re.compile('^ *$')
    rxSuperscripts = re.compile('\\{\\{([0i_^])\\}\\}')
    dictSuperscripts = {'_': 'sub', '^': 'sup', 'i': 'i'}
    wordFields = {'wf', 'wtype', 'Superscripts'}  # keys that should stay in the word dictionary,
                                                  # rather than go to the analyses
    punc2delete = ['||', '|']

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.rxPuncSpaceBefore = re.compile(self.corpusSettings['punc_space_before'])
        self.rxPuncSpaceAfter = re.compile(self.corpusSettings['punc_space_after'])
        self.srcExt = 'yaml'
        self.pID = 0        # id of last aligned segment

    def yaml2dict(self, yamlObj):
        """
        Transform a YAML object into a dictionary
        """
        dictObj = {}
        objStack = [dictObj]
        prevIndent = 1
        for line in yamlObj:
            m = self.rxAllHeaders.search(line)
            if m is None:
                continue
            curIndent = 0
            for c in line:
                if c == ' ':
                    curIndent += 1
                else:
                    break
            if curIndent < prevIndent:
                prevIndent = curIndent
                objStack.pop()
            if m.group(2) not in objStack[-1]:
                objStack[-1][m.group(2)] = []
            if m.group(1) == '-':
                prevIndent += 1
                newLevelDict = {}
                objStack[-1][m.group(2)].append(newLevelDict)
                objStack.append(newLevelDict)
            else:
                objStack[-1][m.group(2)].append(m.group(3))
        return dictObj

    def yaml_iterator(self, yamlFile):
        """
        Iterate over the objects of an input file.
        """
        curObject = []
        sCurPage = ''
        sCurWord = ''
        sCurType = ''
        sCurLine = ''
        iCurLine = 0
        bTextStarted = False
        for line in yamlFile:
            if line.startswith('#'):
                continue
            if line[0] == '-':  # a part or a fragment, for instance
                # yield the current object, flush the data, and continue recording (with curWord empty)
                if bTextStarted:
                    yield {'page': sCurPage, 'line': sCurLine,
                           'word': sCurWord, 'type': sCurType, 'object': self.yaml2dict(curObject)}
                sCurWord = ''
                sCurType = ''
                sCurLine = ''
                curObject = []
                bTextStarted = True
            m = self.rxObjectHeaders.search(line)
            if m is not None:
                if m.group(1) in ['word', 'punc', 'fragment', 'part', 'year']:
                    sCurWord = m.group(2)
                    sCurType = m.group(1)
                elif m.group(1) == 'line':
                    sCurType = 'line'
                    sCurWord = m.group(2)
                    iCurLine += 1
                    if len(sCurWord) > 0:
                        sCurLine = sCurWord
                    else:
                        sCurLine = str(iCurLine)
                elif m.group(1) == 'page':
                    sCurType = 'page'
                    sNewPage = re.sub(':.*', '', m.group(2))
                    if sNewPage != sCurPage:
                        sCurPage = sNewPage
                        sCurWord = sCurPage
                        iCurLine = 0
                        sCurLine = ''
                elif m.group(1) == 'document':
                    sCurType = 'document'
                    sCurPage = m.group(2)
                    iCurLine = 0
                    sCurLine = ''
            elif line[0] == ' ':
                curObject.append(line)
        if bTextStarted:
            yield {'page': sCurPage, 'line': sCurLine,
                   'word': sCurWord, 'type': sCurType, 'object': self.yaml2dict(curObject)}
        yamlFile.close()

    def process_superscripts(self, text):
        """
        Turn the value of the "Superscripts" field into an HTML string with
        text styles.
        {{i}}...{{0}} -> <i>...</i>
        {{^}}...{{0}} -> <sup>...</sup>
        {{_}}...{{0}} -> <sub>...</sub>
        Return the HTML string and a list of tuples (start offset, end offset, HTML tag).
        """
        newValue = ''
        styleStack = []
        iChar = 0
        iMinusOffset = 0
        offsetStack = []
        offsets = []
        text = html.escape(text)
        while iChar < len(text):
            if text[iChar] != '{' or iChar > len(text) - 5:
                newValue += text[iChar]
                iChar += 1
            else:
                m = self.rxSuperscripts.search(text[iChar:])
                if m is None:
                    newValue += text[iChar]
                    iChar += 1
                    continue
                iChar += 5
                iMinusOffset += 5
                if m.group(1) == '0':
                    if len(styleStack) <= 0:
                        continue
                    newValue += '</' + styleStack[-1] + '>'
                    styleStack.pop()
                    offsets[offsetStack[-1]][1] = iChar - iMinusOffset
                    offsetStack.pop()
                else:
                    styleStack.append(self.dictSuperscripts[m.group(1)])
                    newValue += '<' + styleStack[-1] + '>'
                    offsets.append([iChar - iMinusOffset, iChar - iMinusOffset, styleStack[-1]])
                    offsetStack.append(len(offsets) - 1)
        for s in styleStack[::-1]:
            # Potentially unclosed styles
            newValue += '</' + s + '>'
        offsets = [offset for offset in offsets if offset[1] > offset[0]]
        return newValue, offsets

    def make_word(self, obj):
        """
        Transform a dictionary obtained from the YAML iterator
        into a word or a punctuation mark in the output format.
        If use_transcription is true, return a list of words,
        each made from a single segment represented by an analysis.
        """
        wordJson = {'wtype': obj['type'], 'wf': obj['word']}
        if wordJson['wtype'] == 'punc':
            wordJson['wtype'] = 'punct'
        commonAna = {}
        styleOffsets = []
        transcr = ''
        transcrFromSegments = ''
        for k, v in obj['object'].items():
            newKey = k
            if k in self.corpusSettings['replace_fields']:
                newKey = self.corpusSettings['replace_fields'][k]
            elif k == 'Superscripts' and len(v) == 1:
                if self.rxSuperscripts.sub('', v[0]) != wordJson['wf']:
                    print('Wrong superscripts: ' + wordJson['wf'] + ' (' + obj['page'] + ')')
                    continue
                newKey = 'wf_display'
                v[0], styleOffsets = self.process_superscripts(v[0])
            if k in self.corpusSettings['exclude_fields']:
                continue
            if all(type(value) != dict for value in v):
                if len(v) == 1:
                    curValue = v[0]
                    if k == 'Transcription':
                        transcr = curValue
                elif len(v) > 1:
                    curValue = copy.deepcopy(v)
                if k in self.wordFields:
                    # Move all analysis fields to individual analyses
                    wordJson[newKey] = curValue
                else:
                    commonAna[newKey] = curValue
            elif k == 'ana' and all(type(value) == dict for value in v):
                analyses = []
                for ana in v:
                    curAna = {}
                    gramm = ''
                    for anaKey in ana:
                        newKey = anaKey
                        if anaKey in self.corpusSettings['replace_fields']:
                            newKey = self.corpusSettings['replace_fields'][anaKey]
                        if anaKey in self.corpusSettings['exclude_fields']:
                            continue
                        elif anaKey in ['grdic', 'gramm']:
                            if len(gramm) > 0 and len(ana[anaKey]) > 0:
                                gramm += ','
                            gramm += ','.join(ana[anaKey])
                            continue
                        elif len(ana[anaKey]) == 1:
                            curAna[newKey] = ana[anaKey][0]
                            if newKey == 'segment':
                                if len(transcrFromSegments) > 0:
                                    transcrFromSegments += '='
                                transcrFromSegments += ana[anaKey][0]
                        elif len(ana[anaKey]) > 1:
                            curAna[newKey] = copy.deepcopy(ana[anaKey])
                    if len(curAna) > 0:
                        grammJSON = self.tp.parser.transform_gramm_str(gramm, lang=self.corpusSettings['languages'][0])
                        curAna.update(grammJSON)
                        analyses.append(curAna)
                if len(analyses) > 0:
                    wordJson[k] = analyses
            if len(commonAna) > 0:
                if 'ana' in wordJson and len(wordJson['ana']) > 0:
                    for ana in wordJson['ana']:
                        ana.update(commonAna)
                else:
                    wordJson['ana'] = [commonAna]
        if 'ana' in wordJson and len(wordJson['ana']) > 0 and any ('gr.pos' in ana for ana in wordJson['ana']):
            if transcrFromSegments != transcr:
                print('Wrong transcription or segments: ' + transcr + ' != ' + transcrFromSegments
                      + ' (' + obj['page'] + ')')
        return wordJson, styleOffsets

    def correct_para_alignments(self, s):
        """
        In preliminary para_alignments, the offsets are indicated in words.
        Write offsets in characters instead.
        Do not return anything.
        """
        if 'para_alignment' not in s or 'words' not in s:
            return
        for p in s['para_alignment']:
            if 'words' not in p or len(p['words']) <= 0:
                continue
            minWord = min(p['words'])
            maxWord = max(p['words'])
            if minWord < 0 or maxWord >= len(s['words']):
                continue
            p['off_start'] = s['words'][minWord]['off_start']
            p['off_end'] = s['words'][maxWord]['off_end']
            del p['words']

    def concatenate_words(self, s, styleOffsets):
        """
        Take a sentence dictionary that contains a list of word objects
        and concatenate the tokens into a text. Add the 'text' key to
        the sentence and offsets to the words. Add style offsets as
        style_span items to the 'words' list.
        """
        s['text'] = ''
        styleSpans = []
        for iWord in range(len(s['words'])):
            word = s['words'][iWord]
            if (word['wtype'] == 'punct'
                and self.rxPuncSpaceBefore.search(word['wf']) is not None
                and len(s['text']) > 0
                and s['text'][-1] != ' '):
                    s['text'] += ' '
            if word['wtype'] != 'style_span':
                word['off_start'] = len(s['text'])
                word['off_end'] = len(s['text']) + len(word['wf'])
                s['text'] += word['wf']
                if iWord < len(styleOffsets):
                    for offset in styleOffsets[iWord]:
                        styleSpans.append({'span_class': offset[2],
                                           'off_start': word['off_start'] + offset[0],
                                           'off_end': word['off_start'] + offset[1]})
            if (word['wtype'] == 'punct'
                and (self.rxPuncSpaceAfter.search(word['wf']) is not None
                     or len(word['wf']) == 0)
                and len(s['text']) > 0
                and s['text'][-1] != ' '):
                    s['text'] += ' '
            elif (word['wtype'] == 'word'
                  and iWord < len(s['words']) - 1
                  and s['words'][iWord + 1]['wtype'] == 'word'):
                    s['text'] += ' '
        s['text'] = s['text'].rstrip(' ')
        if len(styleSpans) > 0:
            s['style_spans'] = styleSpans
        self.correct_para_alignments(s)

    def get_documents(self, fIn, metadata):
        """
        Iterate over documents in an input file. If the file is not
        split into documents, return the whole file contents as one
        document.
        """
        textJSON = {'meta': metadata, 'sentences': []}
        curSent = {'words': []}
        styleOffsets = []   # for each word, a list of tuples (start, end, style tag)
        for obj in self.yaml_iterator(fIn):
            if obj['type'] == 'document':
                if len(curSent['words']) > 0:
                    self.concatenate_words(curSent, styleOffsets)
                    styleOffsets = []
                    textJSON['sentences'].append(curSent)
                    curSent = {'words': []}
                if len(textJSON['sentences']) > 0 and not self.exclude_text(textJSON['meta']):
                    yield textJSON
                textJSON = {'meta': metadata, 'sentences': []}
                textJSON['meta']['title'] = obj['page']
                for metafield in obj['object']:
                    newKey = metafield
                    if metafield in self.corpusSettings['replace_fields']:
                        newKey = self.corpusSettings['replace_fields'][metafield]
                    textJSON['meta'][newKey] = obj['object'][metafield]
                    if len(textJSON['meta'][newKey]) == 1:
                        # It is a list by default
                        textJSON['meta'][newKey] = textJSON['meta'][newKey][0]
            elif obj['type'] == 'line':
                if len(curSent['words']) > 0:
                    curSent['words'].append({'wtype': 'punct', 'wf': '\n'})
                    self.concatenate_words(curSent, styleOffsets)
                    styleOffsets = []
                    textJSON['sentences'].append(curSent)
                curSent = {'words': [],
                           'meta': {'line': obj['line'], 'page': obj['page']}}
                if len(obj['word'].strip('[] ')) > 0:
                    curSent['words'].append({'wtype': 'punct',
                                             'wf': '[' + obj['word'].strip('[]') + ']'})
                    styleOffsets.append([])
            elif obj['type'] == 'page':
                if len(curSent['words']) > 0:
                    curSent['words'].append({'wtype': 'punct', 'wf': '\n'})
                    self.concatenate_words(curSent, styleOffsets)
                    styleOffsets = []
                    textJSON['sentences'].append(curSent)
                if len(obj['word'].strip('[] ')) > 0:
                    curSent = {'words': [],
                               'meta': {'page': obj['page']}}
                    curSent['words'].append({'wtype': 'punct',
                                             'wf': '[' + obj['word'].strip('[]') + ']'})
                    self.concatenate_words(curSent, [])
                    textJSON['sentences'].append(curSent)
                curSent = {'words': []}
                styleOffsets = []
            elif obj['type'] in ['word', 'punc']:
                curWord, curStyleOffsets = self.make_word(obj)
                styleOffsets.append(curStyleOffsets)
                curSent['words'].append(curWord)
        if len(curSent['words']) > 0:
            self.concatenate_words(curSent, styleOffsets)
            textJSON['sentences'].append(curSent)
        if len(textJSON['sentences']) > 0 and not self.exclude_text(textJSON['meta']):
            yield textJSON
        return

    def get_documents_parallel(self, fIn, metadata):
        """
        Iterate over documents in an input file. If the file is not
        split into documents, return the whole file contents as one
        document. For each word, store both its transliteration (the
        main value) and transcription (value of the Segment fields)
        in separate sentences. Align different versions of the word.
        """
        textJSON = {'meta': metadata, 'sentences': []}
        curSentTranslit = {'words': [], 'lang': 1, 'para_alignment': []}
        curSentTranscr = {'words': [], 'lang': 0, 'para_alignment': []}
        styleOffsets = []   # for each word in transliteration, a list of tuples (start, end, style tag)
        for obj in self.yaml_iterator(fIn):
            if obj['type'] == 'document':
                if len(curSentTranslit['words']) > 0:
                    self.concatenate_words(curSentTranslit, styleOffsets)
                    self.concatenate_words(curSentTranscr, [])
                    styleOffsets = []
                    textJSON['sentences'].append(curSentTranslit)
                    textJSON['sentences'].append(curSentTranscr)
                    curSentTranslit = {'words': [], 'lang': 1, 'para_alignment': []}
                    curSentTranscr = {'words': [], 'lang': 0, 'para_alignment': []}
                if len(textJSON['sentences']) > 0 and not self.exclude_text(textJSON['meta']):
                    yield textJSON
                textJSON = {'meta': metadata, 'sentences': []}
                textJSON['meta']['title'] = obj['page']
                for metafield in obj['object']:
                    newKey = metafield
                    if metafield in self.corpusSettings['replace_fields']:
                        newKey = self.corpusSettings['replace_fields'][metafield]
                    textJSON['meta'][newKey] = obj['object'][metafield]
                    if len(textJSON['meta'][newKey]) == 1:
                        # It is a list by default
                        textJSON['meta'][newKey] = textJSON['meta'][newKey][0]
            elif obj['type'] == 'line':
                if len(curSentTranslit['words']) > 0:
                    curSentTranslit['words'].append({'wtype': 'punct', 'wf': '\n'})
                    curSentTranscr['words'].append({'wtype': 'punct', 'wf': '\n'})
                    self.concatenate_words(curSentTranslit, styleOffsets)
                    self.concatenate_words(curSentTranscr, [])
                    styleOffsets = []
                    textJSON['sentences'].append(curSentTranslit)
                    textJSON['sentences'].append(curSentTranscr)
                curSentTranslit = {'words': [],
                                   'meta': {'line': obj['line'], 'page': obj['page']},
                                   'lang': 1,
                                   'para_alignment': []}
                curSentTranscr = {'words': [],
                                  'meta': {'line': obj['line'], 'page': obj['page']},
                                  'lang': 0,
                                  'para_alignment': []}
                if len(obj['word'].strip('[] ')) > 0:
                    curSentTranslit['words'].append({'wtype': 'punct',
                                                     'wf': '[' + obj['word'].strip('[]') + ']'})
                    styleOffsets.append([])
                    curSentTranscr['words'].append({'wtype': 'punct',
                                                    'wf': '[' + obj['word'].strip('[]') + ']'})
            elif obj['type'] == 'page':
                if len(curSentTranslit['words']) > 0:
                    curSentTranslit['words'].append({'wtype': 'punct', 'wf': '\n'})
                    curSentTranscr['words'].append({'wtype': 'punct', 'wf': '\n'})
                    self.concatenate_words(curSentTranslit, styleOffsets)
                    self.concatenate_words(curSentTranscr, [])
                    styleOffsets = []
                    textJSON['sentences'].append(curSentTranslit)
                    textJSON['sentences'].append(curSentTranscr)
                if len(obj['word'].strip('[] ')) > 0:
                    self.pID += 1
                    curSentTranslit = {'words': [],
                                       'meta': {'line': obj['line'], 'page': obj['page']},
                                       'lang': 1,
                                       'para_alignment': [{'para_id': self.pID,
                                                           'start_offset': 0,
                                                           'end_offset': len(obj['word'].strip('[]')) + 2}]}
                    curSentTranscr = {'words': [],
                                      'meta': {'line': obj['line'], 'page': obj['page']},
                                      'lang': 0,
                                      'para_alignment': [{'para_id': self.pID,
                                                          'start_offset': 0,
                                                          'end_offset': len(obj['word'].strip('[]')) + 2}]}
                    curSentTranslit['words'].append({'wtype': 'punct',
                                                     'wf': '[' + obj['word'].strip('[]') + ']'})
                    curSentTranscr['words'].append({'wtype': 'punct',
                                                    'wf': '[' + obj['word'].strip('[]') + ']'})
                    self.concatenate_words(curSentTranslit, [])
                    self.concatenate_words(curSentTranscr, [])
                    textJSON['sentences'].append(curSentTranslit)
                    textJSON['sentences'].append(curSentTranscr)
                curSentTranslit = {'words': [], 'lang': 1, 'para_alignment': []}
                curSentTranscr = {'words': [], 'lang': 0, 'para_alignment': []}
                styleOffsets = []
            elif obj['type'] in ['word', 'punc']:
                if len(obj['word']) <= 0:
                    continue
                curWordTranslit, curStyleOffsets = self.make_word(obj)
                styleOffsets.append(curStyleOffsets)
                curWordsTranscr = []
                if 'ana' not in curWordTranslit or len(curWordTranslit['ana']) <= 0:
                    if obj['type'] == 'word':
                        curWordsTranscr.append({'wf': '!!!', 'wtype': 'word'})
                    elif curWordTranslit['wf'] in self.punc2delete:  # line breaks, for example
                        curWordsTranscr.append({'wf': ' ', 'wtype': 'punct'})
                    else:
                        curWordsTranscr.append(copy.deepcopy(curWordTranslit))
                else:
                    logogram = ''
                    transcription = ''
                    firstAna = True
                    for ana in curWordTranslit['ana']:
                        if not firstAna:
                            curWordsTranscr.append({'wf': '=', 'wtype': 'punct'})  # clitics
                        newSegment = {'wtype': 'word', 'wf': '!!!', 'ana': [ana]}
                        if 'segment' in ana:
                            newSegment['wf'] = ana['segment']
                            del ana['segment']
                        if 'logogram' in ana:
                            logogram = ana['logogram']
                            del ana['logogram']
                        if 'transcription' in ana:
                            transcription = ana['transcription']
                            del ana['transcription']
                        curWordsTranscr.append(newSegment)
                        firstAna = False
                    curWordTranslit['ana'] = []
                    if len(logogram) > 0 or len(transcription) > 0:
                        curWordTranslit['ana'].append({})
                        if len(logogram) > 0:
                            curWordTranslit['ana'][0]['logogram'] = logogram
                        if len(transcription) > 0:
                            curWordTranslit['ana'][0]['transcription'] = transcription
                self.pID += 1
                curSentTranslit['words'].append(curWordTranslit)
                paraAlignmentTranslit = {'para_id': self.pID, 'words': [len(curSentTranslit['words']) - 1]}
                paraAlignmentTranscr = {'para_id': self.pID, 'words': []}
                for wordTranscr in curWordsTranscr:
                    curSentTranscr['words'].append(wordTranscr)
                    paraAlignmentTranscr['words'].append(len(curSentTranscr['words']) - 1)
                curSentTranslit['para_alignment'].append(paraAlignmentTranslit)
                curSentTranscr['para_alignment'].append(paraAlignmentTranscr)
        if len(curSentTranslit['words']) > 0:
            self.concatenate_words(curSentTranslit, styleOffsets)
            self.concatenate_words(curSentTranscr, [])
            textJSON['sentences'].append(curSentTranslit)
            textJSON['sentences'].append(curSentTranscr)
        if len(textJSON['sentences']) > 0 and not self.exclude_text(textJSON['meta']):
            yield textJSON
        return

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        nTokens, nWords, nAnalyzed = 0, 0, 0
        fIn = open(fnameSrc, 'r', encoding='utf-8-sig')
        iDocument = 0
        if 'parallel' not in self.corpusSettings or not self.corpusSettings['parallel']:
            docGenerator = self.get_documents(fIn, curMeta)
        else:
            docGenerator = self.get_documents_parallel(fIn, curMeta)
        for textJSON in docGenerator:
            curFnameTarget = self.rxStripExt.sub('_' + str(iDocument) + '.json', fnameTarget)
            iDocument += 1
            if curFnameTarget == fnameSrc or curFnameTarget == fnameTarget:
                continue
            if 'parallel' in self.corpusSettings and self.corpusSettings['parallel']:
                # There two parallel tiers: transcription and transliteration
                textJSON['sentences'].sort(key=lambda s: s['lang'])
                for i in range(len(textJSON['sentences']) - 1):
                    if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i+1]['lang']:
                        textJSON['sentences'][i]['last'] = True
            textJSON['sentences'][len(textJSON['sentences']) - 1]['last'] = True
            for s in textJSON['sentences']:
                for word in s['words']:
                    nTokens += 1
                    if word['wtype'] == 'word':
                        nWords += 1
                        if 'ana' in word and len(word['ana']) > 0:
                            nAnalyzed += 1
            self.tp.splitter.recalculate_offsets(textJSON['sentences'])
            self.tp.splitter.add_next_word_id(textJSON['sentences'])
            self.write_output(curFnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed


if __name__ == '__main__':
    x2j = Morphy_YAML2JSON()
    x2j.process_corpus()

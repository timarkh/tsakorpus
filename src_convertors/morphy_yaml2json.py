import os
import re
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

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
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
        iCurLine = 0
        for line in yamlFile:
            if line.startswith('#'):
                continue
            if line[0] == '-':  # a part or a fragment, for instance
                # yield the current object, flush the data, and continue recording (with curWord empty)
                if len(curObject) > 0:
                    yield {'page': sCurPage, 'line': iCurLine,
                           'word': sCurWord, 'type': sCurType, 'object': self.yaml2dict(curObject)}
                sCurWord = ''
                sCurType = ''
                curObject = []
            m = self.rxObjectHeaders.search(line)
            if m is not None:
                if m.group(1) in ['word', 'punc', 'fragment', 'part', 'year']:
                    sCurWord = m.group(2)
                    sCurType = m.group(1)
                elif m.group(1) == 'line':
                    iCurLine += 1
                    sCurType = 'line'
                    sCurWord = m.group(2)
                elif m.group(1) == 'page':
                    sCurType = 'page'
                    sNewPage = re.sub(':.*', '', m.group(2))
                    if sNewPage != sCurPage:
                        sCurPage = sNewPage
                        iCurLine = 0
                elif m.group(1) == 'document':
                    sCurType = 'document'
                    sCurPage = m.group(2)
                    iCurLine = 0
            elif line[0] == ' ':
                curObject.append(line)
        if len(curObject) > 0:
            yield {'page': sCurPage, 'line': iCurLine,
                   'word': sCurWord, 'type': sCurType, 'object': self.yaml2dict(curObject)}
        yamlFile.close()

    def make_word(self, obj):
        """
        Transform a dictionary obtained from the YAML iterator
        into a word or a punctuation mark in the output format.
        """
        wordJson = {'wtype': obj['type'], 'wf': obj['word']}
        for k, v in obj['object'].items():
            if all(type(value) != dict for value in v):
                if len(v) == 1:
                    wordJson[k] = v[0]
                elif len(v) > 1:
                    wordJson[k] = v
        return wordJson

    def get_documents(self, fIn, metadata):
        """
        Iterate over documents in an input file. If the file is not
        split into documents, return the whole file contents as one
        document.
        """
        textJSON = {'meta': metadata, 'sentences': []}
        curSent = {'words': []}
        for obj in self.yaml_iterator(fIn):
            if obj['type'] == 'document':
                if len(textJSON['sentences']) > 0:
                    yield textJSON
                textJSON = {'meta': metadata, 'sentences': []}
                for metafield in obj['object']:
                    textJSON['meta']['title'] = obj['page']
                    textJSON['meta'][metafield] = obj['object'][metafield]
                    if len(textJSON['meta'][metafield]) == 1:
                        # It is a list by default
                        textJSON['meta'][metafield] = textJSON['meta'][metafield][0]
            elif obj['type'] == 'line':
                if len(curSent['words']) > 0:
                    curSent['words'].append({'wtype': 'punc', 'wf': '\n'})
                    textJSON['sentences'].append(curSent)
                curSent = {'words': [{'wtype': 'punc',
                                      'wf': '[' + obj['word'].strip('[]') + ']'}],
                           'meta': {'line': obj['curLine'], 'page': obj['curPage']}}
            elif obj['type'] == 'page':
                if len(curSent['words']) > 0:
                    curSent['words'].append({'wtype': 'punc', 'wf': '\n'})
                    textJSON['sentences'].append(curSent)
                curSent = {'words': [{'wtype': 'punc',
                                      'wf': '[' + obj['word'].strip('[]') + ']'}],
                           'meta': {'page': obj['curPage']}}
                textJSON['sentences'].append(curSent)
                curSent = {'words': []}
            elif obj['type'] in ['word', 'punc']:
                curSent['words'].append(self.make_word(obj))
        if len(curSent['words']) > 0:
            textJSON['sentences'].append(curSent)
        if len(textJSON['sentences']) > 0:
            yield textJSON
        return

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        nTokens, nWords, nAnalyzed = 0, 0, 0
        fIn = open(fnameSrc, 'r', encoding='utf-8-sig')
        iDocument = 0
        for textJSON in self.get_documents(fIn, curMeta):
            curFnameTarget = self.rxStripExt.sub('_' + str(iDocument) + '.json', fnameTarget)
            if curFnameTarget == fnameSrc or curFnameTarget == fnameTarget:
                continue
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

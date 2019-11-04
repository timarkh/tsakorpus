import os
import re
import html
import json
import itertools
from lxml import etree
from txt2json import Txt2JSON
from media_operations import MediaCutter


EAF_TIME_MULTIPLIER = 1000  # time stamps are in milliseconds


class Eaf2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    ELAN aligned files, a csv with metadata and a list with parsed
    word forms.
    """

    mediaExtensions = {'.wav', '.mp3', '.mp4', '.avi'}
    rxSpaces = re.compile('[ \t]+')
    rxLetters = re.compile('\w+')

    def __init__(self, settingsDir='conf'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.speakerMeta = self.load_speaker_meta()
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'eaf'
        self.tlis = {}      # time labels
        self.pID = 0        # id of last aligned segment
        self.glosses = set()
        self.participants = {}     # main tier ID -> participant ID
        self.segmentTree = {}      # aID -> (contents, parent aID, tli1, tli2)
        self.segmentChildren = {}  # (aID, child tier type) -> [child aID]

    def load_speaker_meta(self):
        speakerMeta = {}
        if 'speaker_meta_filename' not in self.corpusSettings:
            return speakerMeta
        try:
            f = open(os.path.join(self.corpusSettings['corpus_dir'], self.corpusSettings['speaker_meta_filename']),
                     'r', encoding='utf-8-sig')
            speakerMeta = json.loads(f.read())
            f.close()
        except FileNotFoundError:
            print('The speaker metadata file not found.')
        return speakerMeta

    def get_tlis(self, srcTree):
        """
        Retrieve and return all time labels from the XML tree.
        """
        tlis = {}
        iTli = 0
        for tli in srcTree.xpath('/ANNOTATION_DOCUMENT/TIME_ORDER/TIME_SLOT'):
            timeValue = ''
            if 'TIME_VALUE' in tli.attrib:
                timeValue = tli.attrib['TIME_VALUE']
            tlis[tli.attrib['TIME_SLOT_ID']] = {'n': iTli, 'time': timeValue}
            iTli += 1
        return tlis

    def traverse_tree(self, srcTree, callback):
        """
        Iterate over all tiers in the XML tree and call the callback function
        for each of them.
        """
        for tierNode in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER'):
            if 'TIER_ID' not in tierNode.attrib:
                continue
            callback(tierNode)

    def cb_build_segment_tree(self, tierNode):
        tierType = ''  # analysis tiers: word/POS/gramm/gloss etc.
        if 'analysis_tiers' in self.corpusSettings:
            for k, v in self.corpusSettings['analysis_tiers'].items():
                if not k.startswith('^'):
                    k = '^' + k
                if not k.endswith('$'):
                    k += '$'
                try:
                    rxTierID = re.compile(k)
                    if (rxTierID.search(tierNode.attrib['TIER_ID']) is not None
                        or rxTierID.search(tierNode.attrib['LINGUISTIC_TYPE_REF']) is not None):
                        tierType = v
                        break
                except:
                    print('Except')
        for segNode in tierNode.xpath('ANNOTATION/REF_ANNOTATION | ANNOTATION/ALIGNABLE_ANNOTATION'):
            if 'ANNOTATION_ID' not in segNode.attrib:
                continue
            aID = segNode.attrib['ANNOTATION_ID']
            try:
                segContents = segNode.xpath('ANNOTATION_VALUE')[0].text.strip()
            except AttributeError:
                segContents = ''
            try:
                segParent = segNode.attrib['ANNOTATION_REF']
            except KeyError:
                segParent = None
            tli1, tli2 = None, None
            if 'TIME_SLOT_REF1' in segNode.attrib:
                tli1 = segNode.attrib['TIME_SLOT_REF1']
            elif segParent in self.segmentTree and self.segmentTree[segParent][2] is not None:
                tli1 = self.segmentTree[segParent][2]
            if 'TIME_SLOT_REF2' in segNode.attrib:
                tli2 = segNode.attrib['TIME_SLOT_REF2']
            elif segParent in self.segmentTree and self.segmentTree[segParent][3] is not None:
                tli2 = self.segmentTree[segParent][3]
            self.segmentTree[aID] = (segContents, segParent, tli1, tli2)
            if segParent is None:
                continue
            if len(tierType) > 0:
                try:
                    self.segmentChildren[(segParent, tierType)].append(aID)
                except KeyError:
                    self.segmentChildren[(segParent, tierType)] = [aID]

    def build_segment_tree(self, srcTree):
        """
        Read the entire XML tree and save all segment data (contents, links to
        the parents and timestamps, if any).
        """
        self.segmentTree = {}
        self.segmentChildren = {}
        self.traverse_tree(srcTree, self.cb_build_segment_tree)

    def fragmentize_src_alignment(self, alignment):
        """
        Find corresponding media file fragment and transform a JSON
        dictionary with the information about the alignment.
        """
        fileName, fileExt = os.path.splitext(alignment['src'].lower())
        if fileExt not in self.mediaExtensions:
            return
        ts1 = alignment['off_start_src']
        ts2 = alignment['off_end_src']
        if len(ts1) <= 0 or len(ts2) <= 0:
            return
        ts1frag, ts2frag, srcFileFrag = self.mc.get_media_name(alignment['src'],
                                                               float(ts1) / EAF_TIME_MULTIPLIER,
                                                               float(ts2) / EAF_TIME_MULTIPLIER)
        alignment['src'] = srcFileFrag
        alignment['off_start_src'] = str(ts1frag)
        alignment['off_end_src'] = str(ts2frag)

    def add_src_alignment(self, sent, tli1, tli2, srcFile):
        """
        Add the alignment of the sentence with the sound/video. If
        word-level time data is available, align words, otherwise
        align the whole sentence.
        """
        sentAlignments = []
        ts1 = self.tlis[tli1]['time']
        ts2 = self.tlis[tli2]['time']
        sentAlignments.append({'off_start_src': ts1,
                               'off_end_src': ts2,
                               'true_off_start_src': float(ts1) / EAF_TIME_MULTIPLIER,
                               'off_start_sent': 0,
                               'off_end_sent': len(sent['text']),
                               'mtype': 'audio',
                               'src_id': ts1 + '_' + ts2,
                               'src': srcFile})
        for alignment in sentAlignments:
            self.fragmentize_src_alignment(alignment)
        sent['src_alignment'] = sentAlignments

    def add_punc(self, text, startOffset):
        """
        Make one or several punctuation tokens out of the text.
        """
        tokens = []
        curToken = {'wf': '', 'off_start': startOffset, 'off_end': startOffset, 'wtype': 'punc'}
        for i in range(len(text)):
            if self.rxSpaces.search(text[i]) is not None:
                if len(curToken['wf']) > 0:
                    curToken['off_end'] = startOffset + i
                    tokens.append(curToken)
                    curToken = {'wf': '', 'off_start': startOffset + i, 'off_end': startOffset + i, 'wtype': 'punc'}
            else:
                curToken['wf'] += text[i]
        if len(curToken['wf']) > 0:
            curToken['off_end'] = startOffset + len(text)
            tokens.append(curToken)
        return tokens

    def retrieve_analyses(self, aID, lang='', topLevel=True):
        """
        Compile list of analyses retrieved from the relevant tiers of an analyzed
        EAF file associated with the token identified by aID.
        topLevel == True iff the function was called by a token processor,
        rather than by the same function recursively. This is needed because
        certain wrap-up operations should be performed only on the top level,
        e.g. gloss-to-tag conversion or collation of analyses.
        TODO: actually, the top-level tier here is the lowest tier in the
        hierarchy where subdivision of a parent cell implies multiple
        analyses. A POS or a lemma tier could be top-level, for example.
        """
        analyses = []
        analysisTiers = []
        for tierType in ['pos', 'gramm', 'lemma', 'parts', 'gloss']:
            if (aID, tierType) not in self.segmentChildren:
                continue
            analysisTiers.append([])
            for childID in self.segmentChildren[(aID, tierType)]:
                if childID not in self.segmentTree:
                    continue
                contents = self.segmentTree[childID][0]
                for ana in self.retrieve_analyses(childID, lang=lang, topLevel=False):
                    if tierType == 'lemma':
                        ana['lex'] = contents
                    elif tierType == 'parts':
                        ana['parts'] = contents
                    elif tierType == 'gloss':
                        ana['gloss'] = contents
                    elif tierType == 'pos' and len(contents) > 0:
                        ana['gr.pos'] = contents
                    elif tierType == 'gramm':
                        grJSON = self.tp.parser.transform_gramm_str(contents, lang=lang)
                        ana.update(grJSON)
                    analysisTiers[-1].append(ana)
            analysisTiers[-1] = [ana for ana in analysisTiers[-1] if len(ana) > 0]
        if len(analysisTiers) <= 0:
            return [{}]
        for combination in itertools.product(*analysisTiers):
            ana = {}
            for partAna in combination:
                ana.update(partAna)
            if len(ana) > 0:
                analyses.append(ana)
        if topLevel:
            if ('one_morph_per_cell' in self.corpusSettings
                    and self.corpusSettings['one_morph_per_cell']):
                curLex = set()
                curStemGloss = set()
                allAnaFields = set()
                for ana in analyses:
                    for k in ana:
                        allAnaFields.add(k)
                totalAna = {k: '' for k in allAnaFields}
                for k in totalAna:
                    for ana in analyses:
                        if k in ['lex'] or k.startswith('gr.'):
                            if len(totalAna[k]) <= 0:
                                totalAna[k] = ana[k]
                            elif type(totalAna[k]) == str and totalAna[k] != ana[k]:
                                totalAna[k] = [totalAna[k], ana[k]]
                            elif type(totalAna[k]) == list and ana[k] not in totalAna[k]:
                                totalAna[k].append(ana[k])
                        else:
                            if len(totalAna[k]) > 0 and k not in ['parts']:
                                totalAna[k] += '-'
                            if k not in ana:
                                totalAna[k] += '∅'
                            else:
                                totalAna[k] += ana[k]
                                if k == 'parts' and not ana[k].startswith('-') and not ana[k].endswith('-'):
                                    curLex.add(ana[k])
                                    if 'gloss' in ana:
                                        curStemGloss.add(ana['gloss'])
                if 'lex' not in totalAna or len(totalAna['lex']) <= 0:
                    totalAna['lex'] = [l for l in sorted(curLex)]
                    if len(totalAna['lex']) == 1:
                        totalAna['lex'] = totalAna['lex'][0]
                if 'trans_en' not in totalAna or len(totalAna['trans_en']) <= 0:
                    totalAna['trans_en'] = [t for t in sorted(curStemGloss)]
                    if len(totalAna['trans_en']) == 1:
                        totalAna['trans_en'] = totalAna['trans_en'][0]
                analyses = [totalAna]

            for ana in analyses:
                self.tp.parser.process_gloss_in_ana(ana)
                if 'gloss_index' in ana:
                    self.tp.parser.gloss2gr(ana, self.corpusSettings['languages'][0])
        if len(analyses) <= 0:
            return [{}]
        return analyses

    def retrieve_words(self, text, wordIDs, lang=''):
        """
        Return a list of words with their analyses retrieved from the relevant
        tiers of an analyzed EAF file. Try to align words with the text of the
        entire sentence.
        """
        words = []
        iSentPos = 0
        iBufferStart = 0
        sBuffer = ''
        for iWord in range(len(wordIDs)):
            iWordPos = 0
            word = self.segmentTree[wordIDs[iWord]][0]
            if len(sBuffer) <= 0:
                iBufferStart = iSentPos
            if len(word) <= 0:
                continue
            while iSentPos < len(text) and text[iSentPos].lower() != word[iWordPos].lower():
                sBuffer += text[iSentPos]
                iSentPos += 1
            if len(sBuffer) > 0:
                words += self.add_punc(sBuffer, iBufferStart)
                sBuffer = ''
                iBufferStart = iSentPos
            if iSentPos == len(text):
                print('Unexpected end of sentence:', text)
                return words
            token = {'wf': word, 'off_start': iSentPos, 'off_end': iSentPos + len(word), 'wtype': 'word'}
            while iSentPos < len(text) and iWordPos < len(word):
                if text[iSentPos].lower() == word[iWordPos].lower():
                    iSentPos += 1
                    iWordPos += 1
                    continue
                if self.rxLetters.search(word[iWordPos]) is None and self.rxLetters.search(text[iSentPos]) is not None:
                    iWordPos += 1
                    continue
                iSentPos += 1
            token['off_end'] = iSentPos
            analyses = [ana for ana in self.retrieve_analyses(wordIDs[iWord], lang=lang) if len(ana) > 0]
            if len(analyses) > 0:
                token['ana'] = analyses
            words.append(token)
        if iSentPos < len(text):
            words += self.add_punc(text[iSentPos:], iSentPos)
        return words

    def process_tier(self, tierNode, aID2pID, srcFile, alignedTier=False):
        """
        Extract segments from the tier node and iterate over them, returning
        them as JSON sentences. If alignedTier is False, store the start and end
        timestamps, as well as pIDs for alignment, in the dictionary aID2pID.
        If alignedTier is True, use the information from aID2pID for establishing
        time boundaries of the sentences and aligning it with the source tier. 
        """
        lang = ''
        # We have to find out what language the tier represents.
        # First, check the tier type. If it is not associated with any language,
        # check all tier ID regexes.
        if 'TIER_ID' not in tierNode.attrib:
            return
        if ('LINGUISTIC_TYPE_REF' in tierNode.attrib and
                tierNode.attrib['LINGUISTIC_TYPE_REF'] in self.corpusSettings['tier_languages']):
            lang = self.corpusSettings['tier_languages'][tierNode.attrib['LINGUISTIC_TYPE_REF']]
        else:
            for k, v in self.corpusSettings['tier_languages'].items():
                if not k.startswith('^'):
                    k = '^' + k
                if not k.endswith('$'):
                    k += '$'
                try:
                    rxTierID = re.compile(k)
                    if rxTierID.search(tierNode.attrib['TIER_ID']) is not None:
                        lang = v
                        break
                except:
                    continue
        if len(lang) <= 0 or lang not in self.corpusSettings['languages']:
            return
        langID = self.corpusSettings['languages'].index(lang)
        
        speaker = ''
        if not alignedTier and 'PARTICIPANT' in tierNode.attrib:
            speaker = tierNode.attrib['PARTICIPANT']
            self.participants[tierNode.attrib['TIER_ID']] = speaker
        else:
            if ('PARENT_REF' in tierNode.attrib
                    and tierNode.attrib['PARENT_REF'] in self.participants):
                speaker = self.participants[tierNode.attrib['PARENT_REF']]
            elif 'PARTICIPANT' in tierNode.attrib:
                speaker = tierNode.attrib['PARTICIPANT']

        segments = tierNode.xpath('ANNOTATION/REF_ANNOTATION | ANNOTATION/ALIGNABLE_ANNOTATION')
        
        for segNode in segments:
            if ('ANNOTATION_ID' not in segNode.attrib
                    or segNode.attrib['ANNOTATION_ID'] not in self.segmentTree):
                continue
            segData = self.segmentTree[segNode.attrib['ANNOTATION_ID']]
            if not alignedTier:
                if segData[2] is None or segData[3] is None:
                    continue
                tli1 = segData[2]
                tli2 = segData[3]
            elif segData[1] is not None:
                aID = segData[1]
                pID, tli1, tli2 = aID2pID[aID]
            else:
                continue
            text = segData[0]
            curSent = {'text': text, 'words': None, 'lang': langID,
                       'meta': {'speaker': speaker}}
            if speaker in self.speakerMeta:
                for k, v in self.speakerMeta[speaker].items():
                    curSent['meta'][k] = v
            if (segNode.attrib['ANNOTATION_ID'], 'word') not in self.segmentChildren:
                curSent['words'] = self.tp.tokenizer.tokenize(text)
                self.tp.splitter.add_next_word_id_sentence(curSent)
                self.tp.parser.analyze_sentence(curSent, lang=lang)
            else:
                curSent['words'] = self.retrieve_words(text,
                                                       self.segmentChildren[(segNode.attrib['ANNOTATION_ID'],
                                                                             'word')],
                                                       lang=lang)
                self.tp.splitter.add_next_word_id_sentence(curSent)
            if len(self.corpusSettings['aligned_tiers']) > 0:
                if not alignedTier:
                    self.pID += 1
                    aID = segNode.attrib['ANNOTATION_ID']
                    aID2pID[aID] = (self.pID, tli1, tli2)
                    paraAlignment = {'off_start': 0, 'off_end': len(curSent['text']), 'para_id': self.pID}
                    curSent['para_alignment'] = [paraAlignment]
                else:
                    paraAlignment = {'off_start': 0, 'off_end': len(curSent['text']), 'para_id': pID}
                    curSent['para_alignment'] = [paraAlignment]
            self.add_src_alignment(curSent, tli1, tli2, srcFile)
            yield curSent

    def get_sentences(self, srcTree, srcFile):
        """
        Iterate over sentences in the XML tree.
        """
        # mainTierTypes = '(' + ' | '.join('/ANNOTATION_DOCUMENT/TIER[@LINGUISTIC_TYPE_REF=\'' + x + '\'] | ' +
        #                                  '/ANNOTATION_DOCUMENT/TIER[@TIER_ID=\'' + x + '\']'
        #                                  for x in self.corpusSettings['main_tiers']) + ')'
        # mainTiers = srcTree.xpath(mainTierTypes)
        mainTiers = []
        alignedTiers = []
        for tierNode in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER'):
            for tierRegex in self.corpusSettings['main_tiers']:
                if not tierRegex.startswith('^'):
                    tierRegex = '^' + tierRegex
                if not tierRegex.endswith('$'):
                    tierRegex += '$'
                try:
                    if re.search(tierRegex, tierNode.attrib['TIER_ID']) is not None:
                        mainTiers.append(tierNode)
                        break
                    elif ('LINGUISTIC_TYPE_REF' in tierNode.attrib
                            and re.search(tierRegex, tierNode.attrib['LINGUISTIC_TYPE_REF']) is not None):
                        mainTiers.append(tierNode)
                        break
                except:
                    pass
            for tierRegex in self.corpusSettings['aligned_tiers']:
                if not tierRegex.startswith('^'):
                    tierRegex = '^' + tierRegex
                if not tierRegex.endswith('$'):
                    tierRegex += '$'
                try:
                    if re.search(tierRegex, tierNode.attrib['TIER_ID']) is not None:
                        alignedTiers.append(tierNode)
                        break
                    elif ('LINGUISTIC_TYPE_REF' in tierNode.attrib
                            and re.search(tierRegex, tierNode.attrib['LINGUISTIC_TYPE_REF']) is not None):
                        alignedTiers.append(tierNode)
                        break
                except:
                    pass
        if len(mainTiers) <= 0:
            return
        # if len(self.corpusSettings['aligned_tiers']) > 0:
        #     alignedTierTypes = '(' + ' | '.join('/ANNOTATION_DOCUMENT/TIER[@LINGUISTIC_TYPE_REF=\'' + x + '\'] | ' +
        #                                         '/ANNOTATION_DOCUMENT/TIER[@TIER_ID=\'' + x + '\']'
        #                                         for x in self.corpusSettings['aligned_tiers']) + ')'
        #     alignedTiers = srcTree.xpath(alignedTierTypes)
        aID2pID = {}    # annotation ID -> (pID, tli1, tli2) correspondence
        for tier in mainTiers:
            for sent in self.process_tier(tier, aID2pID, srcFile, alignedTier=False):
                yield sent
        for tier in alignedTiers:
            for sent in self.process_tier(tier, aID2pID, srcFile, alignedTier=True):
                yield sent

    def add_speaker_marks(self, sentences):
        """
        Add the name/code of the speaker in the beginning of every
        sentence that starts the turn.
        """
        prevSpeaker = ''
        for i in range(len(sentences)):
            if 'meta' not in sentences[i] or 'speaker' not in sentences[i]['meta']:
                continue
            speaker = '[' + sentences[i]['meta']['speaker'] + ']'
            addOffset = len(speaker) + 2
            if sentences[i]['meta']['speaker'] != prevSpeaker:
                sentences[i]['text'] = '\n' + speaker + ' ' + sentences[i]['text']
                sentences[i]['words'].insert(0, {'off_start': -len(speaker) - 1,
                                                 'off_end': -1,
                                                 'wf': speaker,
                                                 'wtype': 'punc',
                                                 'next_word': 0})
                sentences[i]['words'].insert(0, {'off_start': -len(speaker) - 2,
                                                 'off_end': -len(speaker)-1,
                                                 'wf': '\n',
                                                 'wtype': 'punc',
                                                 'next_word': -1})
                for w in sentences[i]['words']:
                    w['off_start'] += addOffset
                    w['off_end'] += addOffset
                    w['next_word'] += 2
                if 'para_alignment' in sentences[i]:
                    for pa in sentences[i]['para_alignment']:
                        if pa['off_start'] > 0:
                            pa['off_start'] += addOffset
                        pa['off_end'] += addOffset
                if 'src_alignment' in sentences[i]:
                    for sa in sentences[i]['src_alignment']:
                        if sa['off_start_sent'] > 0:
                            sa['off_start_sent'] += addOffset
                        sa['off_end_sent'] += addOffset
            prevSpeaker = sentences[i]['meta']['speaker']
            if 'last' in sentences[i] and sentences[i]['last']:
                prevSpeaker = ''

    def add_sentence_meta(self, sentences, meta):
        """
        Add some of the document-level metadata to the sentences.
        """
        for s in sentences:
            if 'meta' not in s:
                continue
            if 'year1' in meta and 'year2' in meta and meta['year1'] == meta['year2']:
                s['meta']['year'] = meta['year1']

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        self.build_segment_tree(srcTree)
        srcFileNode = srcTree.xpath('/ANNOTATION_DOCUMENT/HEADER/MEDIA_DESCRIPTOR')
        if len(srcFileNode) > 0 and 'RELATIVE_MEDIA_URL' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', html.unescape(srcFileNode[0].attrib['RELATIVE_MEDIA_URL']))
        elif len(srcFileNode) > 0 and 'MEDIA_URL' in srcFileNode[0].attrib:
            srcFile = self.rxStripDir.sub('', html.unescape(srcFileNode[0].attrib['MEDIA_URL']))
        else:
            srcFile = ''
        textJSON['sentences'] = [s for s in self.get_sentences(srcTree, srcFile)]
        textJSON['sentences'].sort(key=lambda s: (s['lang'], s['src_alignment'][0]['true_off_start_src']))
        for i in range(len(textJSON['sentences']) - 1):
            # del textJSON['sentences'][i]['src_alignment'][0]['true_off_start_src']
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
            for word in textJSON['sentences'][i]['words']:
                nTokens += 1
                if word['wtype'] == 'word':
                    nWords += 1
                if 'ana' in word and len(word['ana']) > 0:
                    nAnalyzed += 1
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        self.add_speaker_marks(textJSON['sentences'])
        self.add_sentence_meta(textJSON['sentences'], curMeta)
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed

    def process_corpus(self, cutMedia=True):
        """
        Take every eaf file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        """
        Txt2JSON.process_corpus(self)
        if not cutMedia:
            return
        for path, dirs, files in os.walk(os.path.join(self.corpusSettings['corpus_dir'],
                                                      self.srcExt)):
            for fname in files:
                fileExt = os.path.splitext(fname.lower())[1]
                if fileExt in self.mediaExtensions:
                    fname = os.path.abspath(os.path.join(path, fname))
                    print('Cutting media file', fname)
                    self.mc.cut_media(fname)


if __name__ == '__main__':
    t2j = Eaf2JSON()
    t2j.process_corpus(cutMedia=True)

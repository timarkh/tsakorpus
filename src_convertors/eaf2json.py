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

    mediaExtensions = {'.wav', '.mp3', '.mp4', '.avi', '.mov', '.mts'}
    rxSpaces = re.compile('[ \t]+')
    rxLetters = re.compile('\w+')
    bracketPairs = {
        ']': re.compile('\\[[^ \\]]*$'),
        ')': re.compile('\\([^ \\)]*$'),
        '>': re.compile('<[^ >]*$'),
        '}': re.compile('\\{[^ \\}]*$'),
    }
    standardAnaTiers = ['pos', 'gramm', 'lemma', 'parts', 'gloss']

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.speakerMeta = self.load_speaker_meta()
        self.mc = MediaCutter(settings=self.corpusSettings)
        self.srcExt = 'eaf'
        self.tlis = {}  # time labels
        self.pID = 0  # id of last aligned segment
        self.glosses = set()
        self.participants = {}  # main tier ID -> participant ID
        self.segmentTree = {}  # aID -> (contents, parent aID, tli1, tli2)
        self.segmentChildren = {}  # (aID, child tier type) -> [child aID]
        self.spanAnnoTiers = {}  # span annotation tier type -> {tier ID -> [(tli1, tli2, contents)}
        self.alignedSpanAnnoTiers = {}  # aID of a segment -> {span annotation tier ID -> contents}
        self.spanAnnoTLIs = {}   # time-aligned span annotation ID -> {(tli1, tli2)}
        self.additionalWordFields = []  # names of additional word-level fields associated with some analysis tiers
        self.privacySegments = {}  # segments (start_ms, end_ms) that should be beeped out, one list per source file
        self.rxIgnoreTokens = None
        self.set_ignore_tokens()
        self.usedMediaFiles = set()  # filenames of media fragments referenced in the JSONs

    def set_ignore_tokens(self):
        """
        Compile regexes for tokens which should be ignored when
        aligning the token tier with the text tier.
        """
        if 'ignore_tokens' not in self.corpusSettings:
            self.corpusSettings['ignore_tokens'] = ''
        if not self.corpusSettings['ignore_tokens'].startswith('^'):
            self.corpusSettings['ignore_tokens'] = '^' + self.corpusSettings['ignore_tokens']
        if not self.corpusSettings['ignore_tokens'].endswith('$'):
            self.corpusSettings['ignore_tokens'] += '$'
        try:
            self.rxIgnoreTokens = re.compile(self.corpusSettings['ignore_tokens'])
        except:
            print('Please check your ignore token regex.')

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

    def add_aligned_style_span_data(self, parentID, annoTierID, text):
        if annoTierID is None or len(annoTierID) <= 0 or parentID is None:
            return
        if parentID not in self.alignedSpanAnnoTiers:
            self.alignedSpanAnnoTiers[parentID] = {}
        self.alignedSpanAnnoTiers[parentID][annoTierID] = text

    def get_span_tier_id(self, tierNode):
        """
        Return tier ID and the sentence-level metadata field name for a tier that contains
        sentence-level annotation, based on the span_annotation_tiers dictionary
        in conversion_settings.json.
        """
        if 'span_annotation_tiers' not in self.corpusSettings:
            return tierNode.attrib['TIER_ID'], None
        annoTierRules = {}
        if ('LINGUISTIC_TYPE_REF' in tierNode.attrib and
                tierNode.attrib['LINGUISTIC_TYPE_REF'] in self.corpusSettings['span_annotation_tiers']):
            annoTierRules = self.corpusSettings['span_annotation_tiers'][tierNode.attrib['LINGUISTIC_TYPE_REF']]
        else:
            for k, v in self.corpusSettings['span_annotation_tiers'].items():
                if not k.startswith('^'):
                    k = '^' + k
                if not k.endswith('$'):
                    k += '$'
                try:
                    rxTierID = re.compile(k)
                    if rxTierID.search(tierNode.attrib['TIER_ID']) is not None:
                        annoTierRules = v
                        break
                except:
                    continue
        if len(annoTierRules) <= 0 or 'sentence_meta' not in annoTierRules:
            return tierNode.attrib['TIER_ID'], None
        return tierNode.attrib['TIER_ID'], annoTierRules['sentence_meta']

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
                        if tierType not in self.standardAnaTiers:
                            self.additionalWordFields.append(tierType)
                        break
                except:
                    print('Something is wrong with an analysis tier regex: ' + k)
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
            annoTierID, annoTierType = self.get_span_tier_id(tierNode)
            self.add_aligned_style_span_data(segParent, annoTierType, segContents)

    def build_segment_tree(self, srcTree):
        """
        Read the entire XML tree and save all segment data (contents, links to
        the parents and timestamps, if any).
        """
        self.segmentTree = {}
        self.segmentChildren = {}
        self.traverse_tree(srcTree, self.cb_build_segment_tree)

    def fragmentize_src_alignment(self, sent):
        """
        Find corresponding media file fragment and transform a JSON
        dictionaries with the information about the alignment.
        """
        if 'src_alignment' not in sent:
            return
        sent['src_alignment'].sort(key=lambda a: a['off_start_src'])
        minTime = sent['src_alignment'][0]['off_start_src']
        maxTime = sent['src_alignment'][-1]['off_end_src']
        for alignment in sent['src_alignment']:
            fileName, fileExt = os.path.splitext(alignment['src'].lower())
            if fileExt not in self.mediaExtensions:
                return
            segStart = alignment['off_start_src']
            segEnd = alignment['off_end_src']
            ts1frag, ts2frag, srcFileFrag = self.mc.get_media_name(alignment['src'],
                                                                   segStart,
                                                                   segEnd,
                                                                   minTime=minTime,
                                                                   maxTime=maxTime)
            self.usedMediaFiles.add(srcFileFrag)
            alignment['src'] = srcFileFrag
            alignment['off_start_src'] = ts1frag
            alignment['off_end_src'] = ts2frag

    def add_src_alignment(self, sent, tli1, tli2, srcFile):
        """
        Add the alignment of the sentence with the sound/video. If
        word-level time data is available, align words, otherwise
        align the whole sentence.
        """
        sentAlignments = []
        ts1 = self.tlis[tli1]['time']
        ts2 = self.tlis[tli2]['time']
        sentAlignments.append({'off_start_src': float(ts1) / EAF_TIME_MULTIPLIER,
                               'off_end_src': float(ts2) / EAF_TIME_MULTIPLIER,
                               'true_off_start_src': float(ts1) / EAF_TIME_MULTIPLIER,
                               'off_start_sent': 0,
                               'off_end_sent': len(sent['text']),
                               'mtype': 'audio',
                               'src_id': ts1 + '_' + ts2,
                               'src': srcFile})
        # for alignment in sentAlignments:
        #     self.fragmentize_src_alignment(alignment)
        sent['src_alignment'] = sentAlignments

    def add_punc(self, words, text, prevText, startOffset):
        """
        Make one or several punctuation tokens out of the text and
        add them to the words list.
        """
        if len(text) <= 0:
            return

        # First, check for closing brackets that should belong to the word:
        if text[0] in self.bracketPairs and len(words) > 0:
            if self.bracketPairs[text[0]].search(prevText) is not None:
                words[-1]['off_end'] += 1
                text = text[1:]

        curToken = {'wf': '', 'off_start': startOffset, 'off_end': startOffset, 'wtype': 'punct'}
        for i in range(len(text)):
            if self.rxSpaces.search(text[i]) is not None:
                if len(curToken['wf']) > 0:
                    curToken['off_end'] = startOffset + i
                    words.append(curToken)
                    curToken = {'wf': '', 'off_start': startOffset + i, 'off_end': startOffset + i, 'wtype': 'punct'}
            else:
                curToken['wf'] += text[i]
        if len(curToken['wf']) > 0:
            curToken['off_end'] = startOffset + len(text)
            words.append(curToken)

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
        for tierType in set(self.standardAnaTiers) | set(self.additionalWordFields):
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
                    elif tierType in self.additionalWordFields:
                        ana[tierType] = contents
                    analysisTiers[-1].append(ana)
            analysisTiers[-1] = [ana for ana in analysisTiers[-1] if len(ana) > 0]
            if len(analysisTiers[-1]) <= 0:
                analysisTiers[-1] = [{}]
        if len(analysisTiers) <= 0 or (len(analysisTiers) == 1 and len(analysisTiers[0]) <= 0):
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
                            if k in ana:
                                if len(totalAna[k]) <= 0:
                                    totalAna[k] = ana[k]
                                elif type(totalAna[k]) == str and totalAna[k] != ana[k]:
                                    totalAna[k] = [totalAna[k], ana[k]]
                                elif type(totalAna[k]) == list and ana[k] not in totalAna[k]:
                                    totalAna[k].append(ana[k])
                        else:
                            if len(totalAna[k]) > 0 and k not in ['parts', 'gloss']:
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
                    if 'analysis_tiers' in self.corpusSettings and 'gramm' not in self.corpusSettings['analysis_tiers']:
                        self.tp.parser.gloss2gr(ana, self.corpusSettings['languages'][0])
        if len(analyses) <= 0:
            return [{}]
        return analyses

    def retrieve_words(self, text, wordIDs, lang=''):
        """
        Return a list of words with their analyses retrieved from the relevant
        tiers of an analyzed EAF file. Try to align words with the text of the
        entire sentence. Return the text as well, since it may be slightly altered
        if there is no exact correspondence between the text tier and the token tier.
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
            if len(word) <= 0 or self.rxIgnoreTokens.search(word) is not None:
                continue
            while iSentPos < len(text) and text[iSentPos].lower() != word[iWordPos].lower():
                sBuffer += text[iSentPos]
                iSentPos += 1
            if len(sBuffer) > 0:
                self.add_punc(words, sBuffer, text[:iBufferStart], iBufferStart)
                sBuffer = ''
                iBufferStart = iSentPos
            if iSentPos == len(text):
                # If the remaining tokens consist of punctuation, add them to the sentence
                if self.rxLetters.search(word) is None and self.rxIgnoreTokens.search(word) is None:
                    text += word
                    self.add_punc(words, word, text[:iSentPos], iSentPos)
                    continue
                else:
                    print('Unexpected end of sentence:', text)
                    return words, text
            token = {'wf': word, 'off_start': iSentPos, 'off_end': iSentPos + len(word), 'wtype': 'word',
                     'n_orig': iWord}
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
            elif self.rxLetters.search(word) is None:
                token['wtype'] = 'punct'
            for rx in self.tp.tokenizer.specialTokenRegexes:
                if rx['regex'].match(word):
                    for k, v in rx['token'].items():
                        token[k] = v
                    break
            words.append(token)
        if iSentPos < len(text):
            self.add_punc(words, text[iSentPos:], text[:iSentPos], iSentPos)
        return words, text

    def process_span_annotation_tier(self, tierNode, alignedTier=False):
        """
        If the tier in tierNode is a span annotation tier, extract its data.
        If the tier is time-aligned, save the data to self.spanAnnoTiers[annoTierID]
        as time labels.
        """
        if ('span_annotation_tiers' not in self.corpusSettings
                or len(self.corpusSettings['span_annotation_tiers']) <= 0):
            return
        annoTierID, annoTierType = self.get_span_tier_id(tierNode)
        if annoTierType is None or len(annoTierType) <= 0:
            return
        if annoTierType not in self.spanAnnoTiers:
            self.spanAnnoTiers[annoTierType] = {}
        if annoTierID not in self.spanAnnoTiers[annoTierType]:
            self.spanAnnoTiers[annoTierType][annoTierID] = []

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
                self.spanAnnoTLIs[segNode.attrib['ANNOTATION_ID']] = (tli1, tli2)
            elif segData[1] is not None:
                aID = segData[1]
                tli1, tli2 = self.spanAnnoTLIs[aID]
                self.spanAnnoTLIs[segNode.attrib['ANNOTATION_ID']] = self.spanAnnoTLIs[aID]
            else:
                continue
            text = segData[0]
            self.spanAnnoTiers[annoTierType][annoTierID].append((tli1, tli2, text))
        self.spanAnnoTiers[annoTierType][annoTierID].sort(
            key=lambda x: (float(self.tlis[x[0]]['time']), float(self.tlis[x[1]]['time']), x[2])
        )

    def add_privacy_segments(self, srcTree, srcFile):
        """
        Remember segments that should be beeped out because they
        contain sensitive data.
        """
        if 'privacy_tier' not in self.corpusSettings or len(srcFile) <= 0:
            return
        privTierID = self.corpusSettings['privacy_tier']
        if srcFile not in self.privacySegments:
            self.privacySegments[srcFile] = []

        for tierNode in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER'):
            if 'TIER_ID' not in tierNode.attrib:
                continue
            if (tierNode.attrib['TIER_ID'] == privTierID or
                    ('LINGUISTIC_TYPE_REF' in tierNode.attrib
                     and tierNode.attrib['LINGUISTIC_TYPE_REF'] == privTierID)):
                segments = tierNode.xpath('ANNOTATION/ALIGNABLE_ANNOTATION')
                for segNode in segments:
                    if ('ANNOTATION_ID' not in segNode.attrib
                            or segNode.attrib['ANNOTATION_ID'] not in self.segmentTree):
                        continue
                    segData = self.segmentTree[segNode.attrib['ANNOTATION_ID']]
                    if segData[2] is None or segData[3] is None:
                        continue
                    tli1 = segData[2]
                    tli2 = segData[3]
                    self.privacySegments[srcFile].append((int(self.tlis[tli1]['time']), int(self.tlis[tli2]['time'])))

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

        # Find out the participant (speaker) and save that information
        speaker = ''
        if not alignedTier and 'PARTICIPANT' in tierNode.attrib:
            speaker = tierNode.attrib['PARTICIPANT']
            self.participants[tierNode.attrib['TIER_ID']] = speaker
        else:
            if ('PARENT_REF' in tierNode.attrib
                    and tierNode.attrib['PARENT_REF'] in self.participants):
                speaker = self.participants[tierNode.attrib['PARENT_REF']]
                self.participants[tierNode.attrib['TIER_ID']] = speaker
            elif 'PARTICIPANT' in tierNode.attrib:
                speaker = tierNode.attrib['PARTICIPANT']
                self.participants[tierNode.attrib['TIER_ID']] = speaker

        # Find out the language of the tier
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
            # A tier can also contain span annotations, let's check it:
            if len(lang) <= 0:
                self.process_span_annotation_tier(tierNode, alignedTier)
            # Otherwise, we do not want a tier with no language association
            return
        langID = self.corpusSettings['languages'].index(lang)

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
            # Add speaker metadata
            if speaker in self.speakerMeta:
                for k, v in self.speakerMeta[speaker].items():
                    curSent['meta'][k] = v
            # Add metadata and style spans from sentence-aligned annotation tiers
            if segNode.attrib['ANNOTATION_ID'] in self.alignedSpanAnnoTiers:
                spanAnnoData = self.alignedSpanAnnoTiers[segNode.attrib['ANNOTATION_ID']]
                for annoTierID in spanAnnoData:
                    curSpanValue = spanAnnoData[annoTierID]
                    if annoTierID not in curSent['meta']:
                        curSent['meta'][annoTierID] = []
                    if curSpanValue not in curSent['meta'][annoTierID]:
                        curSent['meta'][annoTierID].append(curSpanValue)
                    # Add style spans
                    curRules = {}
                    for tierID in self.corpusSettings['span_annotation_tiers']:
                        if ('sentence_meta' in self.corpusSettings['span_annotation_tiers'][tierID]
                                and self.corpusSettings['span_annotation_tiers'][tierID][
                                    'sentence_meta'] == annoTierID):
                            curRules = self.corpusSettings['span_annotation_tiers'][tierID]
                            break
                    if len(curRules) <= 0:
                        continue
                    if 'styles' in curRules and curSpanValue in curRules['styles']:
                        spanStyle = curRules['styles'][curSpanValue]
                        if 'style_spans' not in curSent:
                            curSent['style_spans'] = []
                        curSent['style_spans'].append({
                            'off_start': 0,
                            'off_end': len(curSent['text']),
                            'span_class': spanStyle,
                            'tooltip_text': curSpanValue
                        })
            # Tokenize the sentence or align it with an existing tokenization
            if (segNode.attrib['ANNOTATION_ID'], 'word') not in self.segmentChildren:
                curSent['words'] = self.tp.tokenizer.tokenize(text)
                self.tp.splitter.add_next_word_id_sentence(curSent)
                self.tp.parser.analyze_sentence(curSent, lang=lang)
                curSent['nTokensOrig'] = len(curSent['words'])
            else:
                tokensOrig = self.segmentChildren[(segNode.attrib['ANNOTATION_ID'], 'word')]
                curSent['nTokensOrig'] = len(tokensOrig)
                curSent['words'], curSent['text'] = self.retrieve_words(text,
                                                                        tokensOrig,
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

    def add_span_annotations(self, sentences):
        """
        Add span-like annotations, i.e. annotations that could span several
        tokens or even sentences and reside in time-aligned tiers.
        Add them to the relevant sentences as style spans and/or as sentence-level
        metadata values, depending on what is said in corpusSettings['span_annotation_tiers'].
        Modify sentences, do not return anything.
        """
        sentences.sort(key=lambda s: s['src_alignment'][0]['true_off_start_src'])
        for annoTierType in self.spanAnnoTiers:
            curRules = {}
            for tierID in self.corpusSettings['span_annotation_tiers']:
                if ('sentence_meta' in self.corpusSettings['span_annotation_tiers'][tierID]
                        and self.corpusSettings['span_annotation_tiers'][tierID]['sentence_meta'] == annoTierType):
                    curRules = self.corpusSettings['span_annotation_tiers'][tierID]
                    break
            if len(curRules) <= 0:
                continue

            for annoTierID in self.spanAnnoTiers[annoTierType]:
                # There may be more than one span-like annotation tier of a given type.
                # Different tiers may refer to different participants, so we have to
                # check which tiers should trigger metadata changes for which sentences.
                curSpeaker = ''
                if annoTierID in self.participants:
                    curSpeaker = self.participants[annoTierID]

                iSentence = 0
                iSpan = 0
                while iSentence < len(sentences) and iSpan < len(self.spanAnnoTiers[annoTierType][annoTierID]):
                    curSpan = self.spanAnnoTiers[annoTierType][annoTierID][iSpan]
                    curSentence = sentences[iSentence]
                    if 'languages' in curRules and 'lang' in curSentence:
                        if self.corpusSettings['languages'][curSentence['lang']] not in curRules['languages']:
                            iSentence += 1
                            continue
                    if (len(curSpeaker) > 0 and 'meta' in curSentence
                            and 'speaker' in curSentence['meta']
                            and curSentence['meta']['speaker'] != curSpeaker):
                        iSentence += 1
                        continue
                    curSpanStart = float(self.tlis[curSpan[0]]['time']) / EAF_TIME_MULTIPLIER
                    curSpanEnd = float(self.tlis[curSpan[1]]['time']) / EAF_TIME_MULTIPLIER
                    curSpanValue = curSpan[2]
                    # This is happening after the offsets are recalculated to account for media cutting
                    curSentenceStart = curSentence['src_alignment'][0]['true_off_start_src']
                    curSentenceEnd = curSentenceStart + (float(curSentence['src_alignment'][0]['off_end_src'])
                                                         - float(curSentence['src_alignment'][0]['off_start_src']))
                    if curSpanStart >= curSentenceEnd - 0.03 or len(curSentence['words']) <= 0:
                        iSentence += 1
                        continue
                    elif curSpanEnd <= curSentenceStart + 0.03:
                        iSpan += 1
                        continue

                    if 'meta' not in curSentence:
                        curSentence['meta'] = {}
                    if annoTierType not in curSentence['meta']:
                        curSentence['meta'][annoTierType] = []
                    if curSpanValue not in curSentence['meta'][annoTierType]:
                        curSentence['meta'][annoTierType].append(curSpanValue)

                    # The ugly part: span-like annotations in ELAN are time-aligned, but usually
                    # they refer to tokens, which are symbolical subdivisions of a time-aligned
                    # sentence. So the "real" time boundaries of span-like annotations are visually
                    # aligned with "imaginary" time boundaries of tokens.
                    # We will calculate these imaginary boundaries to compare them to the annotation
                    # boundaries and know which tokens the annotation should cover.
                    # Note that the visual alignment can be imperfect, so we have to account for that.
                    # We use the original tokenization as represented in ELAN for calculations,
                    # which might be different from what is in curSentence['words'] now (e.g. punctuation
                    # might have been absent from the original tokens).
                    tokenDuration = (curSentenceEnd - curSentenceStart) / curSentence['nTokensOrig']
                    tokensInvolvedOrig = []
                    tokensInvolved = []
                    for iToken in range(curSentence['nTokensOrig']):
                        tokenStart = curSentenceStart + (iToken + 0.1) * tokenDuration
                        tokenEnd = curSentenceStart + (iToken + 0.9) * tokenDuration
                        if curSpanStart <= tokenStart and tokenEnd <= curSpanEnd:
                            tokensInvolvedOrig.append(iToken)
                    # Find which actual token numbers correspond to the original ones.
                    if any('n_orig' in t for t in curSentence['words']):
                        for iToken in range(len(curSentence['words'])):
                            curToken = curSentence['words'][iToken]
                            if 'n_orig' in curToken and curToken['n_orig'] in tokensInvolvedOrig:
                                tokensInvolved.append(iToken)
                    else:
                        tokensInvolved = tokensInvolvedOrig     # I'm not sure this is really necessary
                    if (len(tokensInvolved) > 0
                            and 'styles' in curRules
                            and curSpanValue in curRules['styles']):
                        spanOffStart = curSentence['words'][tokensInvolved[0]]['off_start']
                        spanOffEnd = curSentence['words'][tokensInvolved[-1]]['off_end']
                        spanStyle = curRules['styles'][curSpanValue]
                        if 'style_spans' not in curSentence:
                            curSentence['style_spans'] = []
                        curSentence['style_spans'].append({
                            'off_start': spanOffStart,
                            'off_end': spanOffEnd,
                            'span_class': spanStyle,
                            'tooltip_text': curSpanValue + ' [' + str(iSpan) + ']'
                        })
                    if curSpanEnd < curSentenceEnd:
                        iSpan += 1
                    else:
                        iSentence += 1

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
        aID2pID = {}  # annotation ID -> (pID, tli1, tli2) correspondence
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
        if 'insert_speaker_marks' in self.corpusSettings and not self.corpusSettings['insert_speaker_marks']:
            return
        langs2process = [i for i in range(len(self.corpusSettings['languages']))]
        if 'speaker_marks_languages' in self.corpusSettings:
            langs2process = [i for i in range(len(self.corpusSettings['languages']))
                               if self.corpusSettings['languages'][i] in self.corpusSettings['speaker_marks_languages']]
        langs2process = set(langs2process)
        prevSpeaker = ''
        for i in range(len(sentences)):
            if 'meta' not in sentences[i] or 'speaker' not in sentences[i]['meta']:
                continue
            if 'lang' in sentences[i] and sentences[i]['lang'] not in langs2process:
                continue
            speaker = '[' + sentences[i]['meta']['speaker'] + ']'
            addOffset = len(speaker) + 2
            if sentences[i]['meta']['speaker'] != prevSpeaker:
                sentences[i]['text'] = '\n' + speaker + ' ' + sentences[i]['text']
                sentences[i]['words'].insert(0, {'off_start': -len(speaker) - 1,
                                                 'off_end': -1,
                                                 'wf': speaker,
                                                 'wtype': 'punct',
                                                 'next_word': 0})
                sentences[i]['words'].insert(0, {'off_start': -len(speaker) - 2,
                                                 'off_end': -len(speaker) - 1,
                                                 'wf': '\n',
                                                 'wtype': 'punct',
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
                if 'style_spans' in sentences[i]:
                    for ss in sentences[i]['style_spans']:
                        ss['off_start'] += addOffset
                        ss['off_end'] += addOffset
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

    def clean_up_sentences(self, sentences):
        """
        Remove temporary keys that are no longer needed.
        """
        for s in sentences:
            if 'nTokensOrig' in s:
                del s['nTokensOrig']
            for word in s['words']:
                if 'n_orig' in word:
                    del word['n_orig']

    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        self.spanAnnoTiers = {}
        self.alignedSpanAnnoTiers = {}
        self.spanAnnoTLIs = {}
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
        self.add_privacy_segments(srcTree, srcFile)
        self.add_span_annotations(textJSON['sentences'])
        # First sorting: sort sentences by language, but keep them sorted by speaker
        # (which they are now, since each speaker has a separate set of tiers in ELAN).
        textJSON['sentences'].sort(key=lambda s: (s['lang']))
        if 'sentence_segmentation' in self.corpusSettings and self.corpusSettings['sentence_segmentation']:
            self.tp.splitter.resegment_sentences(textJSON['sentences'])
        for s in textJSON['sentences']:
            self.fragmentize_src_alignment(s)
        # Final sorting: inside each language, sort sentences by their time offsets.
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
        if 'add_contextual_flags' in self.corpusSettings and self.corpusSettings['add_contextual_flags']:
            self.tp.splitter.add_contextual_flags(textJSON['sentences'])
        self.add_speaker_marks(textJSON['sentences'])
        self.add_sentence_meta(textJSON['sentences'], curMeta)
        self.clean_up_sentences(textJSON['sentences'])
        if 'capitalize_sentences' in self.corpusSettings and self.corpusSettings['capitalize_sentences']:
            self.tp.splitter.capitalize_sentences(textJSON['sentences'])
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
        mediaDir = os.path.join(self.corpusSettings['corpus_dir'], self.srcExt)
        if 'media_dir' in self.corpusSettings:
            mediaDir = self.corpusSettings['media_dir']
        for path, dirs, files in os.walk(mediaDir):
            # Process video files first
            files = [fname for fname in files if fname.lower().endswith(('.avi', '.mts', '.mov'))] + \
                    [fname for fname in files if fname.lower().endswith('.mp4')] + \
                    [fname for fname in files if not fname.lower().endswith(('.avi', '.mts', '.mov', '.mp4'))]
            for fname in files:
                fileExt = os.path.splitext(fname.lower())[1]
                if fileExt in self.mediaExtensions:
                    privacySegments = []
                    if fname in self.privacySegments:
                        privacySegments = self.privacySegments[fname]
                    fname = os.path.abspath(os.path.join(path, fname))
                    print('Cutting media file', fname)
                    self.mc.cut_media(fname,
                                      usedFilenames=self.usedMediaFiles,
                                      privacySegments=privacySegments)


if __name__ == '__main__':
    t2j = Eaf2JSON()
    t2j.process_corpus(cutMedia=True)

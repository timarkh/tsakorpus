import os
import re
import json


class WordRelations:
    """
    Contains methods for checking and filtering JSON sentences
    according to the constraints on the relations between words
    in a search query (first and foremost, their mutual distance).
    """

    rxWordRelFields = re.compile('^word_(?:dist_)?(rel|from|to)_([0-9]+)_([0-9]+)')

    def __init__(self, settings_dir, rp=None):
        self.settings_dir = settings_dir
        f = open(os.path.join(self.settings_dir, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']
        self.rp = rp    # ResponseProcessor instance
        # self.sentView = sentence_viewer

    def make_pivotal(self, constraints):
        """
        Replace as many word distance constraints as possible with equivalent
        constraints that would include the pivotal word, i. e. the word that
        already has the largest number of constraints. Change the
        constraints dictionary, do not return anything.
        """
        if len(constraints) < 3:
            return
        nPivotalTerm, constraintsByTerm = self.find_pivotal_term(constraints)
        nextTermsStack = [nPivotalTerm]
        processedTerms = []
        while len(nextTermsStack) > 0:
            curTerm = nextTermsStack.pop()
            processedTerms.append(curTerm)
            if curTerm not in constraintsByTerm:
                continue
            for c in constraintsByTerm[curTerm]:
                if c[0] != curTerm:
                    if c[0] in processedTerms:
                        continue
                    nextTermsStack.append(c[0])
                elif c[1] != curTerm:
                    if c[1] in processedTerms:
                        continue
                    nextTermsStack.append(c[1])
                if curTerm == nPivotalTerm:
                    continue
                if nPivotalTerm < curTerm:
                    curPivotalPair = (nPivotalTerm, curTerm)
                else:
                    curPivotalPair = (curTerm, nPivotalTerm)
                if curPivotalPair not in constraints:
                    continue
                if constraints[curPivotalPair]['from'] != constraints[curPivotalPair]['to']:
                    continue
                nextTerm = nextTermsStack[-1]
                pivotToCurDist = constraints[curPivotalPair]['from']
                if nPivotalTerm > curTerm:
                    pivotToCurDist *= -1
                curToNextDistFrom = constraints[c]['from']
                curToNextDistTo = constraints[c]['to']
                if curTerm > nextTerm:
                    curToNextDistFrom, curToNextDistTo = -curToNextDistTo, -curToNextDistFrom
                pivotToNextDistFrom = pivotToCurDist + curToNextDistFrom
                pivotToNextDistTo = pivotToCurDist + curToNextDistTo
                if nPivotalTerm < nextTerm:
                    nextPivotalPair = (nPivotalTerm, nextTerm)
                    constraints[nextPivotalPair] = {'from': pivotToNextDistFrom,
                                                    'to': pivotToNextDistTo}
                else:
                    nextPivotalPair = (nextTerm, nPivotalTerm)
                    constraints[nextPivotalPair] = {'to': -pivotToNextDistFrom,
                                                    'from': -pivotToNextDistTo}
                del constraints[c]

    def get_constraints(self, htmlQuery):
        """
        Extract word relation constraints from an HTML query
        and return them in a more usable form.
        The constraints dictionary returned by this function
        looks like (nWord1, nWord2) -> {'from': from, 'to': to},
        where nWord1 < nWord2.
        """
        constraints = {}
        relIDs = {}
        for field, value in htmlQuery.items():
            mRel = self.rxWordRelFields.search(field)
            if mRel is not None:
                try:
                    value = int(value)
                except:
                    continue
                relType = mRel.group(1)
                nSource = int(mRel.group(2))
                nRel = int(mRel.group(3))
                relID = (nSource, nRel)
                if relType == 'rel':
                    if nSource <= 0 or value <= 0 or nSource == value:
                        continue
                    if relID not in relIDs:
                        relIDs[relID] = {'target': value}
                    else:
                        relIDs[relID]['target'] = value
                else:
                    if nSource <= 0:
                        continue
                    if relID not in relIDs:
                        relIDs[relID] = {relType: value}
                    else:
                        relIDs[relID][relType] = value
        for relID in relIDs:
            nSource, nRel = relID
            if ('target' not in relIDs[relID]
                    or ('from' not in relIDs[relID]
                        and 'to' not in relIDs[relID])):
                continue
            if 'from' not in relIDs[relID]:
                relIDs[relID]['from'] = -1000
            if 'to' not in relIDs[relID]:
                relIDs[relID]['to'] = 1000
            nTarget = relIDs[relID]['target']
            if nTarget < nSource:
                # only store pairs where the first element is less than the second
                nSource, nTarget = nTarget, nSource
                relIDs[relID]['from'], relIDs[relID]['to'] = -relIDs[relID]['to'], -relIDs[relID]['from']
            wordPair = (nSource, nTarget)
            if wordPair in constraints:
                if ('from' in relIDs[relID]
                    and ('from' not in constraints[wordPair] or
                         constraints[wordPair]['from'] < relIDs[relID]['from'])):
                    constraints[wordPair]['from'] = relIDs[relID]['from']
                if ('to' in relIDs[relID]
                    and ('to' not in constraints[wordPair] or
                         constraints[wordPair]['to'] > relIDs[relID]['to'])):
                    constraints[wordPair]['to'] = relIDs[relID]['to']
            else:
                constraints[wordPair] = {}
                if 'from' in relIDs[relID]:
                    constraints[wordPair]['from'] = relIDs[relID]['from']
                if 'to' in relIDs[relID]:
                    constraints[wordPair]['to'] = relIDs[relID]['to']
            self.make_pivotal(constraints)
        return constraints

    def find_pivotal_term(self, distances):
        """
        Find the number of the search term that participates in the
        largest number of distance constraints.
        Return the number of the pivotal term (1-based) and
        a dictionary "term_number -> [word_pairs_with_this_term]".
        """
        nPivotalTerm = 1
        constraints = {}
        if distances is None or len(distances) <= 0:
            return nPivotalTerm, constraints
        for wordPair in distances:
            for w in wordPair:
                if w not in constraints:
                    constraints[w] = []
                constraints[w].append(wordPair)
        curMaxConstraints = 0
        for w in constraints:
            curNConstraints = len(constraints[w])
            if curNConstraints > curMaxConstraints:
                curMaxConstraints = curNConstraints
                nPivotalTerm = w
        return nPivotalTerm, constraints

    def get_one_highlight_pos(self, highlight):
        """
        Find all offset information in one particular highlight.
        Search recursively.
        """
        pos = set()
        if type(highlight) == list:
            for i in range(len(highlight)):
                pos |= self.get_one_highlight_pos(highlight[i])
        elif type(highlight) == dict:
            if 'offset' in highlight:
                pos.add(highlight['offset'])
            else:
                for v in highlight.values():
                    if type(v) in [list, dict]:
                        pos |= self.get_one_highlight_pos(v)
        return pos

    def get_all_highlight_pos(self, innerHits, constraints):
        """
        Find the positions of highlighted words in the list of words.
        """
        relevantHighlights = set()
        for c in constraints:
            relevantHighlights.add('w' + str(c[0]))
            relevantHighlights.add('w' + str(c[1]))
            for pivotalTermPosition in range(self.settings['max_words_in_sentence']):
                relevantHighlights.add('w' + str(c[0]) + '_' + str(pivotalTermPosition))
                relevantHighlights.add('w' + str(c[1]) + '_' + str(pivotalTermPosition))
        if len(relevantHighlights) <= 0:
            return {}
        positions = {}
        for hl in relevantHighlights:
            if hl in innerHits:
                positions[hl] = [p for p in sorted(self.get_one_highlight_pos(innerHits[hl]))]
        return positions

    def find_word_path_lengths(self, words, posFrom, posTo, cumulatedLen=0, countPunc=False,
                               left2right=True):
        """
        Return a set of path lengths between the words with positions
        posFrom and posTo.
        """
        if posFrom == posTo:
            if left2right:
                return {-cumulatedLen}
            else:
                return {cumulatedLen}
        if not (0 <= posFrom < len(words)) or 'next_word' not in words[posFrom]:
            return set()
        result = set()
        lenAdd = 1
        if words[posFrom]['wtype'] != 'word' and not countPunc:
            lenAdd = 0
        if type(words[posFrom]['next_word']) == int:
            result |= self.find_word_path_lengths(words, words[posFrom]['next_word'], posTo,
                                                  cumulatedLen=cumulatedLen + lenAdd,
                                                  countPunc=countPunc,
                                                  left2right=left2right)
        else:
            for iPos in words[posFrom]['next_word']:
                result |= self.find_word_path_lengths(words, iPos, posTo,
                                                      cumulatedLen=cumulatedLen+lenAdd,
                                                      countPunc=countPunc,
                                                      left2right=left2right)
        return result

    def word_path_exists(self, sentence, posFrom, posTo, minEdges, maxEdges, countPunc=False):
        """
        Check if a path with the length in the range [minEdges, maxEdges]
        exists between the words whose positions in the sentence words list
        are posFrom and posTo. If the "from" word is to the left of the
        "to" word in the sentence, the distance is negative. If countPunc
        is set to False, do not count non-word tokens when counting distance.
        """
        if '_source' not in sentence or 'words' not in sentence['_source']:
            return False
        if minEdges > maxEdges:
            return False
        words = sentence['_source']['words']
        if not (0 <= posFrom < len(words)) or not (0 <= posTo < len(words)):
            return False
        if posFrom == posTo and minEdges <= 0 <= maxEdges:
            return True
        pathLengths = self.find_word_path_lengths(words, posFrom, posTo,
                                                  countPunc=countPunc,
                                                  left2right=True)
        if any(minEdges <= pl <= maxEdges for pl in pathLengths):
            return True
        pathLengths = self.find_word_path_lengths(words, posTo, posFrom,
                                                  countPunc=countPunc,
                                                  left2right=False)
        if any(minEdges <= pl <= maxEdges for pl in pathLengths):
            return True
        return False

    def check_sentence(self, sentence, constraints, nWords=1):
        """
        Check if the sentence satisfies the word relation constraints.
        """
        if 'inner_hits' not in sentence:
            return False
        self.rp.filter_multi_word_highlight(sentence, nWords=nWords)
        wordOffsets = self.get_all_highlight_pos(sentence['inner_hits'], constraints)
        for k, v in constraints.items():
            # wFrom, wTo = 'w' + str(k[0]), 'w' + str(k[1])
            # if wFrom not in wordOffsets or wTo not in wordOffsets:
            #     return False
            pathFound = False
            for wFrom in wordOffsets:
                if wFrom != 'w' + str(k[0]) and not wFrom.startswith('w' + str(k[0]) + '_'):
                    continue
                for hlFrom in wordOffsets[wFrom]:
                    for wTo in wordOffsets:
                        if wTo != 'w' + str(k[0]) and not wTo.startswith('w' + str(k[1]) + '_'):
                            continue
                        for hlTo in wordOffsets[wTo]:
                            if self.word_path_exists(sentence, hlFrom, hlTo, v['from'], v['to'],
                                                     countPunc=False):
                                pathFound = True
                                # return {'to': hlTo, 'from': hlFrom,
                                #         'minEdges': v['from'], 'maxEdges': v['to'],
                                #         'pathLengths_l2r': list(self.find_word_path_lengths(sentence['_source']['words'], hlFrom, hlTo)),
                                #         'pathLengths_r2l': list(self.find_word_path_lengths(sentence['_source']['words'], hlTo, hlFrom, left2right=False))}
                                break
                        if pathFound:
                            break
                    if pathFound:
                        break
                if pathFound:
                    break
            if not pathFound:
                return False
        return True

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

    def __init__(self, settings_dir):
        self.settings_dir = settings_dir
        f = open(os.path.join(self.settings_dir, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.name = self.settings['corpus_name']

    def get_constraints(self, htmlQuery):
        """
        Extract word relation constraints from an HTML query
        and return them in a more usable form.
        """
        constraints = {}
        relIDs = {}
        for field, value in htmlQuery.items():
            mRel = self.rxWordRelFields.search(field)
            try:
                value = int(value)
            except ValueError:
                continue
            if mRel is not None:
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
        return constraints

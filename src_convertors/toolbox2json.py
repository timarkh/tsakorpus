import os
import re
import json
from lxml import etree
from txt2json import Txt2JSON


class Toolbox2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    a Toolbox corpus (currently, only without the glosses)
    and a csv with metadata.
    """

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'tbt'
        self.pID = 0        # id of last aligned segment

    def process_para_node(self, paraNode):
        """
        Extract data from a part of tbt file that contains an original sentence,
        probably together with a bunch of parallel fragments in several languages.
        """
        self.pID += 1
        curTiers = {}
        prevTier = ''
        ref = ''
        for line in paraNode.split('\n'):
            line = line.strip()
            if len(line) <= 0:
                continue
            mTier = re.search('^\\\\([a-z0-9]+) *(.*)', line)
            if mTier is None:
                if prevTier in curTiers:
                    curTiers[prevTier] += ' ' + line
                continue
            prevTier, line = mTier.group(1), mTier.group(2)
            if prevTier in self.corpusSettings['tier_languages']:
                curTiers[prevTier] = line
            elif prevTier == 'ref':
                ref = '[' + line + ']'
        for t in curTiers:
            langID = self.corpusSettings['languages'].index(self.corpusSettings['tier_languages'][t])
            tokens = self.tp.tokenizer.tokenize(curTiers[t])
            if len(ref) > 0:
                curTiers[t] = ref + ' ' + curTiers[t]
                for token in tokens:
                    token['off_start'] += len(ref) + 1
                    token['off_end'] += len(ref) + 1
                    if 'next_word' in token:
                        token['next_word'] += 1
                tokens.insert(0, {'wf': ref, 'wtype': 'punct', 'off_start': 0, 'off_end': len(ref), 'next_word': 1})
            paraAlignment = {'off_start': 0, 'off_end': len(curTiers[t]), 'para_id': self.pID}
            sentence = {'words': tokens, 'text': curTiers[t], 'para_alignment': [paraAlignment],
                        'lang': langID}
            yield sentence


    def convert_file(self, fnameSrc, fnameTarget):
        curMeta = self.get_meta(fnameSrc)
        textJSON = {'meta': curMeta, 'sentences': []}
        nTokens, nWords, nAnalyzed = 0, 0, 0
        fIn = open(fnameSrc, 'r', encoding='utf-8-sig')
        try:
            text = fIn.read()
        except:
            fIn.close()
            print('Could not read file', fnameSrc)
            fIn.close()
            return 0, 0, 0
        fIn.close()
        textJSON['sentences'] = [s for node in re.findall('\n\\\\ref +(?:.(?!\\\\ref ))+', text, flags=re.DOTALL)
                                 for s in self.process_para_node(node)]
        textJSON['sentences'].sort(key=lambda s: s['lang'])
        for i in range(len(textJSON['sentences']) - 1):
            if textJSON['sentences'][i]['lang'] != textJSON['sentences'][i + 1]['lang']:
                textJSON['sentences'][i]['last'] = True
            for word in textJSON['sentences'][i]['words']:
                nTokens += 1
                if 'wtype' in word and word['wtype'] == 'word':
                    nWords += 1
                    if 'ana' in word and len(word['ana']) > 0:
                        nAnalyzed += 1
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed


if __name__ == '__main__':
    x2j = Toolbox2JSON()
    x2j.process_corpus()

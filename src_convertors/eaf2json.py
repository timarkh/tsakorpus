import os
import re
import json
from txt2json import Txt2JSON


class Eaf2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    ELAN aligned files, a csv with metadata and a list with parsed
    word forms.
    """

    def convert_file(self, fnameSrc, fnameTarget):
        fname2check = fnameSrc
        curMeta = {'filename': fnameSrc}
        if not self.corpusSettings['meta_files_dir']:
            fname2check = self.rxStripDir.sub('', fname2check)
        if not self.corpusSettings['meta_files_ext']:
            fname2check = self.rxStripExt.sub('', fname2check)
        if not self.corpusSettings['meta_files_case_sensitive']:
            fname2check = fname2check.lower()
        if fname2check not in self.meta:
            print('File not in meta:', fnameSrc)
        else:
            curMeta.update(self.meta[fname2check])
        textJSON = {'meta': curMeta, 'sentences': []}
        words, parsedWords, sentences = 0, 0, 0
        fSrc = open(fnameSrc, 'r', encoding='utf-8')
        eafText = fSrc.read()
        fSrc.close()

        text = eafText
        # TODO: actual EAF processing
        textJSON['sentences'] = self.tp.process_string(text)

        fTarget = open(fnameTarget, 'w', encoding='utf-8')
        fTarget.write(json.dumps(textJSON, ensure_ascii=False,
                                 indent=self.corpusSettings['json_indent']))
        fTarget.close()
        return words, parsedWords

    def process_corpus(self):
        """
        Take every eaf file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        """
        if self.corpusSettings is None or len(self.corpusSettings) <= 0:
            return
        self.load_meta()
        wordsTotal, parsedTotal = 0, 0
        srcDir = os.path.join(self.corpusSettings['corpus_dir'], 'eaf')
        targetDir = os.path.join(self.corpusSettings['corpus_dir'], 'json')
        for path, dirs, files in os.walk(srcDir):
            for filename in files:
                if not filename.lower().endswith('.eaf'):
                    continue
                targetPath = path.replace(srcDir, targetDir)
                if targetPath == path:
                    continue    # this should never happen, but just in case
                if not os.path.exists(targetPath):
                    os.makedirs(targetPath)
                fnameSrc = os.path.join(path, filename)
                fnameTarget = os.path.join(targetPath, filename)
                fnameTarget = self.rxStripExt.sub('.json', fnameTarget)
                curWords, curWordsPared = self.convert_file(fnameSrc, fnameTarget)
                wordsTotal += curWords
                parsedTotal += curWordsPared
        print('Conversion finished.', wordsTotal, 'words total.')
        if wordsTotal > 0:
            print(parsedTotal, 'words parsed (' + str(parsedTotal / wordsTotal) + '%).')


if __name__ == '__main__':
    t2j = Eaf2JSON()
    # t2j.process_corpus()

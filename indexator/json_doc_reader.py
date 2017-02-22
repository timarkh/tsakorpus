import json
import os


class JSONDocReader:
    """
    An instance of this class is used by the indexator to iterate
    through sentences read from corpus files in tsakorpus native
    JSON format.
    """
    def __init__(self):
        self.filesize_limit = -1

    def get_sentences(self, fname):
        """
        If the file is not too large, iterate through its
        sentences.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        fIn = open(fname, 'r', encoding='utf-8-sig')
        sentences = json.load(fIn)
        fIn.close()
        for i in range(len(sentences)):
            if i == len(sentences) - 1:
                yield sentences[i], True
            else:
                yield sentences[i], False

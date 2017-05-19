import json
import os
import gzip


class JSONDocReader:
    """
    An instance of this class is used by the indexator to iterate
    through sentences read from corpus files in tsakorpus native
    JSON format.
    """
    def __init__(self, format=format):
        self.filesize_limit = -1
        self.lastFileName = ''
        self.format = format
        self.lastDoc = None         # for lazy calculations

    def get_metadata(self, fname):
        """
        If the file is not too large, return its metadata.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        if fname == self.lastFileName and self.lastDoc is not None:
            return self.lastDoc['meta']
        self.lastFileName = fname
        if self.format == 'json':
            fIn = open(fname, 'r', encoding='utf-8-sig')
        elif self.format == 'json-gzip':
            fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
        else:
            return {}
        doc = json.load(fIn)
        self.lastDoc = doc
        metadata = doc['meta']
        fIn.close()
        return metadata

    def get_sentences(self, fname):
        """
        If the file is not too large, iterate through its
        sentences.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        if fname == self.lastFileName and self.lastDoc is not None:
            sentences = self.lastDoc['sentences']
        else:
            self.lastFileName = fname
            if self.format == 'json':
                fIn = open(fname, 'r', encoding='utf-8-sig')
            elif self.format == 'json-gzip':
                fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
            else:
                return {}, True
            doc = json.load(fIn)
            self.lastDoc = doc
            sentences = doc['sentences']
            fIn.close()
        for i in range(len(sentences)):
            if i == len(sentences) - 1:
                yield sentences[i], True
            else:
                yield sentences[i], False

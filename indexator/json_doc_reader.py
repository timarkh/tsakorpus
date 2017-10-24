import json
import ijson
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
        self.lastDocMeta = None         # for lazy calculations

    @staticmethod
    def insert_meta_year(metadata):
        """
        If there is no year field in metadata, but there are year1 and
        year2 fields denoting a range whose values do not differ too much,
        insert the year field. In the opposite case, insert year1 and year2 fields.
        """
        for yearField in ['year', 'year1', 'year2']:
            if yearField in metadata and type(metadata[yearField]) == str:
                try:
                    metadata[yearField] = int(metadata[yearField])
                except:
                    del metadata[yearField]
        if 'year' not in metadata and 'year1' in metadata and 'year2' in metadata:
            if metadata['year1'] == metadata['year2']:
                metadata['year'] = metadata['year1']
            elif 0 < int(metadata['year2']) - int(metadata['year1']) <= 2:
                metadata['year'] = (metadata['year2'] + metadata['year1']) // 2
        elif 'year' in metadata:
            if 'year1' not in metadata:
                metadata['year1'] = metadata['year']
            if 'year2' not in metadata:
                metadata['year2'] = metadata['year']

    def get_metadata(self, fname):
        """
        If the file is not too large, return its metadata.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        if fname == self.lastFileName and self.lastDocMeta is not None:
            self.insert_meta_year(self.lastDocMeta)
            return self.lastDocMeta
        self.lastFileName = fname
        if self.format == 'json':
            fIn = open(fname, 'r', encoding='utf-8-sig')
        elif self.format == 'json-gzip':
            fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
        else:
            return {}
        metadata = {}
        curMetaField = ''
        JSONParser = ijson.parse(fIn)
        for prefix, event, value in JSONParser:
            if (prefix, event) == ('meta', 'map_key'):
                curMetaField = value
            elif len(curMetaField) > 0 and prefix.startswith('meta.'):
                metadata[curMetaField] = value
            elif (prefix, event) == ('meta', 'end_map'):
                break
        self.lastDocMeta = metadata
        fIn.close()
        self.insert_meta_year(metadata)
        return metadata

    def get_sentences(self, fname):
        """
        If the file is not too large, iterate through its
        sentences.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        self.lastFileName = fname
        if self.format == 'json':
            fIn = open(fname, 'r', encoding='utf-8-sig')
        elif self.format == 'json-gzip':
            fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
        else:
            return {}, True
        try:
            doc = json.load(fIn)
            self.lastDocMeta = doc['meta']
            fIn.close()
            for i in range(len(doc['sentences'])):
                if i < len(doc['sentences']) - 1:
                    yield doc['sentences'][i], False
                else:
                    yield doc['sentences'][i], True
                    return
        except MemoryError:
            print('Memory error when reading', fname, ', trying iterative JSON parser (will work slowly).')
            fIn.close()
            self.lastDocMeta = None
            if self.format == 'json':
                fIn = open(fname, 'r', encoding='utf-8-sig')
            elif self.format == 'json-gzip':
                fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
            else:
                return {}, True
            prevSent = {}
            for sentence in ijson.items(fIn, 'sentences.item'):
                if prevSent != {}:
                    yield prevSent, False
                prevSent = sentence
            fIn.close()
            yield prevSent, True
            return

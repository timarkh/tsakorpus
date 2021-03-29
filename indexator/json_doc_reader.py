import json
import ijson
import os
import gzip
import random


class JSONDocReader:
    """
    An instance of this class is used by the indexator to iterate
    through sentences read from corpus files in tsakorpus native
    JSON format.
    """
    def __init__(self, format, settings):
        self.filesize_limit = -1
        self.lastFileName = ''
        self.format = format
        self.lastDocMeta = None         # for lazy calculations
        self.settings = settings
        self.nonpersistentID = random.randint(1, 100)

    @staticmethod
    def insert_meta_year(metadata):
        """
        If there is no year field in metadata, but there are year_from and
        year_to fields denoting a range whose values do not differ too much,
        insert the year field. In the opposite case, insert year_from and year_to fields.
        """
        for yearField in ['year', 'year_from', 'year_to']:
            if yearField in metadata and type(metadata[yearField]) == str:
                try:
                    metadata[yearField] = int(metadata[yearField])
                except:
                    del metadata[yearField]
        if 'year' not in metadata and 'year_from' in metadata and 'year_to' in metadata:
            if metadata['year_from'] == metadata['year_to']:
                metadata['year'] = metadata['year_from']
            elif 0 < int(metadata['year_to']) - int(metadata['year_from']) <= 2:
                metadata['year'] = (metadata['year_to'] + metadata['year_from']) // 2
        elif 'year' in metadata:
            if 'year_from' not in metadata:
                metadata['year_from'] = metadata['year']
            if 'year_to' not in metadata:
                metadata['year_to'] = metadata['year']

    def get_metadata(self, fname):
        """
        If the file is not too large, return its metadata.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        if fname == self.lastFileName and self.lastDocMeta is not None:
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
        if ('fulltext_id' not in metadata
                and 'use_nonpersistent_fulltext_id' in self.settings
                and self.settings['use_nonpersistent_fulltext_id']):
            metadata['fulltext_id'] = str(self.nonpersistentID)
            self.nonpersistentID += random.randint(1, 100)
        self.lastDocMeta = metadata
        fIn.close()
        self.insert_meta_year(metadata)
        return metadata

    def insert_doc_level_meta(self, sentence):
        """
        Copy some document-level metadata into the sentence-level
        metadata dictionary, if it is not already there. This is
        needed for sorting. At the moment, this includes year_from.
        """
        if self.lastDocMeta is None or 'year_from' not in self.lastDocMeta:
            return
        if 'meta' not in sentence:
            sentence['meta'] = {}
        if 'year' in sentence['meta']:
            return
        sentence['meta']['year'] = self.lastDocMeta['year_from']

    def get_sentences(self, fname):
        """
        If the file is not too large, iterate through its
        sentences.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return
        self.get_metadata(fname)
        if self.format == 'json':
            fIn = open(fname, 'r', encoding='utf-8-sig')
        elif self.format == 'json-gzip':
            fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
        else:
            return {}, True
        try:
            doc = json.load(fIn)
            fIn.close()
            for i in range(len(doc['sentences'])):
                self.insert_doc_level_meta(doc['sentences'][i])
                if i < len(doc['sentences']) - 1:
                    yield doc['sentences'][i], False
                else:
                    yield doc['sentences'][i], True
                    return
        except MemoryError:
            print('Memory error when reading', fname, ', trying iterative JSON parser (will work slowly).')
            fIn.close()
            if self.format == 'json':
                fIn = open(fname, 'r', encoding='utf-8-sig')
            elif self.format == 'json-gzip':
                fIn = gzip.open(fname, 'rt', encoding='utf-8-sig')
            else:
                return {}, True
            prevSent = {}
            for sentence in ijson.items(fIn, 'sentences.item'):
                self.insert_doc_level_meta(sentence)
                if prevSent != {}:
                    yield prevSent, False
                prevSent = sentence
            fIn.close()
            yield prevSent, True
            return

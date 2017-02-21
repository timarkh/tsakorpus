import json
import os
import re


class PrepareData:
    """
    Contains functions called when preparing the data
    for indexing in the database.
    """
    SETTINGS_DIR = '../conf'
    rxBadField = re.compile('[^a-z0-9_]|^(?:lex|gr|wf|[wm]type|ana|sent_ids|id)$')

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'word_fields.json'),
                 'r', encoding='utf-8')
        self.wordFields = json.loads(f.read())
        f.close()
        f = open(os.path.join(self.SETTINGS_DIR, 'categories.json'),
                 'r', encoding='utf-8')
        self.categories = json.loads(f.read())
        f.close()

    def generate_words_mapping(self):
        """
        Return Elasticsearch mapping for the type "word", based
        on searchable features described in word_fields.json and
        categories.json.
        """
        m = {'wf': {'type': 'text'},
             'wtype': {'type': 'keyword'},
             'sent_ids': {'type': 'integer', 'index': False},
             'ana': {'type': 'nested',
                     'properties': {'lex': {'type': 'text'}}}
             }
        for field in self.wordFields:
            if self.rxBadField.search(field) is None:
                m['ana']['properties'][field] = {'type': 'text'}
        for field in set(self.categories.values()):
            if self.rxBadField.search(field) is None:
                m['ana']['properties']['gr.' + field] = {'type': 'keyword'}
        return m

    def generate_mappings(self):
        """
        Return Elasticsearch mappings for all types to be used
        in the corpus database.
        """
        mWord = {'properties': self.generate_words_mapping()}
        mappings = {'mappings': {'word': mWord}}
        return mappings

    def write_mappings(self, fnameOut):
        """
        Generate and write Elasticsearch mappings for all types to be used
        in the corpus database.
        """
        fOut = open(fnameOut, 'w', encoding='utf-8')
        fOut.write(json.dumps(self.generate_mappings(), indent=2,
                              ensure_ascii=False))
        fOut.close()


if __name__ == '__main__':
    pd = PrepareData()
    pd.write_mappings('mappings.json')

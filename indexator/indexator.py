import elasticsearch
import json
import os
from prepare_data import PrepareData


class Indexator:
    """
    Contains methods for loading the data in the corpus
    database.
    """
    SETTINGS_DIR = '../conf'

    def __init__(self):
        f = open(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                 'r', encoding='utf-8')
        self.settings = json.loads(f.read())
        f.close()
        self.pd = PrepareData()

    def load_corpus(self):
        """
        Drop the current database, if any, and load the entire corpus.
        """
        pass


if __name__ == '__main__':
    x = Indexator()

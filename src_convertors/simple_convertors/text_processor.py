import os
import re
import json
import copy
from .text_cleaner import TextCleaner
from .tokenizer import Tokenizer
from .sentence_splitter import Splitter
from .analyzer import DumbMorphParser


class TextProcessor:
    """
    Contains mathods for turning a string into a list of sentences.
    """

    def __init__(self, settings, categories, errorLog=''):
        self.settings = copy.deepcopy(settings)
        self.categories = copy.deepcopy(categories)
        self.cleaner = TextCleaner(settings=self.settings)
        self.tokenizer = Tokenizer(settings=self.settings)
        self.splitter = Splitter(settings=self.settings)
        self.parser = DumbMorphParser(settings=self.settings,
                                      categories=self.categories,
                                      errorLog=errorLog)

    def process_string(self, s, lang=''):
        """
        Turn a string into a list of JSON sentences.
        Return the list and the statistics (number of words etc.).
        """
        s = self.cleaner.clean_text(s)
        tokens = self.tokenizer.tokenize(s)
        sentences = self.splitter.split(tokens, s)
        self.cleaner.clean_tokens(tokens)
        nTokens, nWords, nAnalyzed = self.parser.analyze(sentences, lang=lang)
        return sentences, nTokens, nWords, nAnalyzed

    @staticmethod
    def restore_sentence_text(words):
        """
        Restore sentence text as a string based on a list
        of JSON words it consists of. Indert start and end
        offset in each JSON word. Return the text of the
        sentence.
        This function is used when converting source formats
        that do not store the sentence text independently of
        the words.
        """
        text = ''
        for word in words:
            if 'wf' not in word:
                continue
            word['off_start'] = len(text)
            if word['wtype'] == 'word':
                text += word['wf'] + ' '
                word['off_end'] = len(text) - 1
            elif word['wtype'] == 'punctl':
                text += word['wf']
                word['wtype'] = 'punct'
                word['off_end'] = len(text)
            elif word['wtype'] == 'punctr':
                if text.endswith(' '):
                    word['off_start'] -= 1
                    text = text[:-1]
                text += word['wf'] + ' '
                word['wtype'] = 'punct'
                word['off_end'] = len(text) - 1
            else:
                if word['wf'].startswith(('(', '[', '{', '<', '“')):
                    text += word['wf']
                    word['off_end'] = len(text)
                elif word['wf'].startswith((')', ']', '}', '>', '.', ',', '?', '!', '”', '…')):
                    if text.endswith(' '):
                        word['off_start'] -= 1
                        text = text[:-1]
                    text += word['wf'] + ' '
                    word['off_end'] = len(text) - 1
                else:
                    text += word['wf'] + ' '
                    word['off_end'] = len(text) - 1
        return text.rstrip()

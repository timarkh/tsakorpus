import json
import os

FNAME = '/home/maryszmary/Downloads/adygvoice-2012-05-21.prs'

class EANCDocReader():
    """the class for converting texts from EANC format"""
    def __init__(self):
        self.filesize_limit = -1
        self.meta = {}
        self.sentences = []

    def process_text(self):
        with open(self.fname, 'r', encoding='utf-8-sig') as f:
            text = f.read().split('\n')
        self.head = text[1].split('\t')
        sentences = [li for li in text if not li.startswith('#') and li!= '']
        self.extract_sentences(sentences)

    def extract_sentences(self, sentences):
        for word in sentences:
            num, content = tuple(word.split('\t', 1))
            if int(num) == len(self.sentences) - 1:
                self.sentences[int(num)] += [content]
            else:
                self.sentences.append([content])
        self.form_sentences()

    def form_sentences(self):
        for i in range(len(self.sentences)):
            sent = Sentence(i, self.sentences[i])
            self.sentences[i] = sent.content

    def get_sentences(self, fname):
        """
        If the file is not too large, iterate through its
        sentences.
        """
        if os.stat(fname).st_size > self.filesize_limit > 0:
            return None
        self.fname = fname
        self.process_text()
        for i in range(len(self.sentences)):
            isFinal = i == len(self.sentences) - 1
            yield self.sentences[i], isFinal

    def get_meta(self, fname):
        self.fname = fname
        with open(self.fname, 'r', encoding='utf-8-sig') as f:
            text = f.read().split('\n')[1:]
        meta = {}
        for line in text:
            if line.startswith('#meta.'):
                attr_name, value = tuple(line.split('\t'))
                attr_name = attr_name.split('.')[1]
                meta[attr_name] = value
            else:
                break
        return meta


class WordForm():
    """
    extract analyses for one worform
    """
    def __init__(self, data):
        self.data = [data]
        
        

class Sentence():
    """docstring for Sentence"""
    def __init__(self, ID, content):
        self.ID = ID
        self.words = []
        self.form_words(content)
        self.form_content()

    def form_words(self, content):
        for line in content:
            num, word_data = tuple(line.split('\t', 1))
            num = int(num)
            word_data = word_data.split('\t')
            if num == len(self.word):
                self.words.append(WordForm(num, word_data))
            elif num == len(self.word) - 1:
                self.words[-1].data.append(word_data)
            else:
                print('SOMETHING GONE WRONG WHILE ANALYSING WF ' + str(word_data))

    def form_content(self):
        pass


if __name__ == '__main__':
    reader = EANCDocReader()
    # print(reader.get_meta(FNAME))
    for i in reader.get_sentences(FNAME):
        print(i)

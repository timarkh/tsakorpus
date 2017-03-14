import json
import os

FNAME = '/home/maryszmary/Downloads/adygvoice-2012-05-21.prs'
# FNAME = '/home/maryszmary/Downloads/20040123.prs'

## TODO: do something about the punctuation
## проблема: невозможно сохранить исходную индексацию, если считать знаки пунктуации токенами.

class EANCDocReader():
    """the class for converting texts from EANC format"""
    def __init__(self):
        self.filesize_limit = -1
        self.meta = {}
        self.sentences = []

    def process_text(self):
        with open(self.fname, 'r', encoding='utf-8-sig') as f:
            text = f.read().split('\n') 

        # first 2 elements are cut off, bc they are about id, the last bc the information is redundant 
        self.head = text[0].replace('#', '').split('\t')[2:-1] 
        sentences = [li for li in text if not li.startswith('#') and li != '']
        self.extract_sentences(sentences)

    def extract_sentences(self, sentences):
        for word in sentences:
            num, content = tuple(word.split('\t', 1))
            if int(num) == len(self.sentences) - 1:
                self.sentences[int(num)] += [content]
            else:
                self.sentences.append([content])
        print('head: ' + str(self.head))
        for i in range(len(self.sentences)):
            sent = Sentence(i, self.sentences[i], self.head)
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
    def __init__(self, data, head):
        self.wtype = 'word'
        self.head = head
        self.data = [data]
        self.wf = data[2]

    def form_content(self):
        self.anas = []
        for line in self.data:
            if len(line) < len(self.head):
                self.head = self.head[:-1]
            ana = {pair[0] : pair[1] for pair in zip(self.head, line)}
            self.anas.append(ana)
        self.content = {'ana' : self.anas, 'wf': self.wf, 'off_end' : None, 
                        'off_start' : None}


    def start_and_end(self):
        return prev_end + 1, prev_end + 1 + len(self.wf)


class Punct():
    def __init__(self, wf):
        self.wf = wf
        self.wtype = 'punct'

    def start_and_end(self, prev_end):
        return prev_end, prev_end + len(self.wf)
        

class Sentence():
    """docstring for Sentence"""
    def __init__(self, ID, content, head):
        self.ID = ID
        self.head = head
        self.words = []
        self.form_words(content)
        self.form_content()

    def form_words(self, content):
        for line in content:
            num, word_data = tuple(line.split('\t', 1))
            num = int(num)
            # print(word_data)
            word_data = word_data.split('\t')[:-1]
            # print('HEAD: ' + str(self.head))
            if num == len(self.words) + 1:
                self.words.append(WordForm(word_data, self.head))
            elif num == len(self.words):
                self.words[-1].data.append(word_data)
            else:
                print('SOMETHING GONE WRONG WITH LINE ' + str(line))

    def reach_punctuation(self):
        i = 0
        while i < len(self.words):
            if self.words[i].wtype == 'word':
                if self.words[i].content['punctl']\
                   and (i == 0 or self.words[i].content['punctl'] != self.words[i - 1].wf):
                   self.words.insert(i, Punct(self.words[i].content['punctl']))
                elif self.words[i].content['punctr']:
                    self.words.insert(i + 1, Punct(self.words[i].content['punctr']))
                i += 1

    def form_content(self):
        for i in range(len(self.words)):
            self.words[i].form_content()
        self.text = ' '.join([word.wf for word in self.words])
        # self.reach_punctuation()
        self.content = {'text' : self.text, 'words': 
                        [w.content for w in self.words]}


if __name__ == '__main__':
    reader = EANCDocReader()
    # print(reader.get_meta(FNAME))
    # i = 0
    for pair in reader.get_sentences(FNAME):
        print(pair[0]['text'])
    #     for word in pair[0]['words']:
    #         print(word['ana'])
    #     i += 1
    #     if i > 10:
    #         break

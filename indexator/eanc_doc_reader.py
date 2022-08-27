import json
import os


class EANCDocReader:
    """
    the class for converting texts from EANC format
    """
    def __init__(self):
        self.filesize_limit = -1
        self.meta = {}
        self.sentences = []

    def process_text(self):
        """
        Reads the file with the corpus, reads header separates sentences
        from metadata. Calls extract_sentences.
        """
        with open(self.fname, 'r', encoding='utf-8-sig') as f:
            text = f.read().split('\n') 

        # first 2 elements are cut off, bc they are about id,
        # the last bc the information is redundant 
        self.head = text[0].replace('#', '').split('\t')[2:-1] 
        sentences = [li for li in text if not li.startswith('#') and li != '']
        self.extract_sentences(sentences)

    def extract_sentences(self, sentences):
        """
        Takes a list of unprocessed tokens from prs corpus
        """
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


class WordForm:
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
            # if len(line) < len(self.head):
            #     self.head = self.head[:-1]
            ana = {pair[0] : pair[1] for pair in zip(self.head, line)}
            self.anas.append(ana)
        self.content = {'ana' : self.anas, 'wf': self.wf, 'off_end' : None, 
                        'off_start' : None, 'wtype': self.wtype}

    def start_and_end(self, prev_end):
        self.content['off_start'] = prev_end + 1
        self.content['off_end'] = prev_end + 1 + len(self.wf)
        return prev_end + 1 + len(self.wf)

    def unify_analyses(self):
        """
        making analysis attributes valid. currently is in TODO state. Tim!
        """

        # removing redundant attributes
        redundant = ['punctl', 'punctr']
        for i in range(len(self.content['ana'])):
            for attr in redundant:
                if attr in self.content['ana'][i]:
                    self.content['ana'][i].pop(attr)

        # removing empty analyses
        if len(self.content['ana']) == 1:
            if self.content['ana'][0]['nlems'] == '0':
                self.content['ana'] = []


class Punct:
    """
    class for punctuation. a Punct object is like a WordForm object,
    but has no analyses 
    """
    def __init__(self, wf):
        self.wf = wf if wf != '\\n' else '\n'
        self.wtype = 'punct'
        self.content = {'wf': self.wf, 'off_end': None,
                        'off_start': None, 'wtype': self.wtype}

    def start_and_end(self, prev_end):
        length = len(self.wf)
        self.content['off_start'] = prev_end
        self.content['off_end'] = prev_end + length
        return prev_end + len(self.wf)
        

class Sentence:
    """
    a Sentence object is a representation of a corpus sentence.
    takes ID, a list of lines (each line for one token) and the header.
    the json structure required for the corpus is stored in self.content. 
    """
    def __init__(self, ID, content, head):
        self.ID = ID
        self.head = head
        self.words = []
        self.form_words(content)
        self.form_content()

    def form_words(self, content):
        """
        fills the sentence with tokens. iterates through lines
        and separates and builds the wordforms. 
        """
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
        """
        extracts punctuation: iterates all the wordforms 
        and if it seessome punctuation in them, 
        creates an object of class Punct and adds it to the list 
        """
        i = 0
        while i < len(self.words):
            if self.words[i].wtype == 'word':
                punctl = self.words[i].content['ana'][0]['punctl']
                punctr = self.words[i].content['ana'][0]['punctr']
                if punctl and (i == 0 or punctl != self.words[i - 1].wf):
                    self.words.insert(i, Punct(punctl))
                    i += 1
                elif punctr:
                    self.words.insert(i + 1, Punct(punctr))
                    i += 1
            i += 1

    def make_start_and_end(self):
        prev_end = self.words[0].start_and_end(0)
        for i in range(1, len(self.words)):
            prev_end = self.words[i].start_and_end(prev_end)

    def make_text(self):
        self.text = self.words[0].wf
        for token in self.words[1:]:
            if token.wtype == 'word':
                self.text += ' '
            self.text += token.wf

    def clean_analyses(self):
        for i in range(len(self.words)):
            if self.words[i].wtype == 'word':
                self.words[i].unify_analyses()

    def form_content(self):
        for i in range(len(self.words)):
            self.words[i].form_content()
        self.reach_punctuation()
        self.make_start_and_end()
        self.make_text()
        self.make_start_and_end()
        self.clean_analyses()
        self.content = {'text' : self.text, 'words': 
                        [w.content for w in self.words]}



if __name__ == '__main__':
    # FNAME = '/home/maryszmary/Downloads/adygvoice-2012-05-21.prs'
    FNAME = '/home/maryszmary/Downloads/20040123-test.prs'
    sentences = []
    reader = EANCDocReader()
    # print(reader.get_meta(FNAME))
    i = 0
    for pair in reader.get_sentences(FNAME):
        sentences.append(pair[0])
        # print(pair[0]['text'])
        # print(pair[0])
        # # for word in pair[0]['words']:
        # #     print(word)
        i += 1
        if i > 10:
            break
    f = open(FNAME.rsplit('.', 1)[0] + '.json', 'w', encoding='utf-8')
    sentences = json.dumps(sentences, ensure_ascii=False, indent=4)
    f.write(sentences)
    f.close()

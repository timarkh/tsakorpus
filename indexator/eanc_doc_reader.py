import json

class EANCDocReader():
    """the class for converting texts from EANC format"""
    def __init__(self):
        self.filesize_limit = -1
        self.meta = {}
        self.sentences = []

    def process_text(self):
        with open(self.fname) as f:
            text = f.read().split('\n')
        meta, sentences = [], []
        for line in text:
            if line.startswith('#'):
                meta += line
            else:
                sentences += line
        self.extract_meta(meta)
        self.extract_sentences(sentences)

    def extract_meta(self, meta):
        pass

    def extract_sentences(self, sentences):
        for word in sentences:
            num, content = tuple(word.split('\t', 1)[1])
            content = self.analyze_word(content)
            if int(num) == len(self.sentences) - 1:
                self.sentences[num] += content
            else:
                self.sentences.append(content)

    def analyze_word(self, content):
        # return content
        pass

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
            final = i == len(self.sentences) - 1
            yield self.sentences[i], final

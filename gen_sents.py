from gen_wfms_with_repr import WordformGenerator
from gen_ready_wfms import MockMorphParser
import random
import numpy as np
import json
import time


class Sentence:
    def __init__(self):
        self.text = ''
        self.words = []

    def __len__(self):
        return len(self.words)


class Punctuation:
    def __init__(self, text):
        self.wf = text
        self.type = 'punct'

    
class CorpusGenerator:
    """
    object of this class, when created, generates corpus
    out of WordForm class objects and some random puctuation
    """
    def __init__(self, settings):
        self.settings = settings
        self.generate_sents()

    def create_full_wordforms(self):
        """
        returns wordforms with analyses
        """
        f = open('settings.json', 'r', encoding='utf-8')
        settings = json.loads(f.read())
        f.close()
        generator = WordformGenerator(settings)
        mp = MockMorphParser(settings, 30000)
        n = 0
        for wf in generator.wordforms:
            n += mp.add_analysis(wf)
        print(n / len(generator.wordforms))
        return generator.wordforms

    def final_sent(self, sent_arr):
        """
        returns an object of Sentence class
        """
        sent = Sentence()
        text = ''
        punct = np.random.choice([0, 1], len(sent_arr), p=[0.9, 0.1])
        offset = 0
        for i,item in enumerate(sent_arr):
            item.off_start = offset
            offset += len(item.wf)
            item.off_end = offset
            try: #delete frequency attribute
                delattr(item,'freq')
            except:
                pass
            sent.words.append(item.__dict__)
            text += item.wf
            if punct[i] and i != len(sent_arr) - 1:
                punc_item = Punctuation(np.random.choice([';', ',', ':']))
                punc_item.off_start = offset
                offset += 1
                punc_item.off_end = offset
                sent.words.append(punc_item.__dict__)
                text += punc_item.wf
            if i != len(sent_arr) - 1:
                text += ' '
            else:
                finalpunct = Punctuation(np.random.choice(['.', '!', '?'],
                                                          p=[0.7, 0.15, 0.15]))
                text += finalpunct.wf
                sent.words.append(finalpunct.__dict__)
        text = text[0].upper() + text[1:]
        sent.text = text
        return sent
    
    def generate_sents(self):
        """
        returns full corpus (array of objects of Sentence class)
        """
        self.sentences = []
        wfms = self.create_full_wordforms()
        full_list = [[x]*x.freq for x in wfms]
        full_list = [item for sublist in full_list for item in sublist]
        random.shuffle(full_list)
        prevlength = 0
        full_corp = len(full_list)
        mean = np.mean(np.log(self.settings['constants']['MEAN_SENT_LENGTH']))
        while full_list:
            length = int(np.round(np.random.lognormal(mean=mean)))
            while length > self.settings['constants']['MAX_SENT_LENGTH'] or length < 1:
                length = round(np.random.lognormal(mean=mean))
            if full_corp > prevlength+length:
                sentence = full_list[prevlength:prevlength+length]
                prevlength += length
            else:
                sentence = full_list[prevlength:]
                full_list = []
            self.sentences.append(self.final_sent(sentence))
        print('mean sentence length:', np.sum([len(x) for x in self.sentences]) / len(self.sentences))

    def write_json(self):
        """
        writes corpus to .json file
        """
        f = open('test_output/sentences.json', 'w', encoding='utf-8-sig')
        sentences = [x.__dict__ for x in self.sentences]
        f.write(json.dumps(sentences, indent=1, ensure_ascii=False))
        f.close()


if __name__ == '__main__':
    f = open('settings.json', 'r', encoding='utf-8')
    settings = json.loads(f.read())
    f.close()
    gen = CorpusGenerator(settings)
    gen.write_json()

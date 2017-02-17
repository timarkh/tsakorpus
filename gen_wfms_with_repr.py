import json
import math
import string
import random


class WordForm():
    """docstring for WordForm"""
    def __init__(self, freq):
        self.freq = freq


class WordformGenerator():
    '''
    the object of this class generates objects of WordForm class
    and gives them text representations
    '''
    def __init__(self,settings):
        self.settings = settings
        self.generate_final_wordforms()

        
    def generate_initial_wordforms(self):
        '''
        returns a list of wordforms (instances) with freqs
        '''
        n = self.calc_num_of_words()
        wfms_with_freq = []
        first = self.calc_f_0(n)
        for i in range(n//2):
            freq = first//(i + 1)
            #print('current_freq: ' + str(freq))
            wfms_with_freq.append(WordForm(freq))
        wfms_with_freq += [WordForm(1) for i in range(n - n//2)]
        print(sum([wf.freq for wf in wfms_with_freq]))
        print('number of wordforms:',n)
        return wfms_with_freq


    def calc_f_0(self,n):
        sum_of_row = 0
        i = n//2
        while i >= 1:
            sum_of_row += 1/i
            i -= 1
        return round((self.settings['constants']['LENGTH_OF_CORPUS'] - n/2)/sum_of_row)


    def calc_num_of_words(self):
        gamma = 0.577
        N_0 = self.settings['constants']['N_0']
        disc = 1/4 + 2 * self.settings['constants']['LENGTH_OF_CORPUS'] * ((math.log(N_0) + gamma + 1)/ N_0)
        n = 2 * (1/2 + math.sqrt(disc)) * N_0/(math.log(N_0) + gamma + 1)
        return round(n)


    def calc_lengths(self,wordlist):
        '''
        returns a list of mean wordform lengths (integers)
        '''
        a = self.settings['constants']['MEAN_WORD_LENGTH'] - 1
        b = 0.4
        lengths = []
        for word in wordlist:
            lengths.append(round(a*(word.freq**(-b)) + 1))
        return lengths

        
    def give_text_repr(self,wordlist,lengths):
        '''
        returns list of WordForm objects with text representation added
        '''
        reprs = set()
        for i,length in enumerate(lengths):
            lengthvars = [(4 - abs(i)) * [length + i] for i in range(-3, 4) if length + i >= 1]
            lengthvars = [item for sublist in lengthvars for item in sublist]
            le = random.choice(lengthvars)
            text = ''.join(random.choice(self.settings['constants']['ALPHABET']) for i in range(le))
            while text in reprs:
                le = random.choice(lengthvars)
                text = ''.join(random.choice(self.settings['constants']['ALPHABET']) for i in range(le))
            wordlist[i].text = text
            reprs.add(text)
        print('mean word length:',sum([len(x) for x in reprs]) / len(reprs))
        return wordlist


    def generate_final_wordforms(self):
        wfms = self.generate_initial_wordforms()
        self.wordforms = self.give_text_repr(wfms,self.calc_lengths(wfms))

            
if __name__ == '__main__':
    f = open('settings.json', 'r', encoding='utf-8')
    settings = json.loads(f.read())
    f.close()
    generator = WordformGenerator(settings)
    print(generator.wordforms[-1].freq,generator.wordforms[-1].text)

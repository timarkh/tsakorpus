import random
import math
import json


class MockMorphParser:
    """
    When created, an object of this class calculates the number
    of different lexemes based on the corpus size, generates the
    lexemes, and then works as a morphological parser, taking a
    Wordform object and adding analyses to it.
    """
    def __init__(self, settings, n_lexemes):
        self.settings = settings
        self.n_lexemes = n_lexemes
        lengths = [(3 - abs(i)) * [settings['constants']['MEAN_WORD_LENGTH'] + i]
                   for i in range(-2, 3)
                   if settings['constants']['MEAN_WORD_LENGTH'] + i >= 3]
        self.lengths = []
        for l in lengths:
            self.lengths += l
        self.pos = [gr for gr in settings['grammar']]
        self.generate_probabilities()
        self.generate_lexemes()

    @staticmethod
    def ddistr(probabilities):
        cdf = [(i, sum(p for j, p in probabilities
                       if j is None or (j is not None and i is not None and j < i)))
               for i, _ in probabilities]
        r = random.random()
        return max(i for i, c in cdf if (c <= r))

    def generate_probabilities(self):
        l = self.settings['constants']['MEAN_AMBIGUITY']
        self.prob = [(k, l ** k * math.exp(-l) / math.factorial(k))
                     for k in range(math.floor(l) * 4)]

    def one_lexeme(self):
        """
        Generate and return one random lexeme.
        """
        l = {}
        lLen = random.choice(self.lengths)
        l['lex'] = ''.join(random.choice(self.settings['constants']['ALPHABET'])
                           for i in range(lLen))
        l['pos'] = random.choice(self.pos)
        return l

    def generate_lexemes(self):
        """
        Generate random lexemes and store them in self.lexemes.
        """
        self.lexemes = [self.one_lexeme()
                        for _ in range(self.n_lexemes)]

    def add_analysis(self, wf):
        """
        Add a random analysis (or analyses) to a Wordform object.
        """
        n = MockMorphParser.ddistr(self.prob)
        # print(n)
        return n

if __name__ == '__main__':
    f = open('settings.json', 'r', encoding='utf-8')
    settings = json.loads(f.read())
    f.close()
    mp = MockMorphParser(settings, 30000)
    wf = {}
    n = 0
    for i in range(20):
        n += mp.add_analysis(wf)
    print(n / 20)

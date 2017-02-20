import random
import math
import json
import copy


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
        self.prob = {}
        l = self.settings['constants']['MEAN_AMBIGUITY']
        self.prob['n_ana'] = [(k, l ** k * math.exp(-l) / math.factorial(k))
                              for k in range(math.floor(l) * 5)]
        for pos in self.settings['grammar']:
            for cat in self.settings['grammar'][pos]:
                values = self.settings['grammar'][pos][cat]
                if len(values) < 8:
                    self.prob[cat] = [(v, 1 / len(values)) for v in values]
                else:
                    norm_coef = sum(1 / i for i in range(1, len(values) + 1))
                    self.prob[cat] = []
                    for i in range(len(values)):
                        self.prob[cat].append((values[i], 1 / (norm_coef * (i + 1))))
                print(cat, self.prob[cat])

    def one_lexeme(self):
        """
        Generate and return one random lexeme.
        """
        l = {}
        lLen = random.choice(self.lengths)
        l['lex'] = ''.join(random.choice(self.settings['constants']['ALPHABET'])
                           for i in range(lLen))
        l['gr'] = {'pos': random.choice(self.pos)}
        return l

    def generate_lexemes(self):
        """
        Generate random lexemes and store them in self.lexemes.
        """
        self.lexemes = [self.one_lexeme()
                        for _ in range(self.n_lexemes)]

    def get_random_cat_value(self, cat):
        return MockMorphParser.ddistr(self.prob[cat])

    def generate_analysis(self):
        lex = copy.deepcopy(random.choice(self.lexemes))
        for cat in self.settings['grammar'][lex['gr']['pos']]:
            lex['gr'][cat] = self.get_random_cat_value(cat)
        return lex

    def add_analysis(self, wf):
        """
        Add a random analysis (or analyses) to a Wordform object.
        """
        n = MockMorphParser.ddistr(self.prob['n_ana'])
        wf.ana = [self.generate_analysis()
                  for _ in range(n)]
        # print(n)
        return n

if __name__ == '__main__':
    f = open('settings.json', 'r', encoding='utf-8')
    settings = json.loads(f.read())
    f.close()
    mp = MockMorphParser(settings, 30000)
    from gen_wfms_with_repr import WordForm
    n = 0
    for i in range(20):
        wf = WordForm(1)
        n += mp.add_analysis(wf)
        print(wf.ana)
    print(n / 20)
    print(mp.lexemes[:30])
    print(len(set((l['lex'], l['gr']['pos']) for l in mp.lexemes)))

import re
import copy
import html


class TextCleaner:
    """
    Contains methods for cleaning a string from things like
    HTML entities etc.
    It is assumed that the cleaner can be language-dependent.
    """
    rxTags = re.compile('</?(?:a|img|span|div|p|body|html|head)(?: [^<>]+)?>|[\0⌐-♯]+',
                        flags=re.DOTALL)
    rxSpaces1 = re.compile(' {2,}| +|\t+|&nbsp;| ', flags=re.DOTALL)
    rxSpaces2 = re.compile('(?: *\n)+ *', flags=re.DOTALL)
    rxPuncWords = re.compile('([,!?:;·;·)\\]>])([\\w(\\[<])')
    rxQuotesL = re.compile('([\\s(\\[{<\\-])"([\\w\\-\'`´‘’‛@.,-‒–—―•])',
                           flags=re.DOTALL)
    rxQuotesR = re.compile('([\\w\\-\'`´‘’‛/@.,-‒–—―•,!?:;·;·])"([\\s)\\]}>\\-.,!])',
                           flags=re.DOTALL)
    rxNonstandardQuotesL = re.compile('[“]', flags=re.DOTALL)
    rxNonstandardQuotesR = re.compile('[”]', flags=re.DOTALL)

    rxCyrISmall = re.compile('(?<=[Ѐ-ԧ])i|i(?=[Ѐ-ԧ])')
    rxCyrIBig = re.compile('(?<=[Ѐ-ԧ])I|I(?=[Ѐ-ԧ])')
    rxCyrAeSmall = re.compile('(?<=[Ѐ-ԧ])æ|æ(?=[Ѐ-ԧ])')
    rxCyrAeBig = re.compile('(?<=[Ѐ-ԧ])Æ|Æ(?=[Ѐ-ԧ])')
    rxCyrSchwaSmall = re.compile('(?<=[Ѐ-ԧ])[ǝə]|[ǝə](?=[Ѐ-ԧ])')
    rxCyrSchwaBig = re.compile('(?<=[Ѐ-ԧ])Ə|Ə(?=[Ѐ-ԧ])')
    rxCyrHSmall = re.compile('(?<=[Ѐ-ԧ])h|h(?=[Ѐ-ԧ])')
    rxCyrHBig = re.compile('(?<=[Ѐ-ԧ])H|H(?=[Ѐ-ԧ])')

    dictDiacriticsUdm = {'и': 'ӥ', 'о': 'ӧ', 'ж': 'ӝ',
                         'з': 'ӟ', 'ч': 'ӵ', 'И': 'Ӥ',
                         'О': 'Ӧ', 'Ж': 'Ӝ', 'З': 'Ӟ', 'Ч': 'Ӵ'}
    rxDiacriticsUdm = re.compile('([иожзчИОЖЗЧ])([:"])(?=[а-яА-ЯёЁ?!])')
    rxUdmU2I = re.compile('(?<=[а-яА-Я])[ћbü]')
    rxUdmO2O = re.compile('(?<=[а-яА-ЯӜӞӴӝӟӵ])[ќö]|[ќö](?=[а-яА-ЯӜӞӴӝӟӵ])')
    rxUdmX2Ch = re.compile('(?<=[а-яА-ЯӜӞӴӝӟӵ])[џx]|[џx](?=[а-яА-ЯӜӞӴӝӟӵ])')
    rxUdmDzh = re.compile('(?<=[а-яА-ЯӜӞӴӝӟӵ])љ|љ(?=[а-яА-ЯӜӞӴӝӟӵ])')
    rxUdmZj = re.compile('(?<=[а-яА-ЯӜӞӴӝӟӵ])њ|њ(?=[а-яА-ЯӜӞӴӝӟӵ])')

    rxArmPeriod = re.compile('(?<![a-zA-Z ]):')
    rxArmIntraWordPunc = re.compile('[՞՜՛]')
    rxArmOldCond = re.compile('^կը +')

    rxRNCStress = re.compile('`(\\w)')
    rxModifierStress = re.compile('(\\w)́')

    def __init__(self, settings):
        self.settings = copy.deepcopy(settings)

    def clean_text(self, text, lang=''):
        """
        Main method that calls separate step-by-step procedures.
        """
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        text = self.convert_html(text)
        text = self.clean_spaces(text)
        text = self.separate_words(text, lang)
        if 'convert_quotes' in self.settings and self.settings['convert_quotes']:
            text = self.convert_quotes(text, lang)
        text = self.clean_other(text, lang)
        return text

    def convert_html(self, text):
        text = self.rxTags.sub('', text)  # deletes all tags in angle brackets
        text = html.unescape(text)
        return text

    def clean_spaces(self, text):
        text = self.rxSpaces1.sub(' ', text.strip())  # unify all spaces
        text = self.rxSpaces2.sub('\n ', text)  # normalize new lines
        return text

    def separate_words(self, text, lang=''):
        # punctuation inside a word
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        text = self.rxPuncWords.sub('\\1 \\2', text)  # adds a space between punctuation and next letter
        return text

    def convert_quotes(self, text, lang=''):
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        text = self.rxQuotesL.sub('\\1«\\2', text)
        text = self.rxQuotesR.sub('\\1»\\2', text)
        text = self.rxNonstandardQuotesL.sub(self.settings['left_quot_mark'], text)
        text = self.rxNonstandardQuotesR.sub(self.settings['right_quot_mark'], text)
        return text

    def clean_other(self, text, lang=''):
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        if lang == 'udmurt':
            text = self.rxDiacriticsUdm.sub(lambda m: self.dictDiacriticsUdm[m.group(1)], text)
            text = self.rxUdmU2I.sub('ӥ', text)
            text = self.rxUdmO2O.sub('ӧ', text)
            text = self.rxUdmX2Ch.sub('ӵ', text)
            text = self.rxUdmDzh.sub('ӝ', text)
            text = self.rxUdmZj.sub('ӟ', text)
        if lang in ['ukrainian', 'kazakh', 'komi']:
            text = self.rxCyrISmall.sub('і', text)
            text = self.rxCyrIBig.sub('І', text)
        if lang in ['kazakh', 'tatar', 'bashkir', 'kalmyk']:
            text = self.rxCyrHSmall.sub('һ', text)
            text = self.rxCyrHBig.sub('Һ', text)
        if lang in ['kazakh', 'tatar', 'bashkir']:
            text = self.rxCyrSchwaSmall.sub('ә', text)
            text = self.rxCyrSchwaBig.sub('Ә', text)
        if lang in ['ossetic', 'iron', 'digor']:
            text = self.rxCyrAeSmall.sub('ӕ', text)
            text = self.rxCyrAeBig.sub('Ӕ', text)
        if lang in ['armenian']:
            text = self.rxArmPeriod.sub('։', text)
        text = text.replace('…', '...')
        text = text.replace('\\r\\n', '\n')
        text = text.replace('\\n', '\n')
        text = text.replace('\\', '/')
        return text

    def clean_social_networks(self, text, lang=''):
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        text = re.sub('(?<=\\w)ааа+', 'а', text)
        text = re.sub('(?<=\\w)ооо+', 'о', text)
        text = re.sub('(?<=\\w)еее+', 'е', text)
        text = re.sub('(?<=\\w)ууу+', 'у', text)
        text = re.sub('(?<=\\w)иии+', 'у', text)
        text = re.sub('(?<=\\w)ыы+', 'ы', text)
        text = re.sub('(?<=\\w)ээ+', 'э', text)
        if lang == 'udmurt':
            text = self.rxDiacriticsUdm.sub(lambda m: self.dictDiacriticsUdm[m.group(1)], text)
            text = self.rxUdmU2I.sub('ӥ', text)
            text = self.rxUdmO2O.sub('ӧ', text)
            text = self.rxUdmX2Ch.sub('ӵ', text)
            text = self.rxUdmDzh.sub('ӝ', text)
            text = self.rxUdmZj.sub('ӟ', text)
            text = re.sub('(?<=\\w)ӧӧ+', 'ӧ', text)
            text = re.sub('(?<=\\w)ӥӥ+', 'ӥ', text)
        return text

    def clean_token(self, text, lang=''):
        """
        Clean a token for search purposes (the baseline will
        still have the original, uncleaned version).
        """
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        wordClean = text
        if lang in ['armenian']:
            wordClean = self.rxArmIntraWordPunc.sub('', wordClean)
        return wordClean

    def clean_tokens(self, tokens, lang=''):
        """
        Clean token['wf'] for each token in the list. Change the list,
        do not return anything.
        """
        if len(lang) <= 0:
            lang = self.settings['languages'][0]
        for i in range(len(tokens)):
            if 'wf' in tokens[i] and tokens[i]['wtype'] == 'word':
                tokens[i]['wf'] = self.clean_token(tokens[i]['wf'])

    def clean_token_rnc(self, text):
        """
        Clean a token from things specific to the Russian National Corpus,
        such as stress marks.
        Return two versions of the token: one for the search, the other
        for the baseline.
        """
        wordClean = self.rxRNCStress.sub('\\1', text)
        wordClean = self.rxModifierStress.sub('\\1', wordClean)
        wordText = self.rxRNCStress.sub('\\1́', text)
        return wordClean, wordText

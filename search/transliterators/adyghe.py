import re

dictNgrams = {'кӏу': 'kʷʼ', 'кӏо': 'kʷʼe', 'шӏу': 'ʃʷʼ', 'шӏо': 'ʃʷʼe',
              'кӏ': 'tʃʼ', 'лӏ': 'ɬʼ', 'пӏо': 'pʷʼe', 'пӏу': 'pʷʼ',
              'пӏ': 'pʼ', 'тӏу': 'tʷʼ', 'тӏо': 'tʷʼe', 'цӏ': 'tsʼ',
              'чӏ': 'tʃʼ', 'къ': 'q', 'дзу': 'dzʷ', 'дзо': 'dzʷe',
              'гъу': 'ʁʷ', 'гъо': 'ʁʷe', 'жъу': 'ʐʷ', 'жъо': 'ʐʷe',
              'къу': 'qʷ', 'къо': 'qʷe', 'хъу': 'χʷ', 'хъо': 'χʷe',
              'шъу': 'ʂʷ', 'шъо': 'ʂʷe', 'ӏу': 'ʔʷ', 'ӏо': 'ʔʷe',
              'гу': 'ɡʷ', 'го': 'ɡʷe', 'гъ': 'ʁ', 'дж': 'dʒ',
              'дз': 'dz', 'жь': 'ʑ', 'жъ': 'ʐ', 'лъ': 'ɬ',
              'тӏ': 'tʼ', 'хъ': 'χ', 'чъ': 'tʂ', 'шъ': 'ʂ',
              'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g',
              'д': 'd', 'е': 'je', 'ё': 'jo', 'ж': 'ʒ',
              'з': 'z', 'и': 'jə', 'й': 'j', 'ӏ': 'ʔ',
              'к': 'k', 'л': 'ɮ', 'м': 'm', 'н': 'n',
              'о': 'we', 'п': 'p', 'р': 'r', 'с': 's',
              'т': 't', 'у': 'wə', 'ф': 'f', 'х': 'x',
              'ц': 'ts', 'ч': 'tʃ', 'ш': 'ʃ', 'щ': 'ɕ',
              'ъ': 'j', 'ы': 'ə', 'ь': 'ʲ', 'э': 'e',
              'ю': 'ju', 'я': 'ja', 'ку': 'kʷ', 'ко': 'kʷe', 'хь': 'ħ'}

for k in list(dictNgrams.keys()):
    dictNgrams[k.upper()] = dictNgrams[k].upper()
    if len(k) > 1:
        for i in range(len(k)):
            if k[i].upper() == k[i]:
                continue
            kUpper = k[:i] + k[i].upper() + k[i+1:]
            dictNgrams[kUpper] = dictNgrams[k][0].upper() + dictNgrams[k][1:]

rxAdygheCyr2IPA = re.compile('(?:' + '|'.join(k for k in sorted(dictNgrams,
                                                                key=lambda x: -len(x))) + ')')


def adyghe_translit_ipa(text):
    """
    Transliterate Adyghe text from Cyrillic orthography to IPA.
    """
    return rxAdygheCyr2IPA.sub(lambda m: dictNgrams[m.group(0)], text)


def adyghe_input_normal(field, text):
    """
    Prepare a string from one of the qury fields for subsequent
    processing: replace common shortcuts with valid Adyghe characters.
    """
    if field not in ('wf', 'lex', 'lex2', 'trans_ru', 'trans_ru2'):
        return text
    text = re.sub('(?<=[а-яА-ЯёЁӏ])[I1]', 'ӏ', text)
    text = re.sub('[I1](?=[а-яА-ЯёЁӏ])', 'ӏ', text)
    if '*' not in text or re.search('[\\[\\]\\.()]', text) is not None:
        text = text.replace('уэ', '(о|уэ)')
    return text

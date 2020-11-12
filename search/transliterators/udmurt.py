import re

dic2cyr = {'a': 'а', 'b': 'б', 'v': 'в',
           'g': 'г', 'd': 'д', 'e': 'э',
           'ž': 'ж', 'š': 'ш', 'e̮': 'ӧ',
           'ə': 'ө', 'ǯ́': 'ӟ', 'ǯ': 'ӝ', 'č́': 'ч', 'č': 'ӵ',
           'z': 'з', 'i': 'ӥ', 'j': 'й', 'k': 'к',
           'l': 'л', 'm': 'м', 'n': 'н',
           'o': 'о', 'p': 'п', 'r': 'р',
           's': 'с', 't': 'т', 'u': 'у',
           'c': 'ц', 'w': 'ў', 'x': 'х',
           'f': 'ф', 'i̮': 'ы'}
cyr2dic = {v: k for k, v in dic2cyr.items()}
cyr2dic.update({'я': 'ʼa', 'е': 'ʼe', 'и': 'ʼi',
                'ё': 'ʼo', 'ю': 'ʼu', 'ь': 'ʼ', 'щ': 'šʼ'})
cyrHard2Soft = {'а': 'я', 'э': 'е', 'е': 'е', 'ӥ': 'и', 'о': 'ё', 'у': 'ю'}
rxSoften = re.compile('(?<![чӟ])ʼ([аэӥоу])', flags=re.I)
rxCyrSoften = re.compile('([čǯ])(?!ʼ)', flags=re.I)
rxCyrMultSoften = re.compile('ʼ{2,}')
rxNeutral1 = re.compile('(?<=[бвгжкмпрфхцчшщйʼ])([эӥ])', re.I)
rxNeutral2 = re.compile('([бвгжкмпрфхцчʼаоэӥуўяёеиюө]|\\b)(ӥ)', re.I)
rxCyrNeutral = re.compile('(?<=[bvgzkmprfxcwj])ʼ', re.I)
rxCJV = re.compile('(?<=[бвгджзӟклмнпрстўфхцчшщ])й([аяэеӥоёую])', re.I)
rxSh = re.compile('ш(?=[ʼяёюиеЯЁЮИЕ])')
rxZh = re.compile('ж(?=[ʼяёюиеЯЁЮИЕ])')
rxShCapital = re.compile('Ш(?=[ʼяёюиеЯЁЮИЕ])')
rxZhCapital = re.compile('Ж(?=[ʼяёюиеЯЁЮИЕ])')
rxVJV = re.compile('(?<=[аеёиӥоӧөуыэюяʼ])й([аэоу])', flags=re.I)
rxJV = re.compile('\\bй([аэоу])')
rxJVCapital = re.compile('\\bЙ([аэоуАЭОУ])')
rxCyrVJV = re.compile('([aeiouɨəɤ])ʼ([aeouɨəɤ])')
rxCyrVSoft = re.compile('([aeiouɨəɤ]|\\b)ʼ')
rxCyrJV = re.compile('\\bʼ([aeouɨəɤ])')
rxExtraSoft = re.compile('([дзлнст])ь\\1(?=[ьяеёию])')
rxCyrExtraSoft = re.compile('([džlnšt])\\1(?=ʼ)')


cyrReplacements = {}
srcReplacements = {}


def udmurt_translit_upa(text):
    """
    Transliterate Udmurt text from Cyrillic script to Latin UPA.
    """
    text = text.replace('жи', 'жӥ')
    text = text.replace('ӝи', 'ӝӥ')
    text = text.replace('ӟи', 'ӟӥ')
    text = text.replace('чи', 'чӥ')
    text = text.replace('ӵи', 'ӵӥ')
    text = text.replace('ши', 'шӥ')
    text = text.replace('же', 'жэ')
    text = text.replace('ӝе', 'ӝэ')
    text = text.replace('ӟе', 'ӟэ')
    text = text.replace('че', 'чэ')
    text = text.replace('ӵе', 'ӵэ')
    text = text.replace('ше', 'шэ')
    text = text.replace('Жи', 'Жӥ')
    text = text.replace('Ӝи', 'Ӝӥ')
    text = text.replace('Ӟи', 'Ӟӥ')
    text = text.replace('Ши', 'Шӥ')
    text = text.replace('Же', 'Жэ')
    text = text.replace('Ӝе', 'Ӝэ')
    text = text.replace('Ӟе', 'Ӟэ')
    text = text.replace('Че', 'Чэ')
    text = text.replace('Ӵе', 'Ӵэ')
    text = text.replace('Ше', 'Шэ')

    letters = []
    for letter in text:
        if letter.lower() in cyr2dic:
            if letter.islower():
                letters.append(cyr2dic[letter.lower()])
            else:
                letters.append(cyr2dic[letter.lower()].upper())
        else:
            letters.append(letter)
    res = ''.join(letters)
    res = rxCyrVJV.sub('\\1j\\2', res)
    res = rxCyrJV.sub('j\\1', res)
    res = res.replace('ъʼ', 'j')
    res = res.replace('sʼ', 'šʼ')
    res = res.replace('zʼ', 'žʼ')
    res = rxCyrNeutral.sub('', res)
    res = rxCyrExtraSoft.sub('\\1ʼ\\1', res)
    res = res.replace('sšʼ', 'šʼšʼ')
    res = res.replace('zžʼ', 'žʼžʼ')
    res = rxCyrMultSoften.sub('ʼ', res)
    res = rxCyrVSoft.sub('\\1', res)
    res = res.replace('šʼ', 'ś')
    res = res.replace('žʼ', 'ź')
    res = res.replace('čʼ', 'č́')
    res = res.replace('nʼ', 'ń')
    res = res.replace('Šʼ', 'Ś')
    res = res.replace('Žʼ', 'Ź')
    res = res.replace('Čʼ', 'Č́')
    res = res.replace('Nʼ', 'Ń')
    return res

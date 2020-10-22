import re

dic2cyr = {'a': 'а', 'b': 'б', 'v': 'в',
           'g': 'г', 'd': 'д', 'e': 'э',
           'ž': 'ж', 'š': 'ш', 'ɤ': 'ӧ',
           'ə': 'ө', 'ǯ': 'ӟ', 'č': 'ч',
           'z': 'з', 'i': 'ӥ', 'j': 'й', 'k': 'к',
           'l': 'л', 'm': 'м', 'n': 'н',
           'o': 'о', 'p': 'п', 'r': 'р',
           's': 'с', 't': 'т', 'u': 'у',
           'c': 'ц', 'w': 'ў', 'x': 'х',
           'y': 'ы', 'f': 'ф', 'ɨ': 'ы'}
cyr2dic = {v: k for k, v in dic2cyr.items()}
cyr2dic.update({'я': 'ʼa', 'е': 'ʼe', 'и': 'ʼi',
                'ё': 'ʼo', 'ю': 'ʼu', 'ь': 'ʼ', 'ы': 'ɨ', 'у': 'u'})
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
rxCyrW = re.compile('(\\b|[кр])у(?=[аоэи])')

rxCyrillic = re.compile('^[а-яёӟӥӧўөА-ЯЁӞӤӦЎӨ.,;:!?\-()\\[\\]{}<>]*$')

cyrReplacements = {}
srcReplacements = {}


def beserman_translit_cyrillic(text):
    """
    Transliterate Beserman text from dictionary Latin script to the Cyrillics.
    """
    if rxCyrillic.search(text) is not None:
        return text

    letters = []
    for letter in text:
        if letter.lower() in dic2cyr:
            if letter.islower():
                letters.append(dic2cyr[letter.lower()])
            else:
                letters.append(dic2cyr[letter.lower()].upper())
        else:
            letters.append(letter)
    res = ''.join(letters)
    res = res.replace('h', 'х')
    res = res.replace('H', 'Х')
    res = rxSoften.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxSh.sub('с', res)
    res = rxZh.sub('з', res)
    res = rxShCapital.sub('С', res)
    res = rxZhCapital.sub('З', res)
    res = rxVJV.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxVJV.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxJV.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxJVCapital.sub(lambda m: cyrHard2Soft[m.group(1).lower()].upper(), res)
    res = rxNeutral1.sub(lambda m: cyrHard2Soft[m.group(1).lower()], res)
    res = rxNeutral2.sub('\\1и', res)
    res = rxCJV.sub(lambda m: 'ъ' + cyrHard2Soft[m.group(1).lower()], res)
    res = res.replace('ӟʼ', 'ӟ')
    res = res.replace('Ӟʼ', 'Ӟ')
    res = res.replace('чʼ', 'ч')
    res = res.replace('Чʼ', 'Ч')
    res = res.replace('ʼ', 'ь')
    res = rxExtraSoft.sub('\\1\\1', res)

    if res in cyrReplacements:
        res = cyrReplacements[res]
    return res


def beserman_translit_upa(text):
    text = text.replace("'", 'ʼ')
    text = text.replace('ə', 'ə̑')
    text = text.replace('Ə', 'Ə̑')
    text = text.replace('ɤ', 'e̮')
    text = text.replace('ɨ', 'i̮')
    text = text.replace('Ɨ', 'I̮')
    text = text.replace('čʼ', 'č́')
    text = text.replace('Čʼ', 'Č́')
    text = text.replace('ǯʼ', 'ǯ́')
    text = text.replace('Ǯʼ', 'Ǯ́')
    text = text.replace('šʼ', 'ś')
    text = text.replace('Šʼ', 'Ś')
    text = text.replace('žʼ', 'ź')
    text = text.replace('Žʼ', 'Ź')
    text = text.replace('dʼ', 'd́')
    text = text.replace('Dʼ', 'D́')
    text = text.replace('tʼ', 't́')
    text = text.replace('Tʼ', 'T́')
    text = text.replace('lʼ', 'ĺ')
    text = text.replace('Lʼ', 'Ĺ')
    text = text.replace('nʼ', 'ń')
    text = text.replace('Nʼ', 'Ń')
    text = text.replace('ʼ', '̓')
    return text

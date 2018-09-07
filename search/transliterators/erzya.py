import re

cyr2upa = {'я': 'ʼa', 'е': 'ʼe', 'ѣ': 'ʼe', 'и': 'ʼi',
           'ё': 'ʼo', 'ю': 'ʼu', 'ь': 'ʼ', 'і': 'ʼi',
           'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g',
           'д': 'd', 'ж': 'ž', 'з': 'z', 'к': 'k',
           'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
           'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
           'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'c',
           'ч': 'č', 'ш': 'š', 'щ': 'štʼ', 'ъ': 'j',
           'ы': 'i̮', 'э': 'e', 'й': 'j', 'ҥ': 'n', 'ѳ': 'f'}
rxYer = re.compile('ъ+\\b')
rxCyrVJV = re.compile('([aeiou])ʼ([aeou])')
rxCyrJV = re.compile('\\bʼ([aeou])')
rxCyrNeutral = re.compile('(?<=[bvgžkmpxčšj])ʼ', flags=re.I)
rxCyrRegressiveSoft = re.compile('([dzlnrstc])([dzlnrstc])(?=ʼ)')
rxCyrMultSoften = re.compile('ʼ{2,}')
rxCyrVSoft = re.compile('([aeiou]|\\b)ʼ', flags=re.I)


def erzya_translit_upa(text):
    """
    Transliterate Erzya text from Cyrillic script to Latin UPA.
    """
    text = rxYer.sub('', text)
    text = text.replace('жи', 'жӥ')
    text = text.replace('ши', 'шӥ')
    text = text.replace('же', 'жэ')
    text = text.replace('ше', 'шэ')
    text = text.replace('Жи', 'Жӥ')
    text = text.replace('Ши', 'Шӥ')
    text = text.replace('Же', 'Жэ')
    text = text.replace('Ше', 'Шэ')

    letters = []
    for letter in text:
        if letter.lower() in cyr2upa:
            if letter.islower():
                letters.append(cyr2upa[letter.lower()])
            else:
                letters.append(cyr2upa[letter.lower()].upper())
        else:
            letters.append(letter)
    res = ''.join(letters)
    res = rxCyrVJV.sub('\\1j\\2', res)
    res = rxCyrJV.sub('j\\1', res)
    res = res.replace('ъʼ', 'j')
    res = rxCyrNeutral.sub('', res)
    for i in range(5):
        res = rxCyrRegressiveSoft.sub('\\1ʼ\\2', res)
    res = rxCyrMultSoften.sub('ʼ', res)
    res = rxCyrVSoft.sub('\\1', res)
    res = res.replace('sʼ', 'ś')
    res = res.replace('zʼ', 'ź')
    res = res.replace('čʼ', 'č')
    res = res.replace('nʼ', 'ń')
    res = res.replace('cʼ', 'ć')
    res = res.replace('rʼ', 'ŕ')
    res = res.replace('Sʼ', 'Ś')
    res = res.replace('Zʼ', 'Ź')
    res = res.replace('Čʼ', 'Č')
    res = res.replace('Nʼ', 'Ń')
    res = res.replace('Cʼ', 'Ć')
    res = res.replace('Rʼ', 'Ŕ')
    return res

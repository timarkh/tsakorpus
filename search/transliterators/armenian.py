import re

dictArm2Lat = {'խ': 'x', 'ու': 'u', 'ւ': 'w',
               'է': 'ē', 'ր': 'r', 'տ': 't',
               'ե': 'e', 'ը': 'ə', 'ի': 'i',
               'ո': 'o', 'պ': 'p', 'չ': 'č‘',
               'ջ': 'ĵ', 'ա': 'a', 'ս': 's',
               'դ': 'd', 'ֆ': 'f', 'ք': 'k‘',
               'հ': 'h', 'ճ': 'č', 'կ': 'k',
               'լ': 'l', 'թ': 't‘', 'փ': 'p‘',
               'զ': 'z', 'ց': 'c‘', 'գ': 'g',
               'վ': 'v', 'բ': 'b', 'ն': 'n',
               'մ': 'm', 'շ': 'š', 'ղ': 'ġ',
               'ծ': 'c', 'ձ': 'j', 'յ': 'y',
               'օ': 'ō', 'ռ': 'ŕ', 'ժ': 'ž',
               'և': 'ew', ':': '.'}

dictLat2Arm = {'x': 'խ', 'u': 'ու', 'w': 'ւ',
               'ē': 'է', 'e\'': 'է', 'r': 'ր', 't': 'տ',
               'e': 'ե', 'ə': 'ը', '@': 'ը', 'i': 'ի',
               'o': 'ո', 'p': 'պ', 'č‘': 'չ', 'c_\'': 'չ',
               'ĵ': 'ջ', 'j\'': 'ջ', 'a': 'ա', 's': 'ս',
               'd': 'դ', 'f': 'ֆ', 'k‘': 'ք', 'k\'': 'ք',
               'h': 'հ', 'č': 'ճ', 'c_': 'ճ', 'k': 'կ',
               'l': 'լ', 't‘': 'թ', 't\'': 'թ', 'p‘': 'փ', 'p\'': 'փ',
               'z': 'զ', 'c‘': 'ց', 'c\'': 'ց', 'g': 'գ',
               'v': 'վ', 'b': 'բ', 'n': 'ն',
               'm': 'մ', 'š': 'շ', 's_': 'շ',
               's\'': 'շ', 'ġ': 'ղ', 'g\'': 'ղ',
               'c': 'ծ', 'j': 'ձ', 'y': 'յ',
               'ō': 'օ', 'o\'': 'օ', 'ŕ': 'ռ', 'r\'': 'ռ',
               'ž': 'ժ', 'z\'': 'ժ', 'z_': 'ժ'}


def armenian_translit_meillet(text):
    text = text.replace('ու', 'u')
    text = text.replace('ու'.upper(), 'U')
    text = text.replace('Ու'.upper(), 'U')
    textTrans = ''
    for c in text:
        try:
            c = dictArm2Lat[c]
        except KeyError:
            try:
                c = dictArm2Lat[c.lower()].upper()
            except KeyError:
                pass
        textTrans += c
    return textTrans


def armenian_input_latin(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace latin characters with Armenian equivalents.
    """
    if field not in ('wf', 'lex', 'lex2', 'trans_ru', 'trans_ru2'):
        return text
    textTrans = ''
    for c in re.findall('.[\'_]+|.', text):
        try:
            c = dictLat2Arm[c]
        except KeyError:
            try:
                c = dictLat2Arm[c.lower()].upper()
            except KeyError:
                pass
        textTrans += c
    return textTrans


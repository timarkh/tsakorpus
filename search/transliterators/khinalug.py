import re

def khinalug_input_normal(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace common shortcuts with valid Khinalug characters.
    """
    if field not in ('wf', 'lex', 'lex2', 'trans_ru', 'trans_ru2'):
        return text
    text = text.replace('c1_', 'č̄')
    text = text.replace('c1\'', 'č̣')
    text = text.replace('7', 'ˁ')
    text = text.replace('g1', 'ǧ')
    text = text.replace('s1', 'š')
    text = text.replace('z1', 'ž')
    text = text.replace('c1', 'č')
    text = text.replace('j1', 'ǯ')
    text = text.replace('a1', 'ä')
    text = text.replace('u1', 'ü')
    text = text.replace('o1', 'ö')
    text = text.replace('i1', 'ı')
    text = text.replace('k_', 'k̄')
    text = text.replace('t_', 't̄')
    text = text.replace('q_', 'q̄')
    text = text.replace('c_', 'c̄')
    text = text.replace('c\'', 'c̣')
    text = text.replace('k\'', 'ḳ')
    text = text.replace('q\'', 'q̇')
    text = text.replace('x\'', 'x̣')
    text = text.replace('t\'', 'ṭ')
    text = text.replace('h\'', 'ḥ')
    return text

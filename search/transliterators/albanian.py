import re

def albanian_input_normal(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace common shortcuts with valid Albanian characters.
    """
    if field not in ('wf', 'lex', 'lex2', 'trans_ru', 'trans_ru2'):
        return text
    text = text.replace('ё', 'ë')
    text = text.replace('e:', 'ë')
    text = text.replace('c,', 'ç')
    return text


def albanian_input_simplified(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: ignore diacritics.
    """
    if field not in ('wf', 'lex', 'lex2', 'trans_ru', 'trans_ru2'):
        return text
    text = text.replace('a', '[aá]')
    text = text.replace('e', '[eëéæ]')
    text = text.replace('ë', 'ë́?')
    text = text.replace('i', '[ií]')
    text = text.replace('u', '[uú]')
    text = text.replace('o', '[oó]')
    text = text.replace('y', '[yý]')
    text = text.replace('e:', 'ë́?')
    text = text.replace('c,', 'ç')
    return text


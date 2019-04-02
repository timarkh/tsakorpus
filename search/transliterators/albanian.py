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
    return text

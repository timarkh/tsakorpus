import re

def uralic_input_simplified(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace ASCII characters with all possible characters.
    """
    if field not in ('wf', 'lex'):
        return text
    text = text.replace('a', '[aäă]ː?')
    text = text.replace('o', '[oöɔ]ː?')
    text = text.replace('u', '[uü]ː?')
    text = text.replace('i', '[iɨıĭ]ː?')
    text = text.replace('e', '[eɛ]ː?')
    text = text.replace('@', 'əː?')
    text = text.replace('s', '[sš]ʼ?')
    text = text.replace('c', '[cč]ʼ?')
    text = text.replace('n', '[nŋ]ʼ?')
    text = text.replace('z', '[zžǯ]ʼ?')
    text = text.replace('\'', '[\'ʼʔ]')
    return text

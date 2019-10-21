import re

def uralic_input_simplified(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace ASCII characters with all possible characters.
    """
    if field not in ('wf', 'lex'):
        return text
    text = text.replace('ia', 'i͡?a')
    text = text.replace('ua', 'u͡?a')
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
    text = text.replace('d', '[dð]ʼ?')
    text = text.replace('\'', '[\'ʼʔ]')
    return text


def uralic_input_simplified_cyr(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace basic letters with all possible characters.
    (Cyrillic version)
    """
    if field not in ('wf', 'lex'):
        return text
    text = text.replace('а', '[аӑӓ]')
    text = text.replace('о', '[оӧөӫ]')
    text = text.replace('у', '[уӯӱӳўүұ]')
    text = text.replace('и', '[иӣӥії]')
    text = text.replace('е', '[еӗәӛєё]')
    text = text.replace('ы', '[ыӹ]')
    text = text.replace('г', '[гґғ]')
    text = text.replace('ж', '[жӝҗ]')
    text = text.replace('з', '[зӟҙ]')
    text = text.replace('к', '[кқҝҟҡ]')
    text = text.replace('н', '[нңҥ]')
    text = text.replace('с', '[сҫ]')
    text = text.replace('х', '[хҳ]')
    text = text.replace('ч', '[чӵҷҹ]')
    return text

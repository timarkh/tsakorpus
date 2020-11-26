def aramaic_urmi_input_normal(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace common shortcuts with valid Cyrillic characters
    of Christian Urmi (Neo-Aramaic).
    """
    if field not in ('wf', 'lex', 'root'):
        return text
    text = text.replace('b1', 'в')
    text = text.replace('c1', 'ç')
    text = text.replace('s1', 'ş')
    text = text.replace('t1', 'ţ')
    text = text.replace('z1', 'ƶ')
    text = text.replace('i1', 'ь')
    text = text.replace('e1', 'ə')
    return text


def aramaic_turoyo_input_normal(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace common shortcuts with valid characters
    of Turoyo (Neo-Aramaic).
    """
    if field not in ('wf', 'lex', 'root'):
        return text
    text = text.replace('\'', 'ʕ')
    text = text.replace('"', 'ʔ')
    text = text.replace('d_', 'ḏ')
    text = text.replace('d_/', 'ḏ̣')
    text = text.replace('g1', 'ǧ')
    text = text.replace('h/', 'ḥ')
    text = text.replace('s1', 'š')
    text = text.replace('s/', 'ṣ')
    text = text.replace('t_', 'ṯ')
    text = text.replace('t/', 'ṭ')
    text = text.replace('e1', 'ə')
    return text

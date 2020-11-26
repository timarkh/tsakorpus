def tajik_input_normal(field, text):
    """
    Prepare a string from one of the query fields for subsequent
    processing: replace common shortcuts with valid Tajik characters.
    """
    if field not in ('wf', 'lex'):
        return text
    text = text.replace('и1', 'ӣ')
    text = text.replace('х1', 'ҳ')
    text = text.replace('к1', 'қ')
    text = text.replace('ч1', 'ҷ')
    text = text.replace('у1', 'ӯ')
    text = text.replace('г1', 'ғ')
    return text
import re
from transliterators.adyghe import adyghe_translit_ipa


def trans_IPA_baseline(text, lang):
    if lang == 'adyghe':
        return adyghe_translit_ipa(text)
    return text

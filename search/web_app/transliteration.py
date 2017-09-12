import re
from transliterators.adyghe import adyghe_translit_ipa
from transliterators.beserman import beserman_translit_cyrillic


def trans_IPA_baseline(text, lang):
    if lang == 'adyghe':
        return adyghe_translit_ipa(text)
    return text

def trans_cyrillic_baseline(text, lang):
    if lang == 'beserman':
        return beserman_translit_cyrillic(text)
    return text

# Implement your corpus-specific functions here by changing these
# function stubs. Do not change function signatures, do not remove
# functions.

import re


def dictionary_link_wf(lang, wf, analyses, sent_meta):
    """
    Return a link to an external dictionary, database or whatever,
    which will be displayed next to the word in the analysis box.
    analyses: list of analyses, each represented as a dictionary
    NB: analyses and sent_meta may be None.
    If empty, no link will be displayed.
    """
    return ''


def dictionary_link_lemma(lang, wf, ana, sent_meta):
    """
    Return a link to an external dictionary, database or whatever,
    which will be displayed next to the lemma in the analysis box
    (one for each analysis if there are many analyses).
    ana: one analysis as a dictionary
    NB: ana and sent_meta may be None.
    If empty, no link will be displayed.
    """
    return ''

Converting glosses to tags
==========================

This page refers to a specific conversion step relevant for the following source convertors:

- :doc:`eaf2json`
- :doc:`xml_flex2json`
- :doc:`iso_tei_hamburg2json`
- :doc:`exmaralda_hamburg2json`

See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Glosses vs. tags
----------------

The default way of representing word-level morphological information in corpus linguistics is to assign each word a grammatical tag or a set of tags. Part-of-speech (POS) tags are the most common example, but corpora of morphologically rich languages often have tags for other categories, such as tense, number or case. In typology and language documentation, however, another approach is often used, which is called *glossing*. Glossing means that each word is split into morphemes, and each morpheme gets a label, called *gloss*. If only glosses are present in the annotation, it may negatively affect the search functionality of the corpus. You can find out more :doc:`here </tags_vs_glosses>`.

Conversion rules
----------------

To address this problem, Tsakorpus source convertors offer a possibility of converting one's grammatical (i.e. affixal) glosses into grammatical tags.

It is assumed that the part-of-speech tag is already present in the source data in some way, otherwise it would be difficult to restore it based on glosses only.

If you want glosses to be automatically translated into grammatical tags, you can create a file called ``grammRules.csv`` or ``grammRules.txt``and put it in ``/src_convertors/corpus/conf_conversion``. This text file should contain rules that explain how to reconstruct grammatical tags from the glosses. Each rule has two parts separated by a tab (``csv``) or `` -> `` (``txt``). The right-hand part is the reconstructed tag or comma-separated set of tags, and the left-hand part is the condition under which it should be added to a word. The condition must describe a combination of glosses and (optionally) part-of-speech tags. It can be simply a single gloss/tag (written as is), or a regexp that should have a match somewhere inside the glossing (written in double quotes), or a Boolean expression which can use brackets, ``|`` for disjunction, ``&`` for conjunction, ``~`` for negation and expressions of the two previous kinds. Here are several examples with comments::

    1Pl -> 1,pl                   # if the word has a gloss 1Pl, add "1" and "pl" to the set of grammatical tags
    "Poss\.1(-Acc-Sg)?$" -> 1sg   # if the word has a gloss Poss.1, either followed by glosses Acc and Sg, or at the end of the word, add the tag 1sg
    [N]&~[Pl|Acc.Pl] -> sg        # if the word has a POS tag N and has neither Pl nor Acc.Pl gloss, add the tag sg.

If no such rules are present, each gloss will be transformed into an eponymous lowercase tag.

Additionally, you can add ``posRules.txt``. This is a tab-delimited file where each line consists of two columns: a part-of-speech tag used in the source data and a tag you want to replace it with in the online version of your corpus. All tags that do not have a replacement will be left as is.

How to find grammatical glosses
-------------------------------

Now that the convertor has the rules, how does it know what to apply them to? It can be rather tricky to understand what is a grammatical gloss and what is a stem gloss (i.e. translation). Glosses are commonly written in uppercase, but not always, and there can be uppercase stem glosses too (e.g. the pronoun *I*). In FieldWorks, affixes and stems have special marking, but this is not always the case in ELAN or EXMARaLDA files. Tsakorpus will attempt to tell stemm glosses from affix glosses, but if does not succeed, you will need to add a ``glosses`` parameter to :doc:`conversion_settings.json </src_convertors>`. It should be a dictionary where keys are language names and values are lists of strings. For each language, you will have to list all your glosses there. Note that a gloss is understood as a string related to one morpheme. So if you have, for example, morphemes glossed as ``ACC.SG``, ``ACC.PL``, ``GEN.SG`` and ``GEN.PL``, you will have to list them in full, not just ``ACC``, ``GEN``, ``SG`` and ``PL``.

Stem gloss
----------

Right now, the gloss for the stem is automatically placed in the ``trans_en`` field. This is a workaround that will be improved in the future.

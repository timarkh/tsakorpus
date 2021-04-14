FieldWorks convertor
====================

This document explains how to convert texts annotated in FieldWorks_ (FLEX) to Tsakorpus JSON. See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Convertor: ``/src_convertors/xml_rnc2json.py``.

.. _FieldWorks: https://software.sil.org/fieldworks/

Export
------

FieldWorks stores texts in a sophisticated database, so first you need to export your data. You have to open your project in FieldWorks and click "Export" using the "Verifiable generic XML" option. When exporting, the "Interlinear texts" section should be active, the "Analyze" tab should be open, and all relevant annotation tiers should be switched on and visible.

Configuration and challenges
----------------------------

Files exported from FieldWorks are problematic in many respects:

- XMLs coming from different versions of FieldWorks look differently.
- The exported XML does not have any connection to the dictionary (there should be one, but it has been broken for a long time now). Any dictionary information not present in the interlinear will be lost.
- FieldWorks does not have the lemma concept, unlike Tsakorpus. That means that you will either have stems instead of lemmata, or have to somehow reconstruct lemmata from stems and grammatical information yourself.
- All inflectional morphological information is stored in the glosses, so if some category is not overtly marked (which is common for e.g. singular, nominative/absolutive or imperative) and you do not have null morphemes, you will not be able to search for it unless you reconstruct it.

Tsakorpus FieldWorks convertor addresses the first problem by using flexible data extraction that was tested on different kinds of XML. Nevertheless, there is no guarantee that it will work with any FLEX XML. There is currently no solution for second and third problems. The fourth problem can be solved by :doc:`writing a set of rules </src_convertors_gloss>` which will allow the convertor to reconstruct hidden categories.

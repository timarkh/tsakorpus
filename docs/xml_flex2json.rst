FieldWorks convertor
====================

This document explains how to convert texts annotated in FieldWorks_ (FLEX) to Tsakorpus JSON. See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Convertor: ``/src_convertors/xml_flex2json.py``.

.. _FieldWorks: https://software.sil.org/fieldworks/

Export
------

FieldWorks stores texts in a sophisticated database, so first you need to export your data. You have to open your project in FieldWorks and click "Export" using the "Verifiable generic XML" option. When exporting, the "Interlinear texts" section should be active, the "Analyze" tab should be open, and all relevant annotation tiers should be switched on and visible.

Configuration
-------------

Following additional configuration parameters have to be set in :doc:`conversion_settings.json </src_convertors>`:

* ``language_codes`` (dictionary) -- contains correspondences between the ``lang`` attribute values used to identify languages of the original text, translations and glosses, and the language names as specified in the ``languages`` list. If verbose language codes are used in your FLEX project, only this parts before the first hyphen should be used in this dictionary (e.g. ``os`` instead of ``os-xxx-yyy``).

* ``bad_analysis_languages`` (list of strings, optional) -- if your files have glosses in more than one language, this list can contain language codes for the gloss languages that have to be disregarded (e.g. if you only want to keep English glosses).

Challenges
----------

Files exported from FieldWorks are problematic in many respects:

- XMLs coming from different versions of FieldWorks look differently.
- The exported XML does not have any connection to the dictionary (there should be one, but it has been broken for a long time now). Any dictionary information not present in the interlinear will be lost.
- FieldWorks does not have the lemma concept, unlike Tsakorpus. That means that you will either have stems instead of lemmata, or have to somehow reconstruct lemmata from stems and grammatical information yourself.
- All inflectional morphological information is stored in the glosses, so if some category is not overtly marked (which is common for e.g. singular, nominative/absolutive or imperative) and you do not have null morphemes, you will not be able to search for it unless you reconstruct it.

Tsakorpus FieldWorks convertor addresses the first problem by using flexible data extraction that was tested on different kinds of XML. Nevertheless, there is no guarantee that it will work with any FLEX XML. There is currently no solution for second and third problems. The fourth problem can be solved by :doc:`writing a set of rules </src_convertors_gloss>` which will allow the convertor to reconstruct hidden categories.


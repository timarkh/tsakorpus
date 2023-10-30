Categories and tags
===================

Introduction
------------

Tsakorpus uses tags for part-of-speech, morphological and other kinds of annotation. Tags are strings, usually short, such as ``N``, ``acc`` or ``pl``. If you only have glosses, but no tags, read :doc:`here </src_convertors_gloss>` how they can be converted.

Tags in Tsakorpus must be classified into categories. This is done in the ``categories.json`` file, which is used during :doc:`source conversion </src_convertors>`, :doc:`indexing </indexator>` and search. This file defines which tag in which language belongs to which category. Category labels are also strings. For example, ``N`` and ``V`` could belong to a category called ``pos``, ``nom`` and ``acc`` to ``case``, and ``sg`` and ``pl``, to ``number``.

Categorization is used in multiple places across Tsakorpus. For example, you can :doc:`set </configuration>` the order of categories when displaying analyses. The tags are also sorted by categories in corpus JSON files. For example, a word tagged ``N,pl,acc`` will look like this with the aforementioned categorization:

.. code-block:: javascript
    :linenos:
    
    {
        "wf": "corpora"
        "ana": [
            "lex": "corpus",
            "gr.pos": "N",
            "gr.number": "pl",
            "gr.case": "acc"
        ]
    }

It is possible for a category to have multiple values; they will be stored in a list in the JSON files. If you only want to test Tsakorpus and do not want to put much effort into categorization, you could just assign all tags the same category. But in any case, all tags you use must be present in ``categories.json``, otherwise they will not be searchable.

Format
------

``categories.json`` is a dictionary. Its keys are language names (as written in the ``languages`` parameter of :doc:`conversion_settings.json </src_convertors>` or :doc:`/conf/corpus.json </configuration>`). For each language, the value is also a dictionary. Its keys are tags available for that language, and values are their categories. Here is an example:

.. code-block:: javascript
  :linenos:
    
  {
    {
      "beserman": {
        "A": "pos",
        "N": "pos",
        "V": "pos",
        "ins": "case",
        "loc": "case",
        "ill": "case"
    },
    "russian": {
        "A": "pos",
        "S": "pos",
        "V": "pos",
        "acc": "case",
        "gen": "case",
        "nom": "case"
    }
  }

If a language does not appear in this dictionary, its tags will not be searchable. If you have extra languages (i.e. languages that you do not have in your corpus), nothing bad will happen. If you have multiple languages, enabled the "search in all languages" option and want some tags to be searchable under this option, you have to create a language named ``all`` with its own tag-to-category dictionary.

Making your life easier
-----------------------

If you use source convertors, ``categories.json`` probably should look the same in ``/src_convertors`` and in ``/conf``, so you can create a symlink in your :doc:`fork </forks>`.

If you don't have the list of tags you have in the corpus, it would be best to compile it with a script, so that you make sure you did not miss anything. There are ready scripts for spoken ISO/TEI files, EXMARaLDA EXB files and Uniparser_ grammars `here <https://github.com/timarkh/tsakorpus-additional-tools>`_.

.. _Uniparser: https://pypi.org/project/uniparser-morph/

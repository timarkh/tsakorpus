RNC XML convertor
=================

This document explains how to convert RNC XML documents to Tsakorpus JSON. See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Convertor: ``/src_convertors/xml_rnc2json.py``.

Introduction
------------

The RNC XML convertor understands XML files with raw or morphologically annotated text in the format of Russian National Corpus. Currently, files with simple annotated texts ("Main subcorpus" and similar subcorpora) and parallel texts are supported. Although this is a project-specific format, it is a fairly simple one. If your format is not supported by Tsakorpus, it might be easier for you to convert your files into RNC XML, so that Tsakorpus can take it from there.

Format description
------------------

All data is contained in an ``<html>`` node, which has ``<head>`` and ``<body>`` daughters. ``<head>`` may contain metadata, which alternatively can be stored in a separate metadata file. Each metadata field is stored as ``<meta name="..." content="..."/>``.

In the case of simple annotated files, ``<body>`` contains paragraphs (``<p>``, possibly with a class attribute), which, in turn, contain sentences (``<se>``). Sentences contain words (``<w>``, see :doc:`parsed_wordlist_format` for details), while punctuation is placed between the word nodes as plain text. If there are newlines between the words, they are ignored. It is allowed to have spans marking italics (``<i>``) or boldface (``<b>``) inside ``<se>``; they will be transformed into :doc:`style spans </styles>`.

In parallel corpora, ``<body>`` contains translation units (``<para>``), which contain aligned sentences. Each sentence has to have a ``lang`` attribute. The sentences are structured in the same way as in the case of simple texts. There may also be a ``<p>`` layer between ``<body>`` and ``<para>``.

If your files or some of the languages in your files do not have morphological annotation, the ``<se>`` elements must contain plain text without the ``<w>`` and ``<ana>`` tags.

Configuration
-------------

Additional settings available for this convertor are the following:

* ``corpus_type`` (string) -- whether the corpus is parallel (``parallel``) or not (``main``). Defaults to ``main``.

* ``meta_in_header`` (Boolean) -- whether the metadata should be searched in the XML header. If it is found, it undergoes certain name changes to comply with the Tsakorpus requirements (see ``get_meta_from_header`` function in ``/src_convertors/xml_rnc2json.py`` for details).

* ``multivalued_ana_features`` (list of strings) -- names of analysis attributes have to be treated as carrying multiple values separated by a whitespace. Such strings will be converted into lists.

* ``language_codes`` (dictionary) -- contains correspondences between the ``lang`` attribute values used to identify the languages in a parallel corpus and the language names as specified in the ``languages`` list.

* ``clean_words_rnc`` (Boolean) -- whether the tokens should undergo additional RNC-style cleaning (such as removal of the stress marks).

Examples
--------

Simple annotated text
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: xml
  :linenos:

  <?xml version="1.0" encoding="utf-8"?>
  <html>
    <head>
      <meta name="title" content="XXX"/>
      <meta name="author" content="YYY"/>
      <meta name="genre" content="blog"/>
      <meta name="year" content="2004"/>
    </head>
    <body>
      <p>
        <se>
          <w><ana lex="группа" gr="S,f,inan,sg,nom" disamb="yes" sem="pt:set sc:x r:concr hi:class" sem2="pt:set t:hier r:abstr t:group sc:hum r:concr"/>Группа</w> "<w><ana lex="послушать" gr="V,pf,tran,pl,act,2p,imper" disamb="yes" sem="ca:noncaus d:pref t:perc" sem2="ca:noncaus d:pref t:perc"/>ПОСЛУШАЙТЕ</w>!"
        </se>
      </p>
    </body>
  </html>

Parallel annotated text
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: xml
  :linenos:

  <?xml version="1.0" encoding="utf-8"?>
  <html>
    <head></head>
    <body>
      <para id="0">
        <se lang="bua" variant_id="0"><w><ana lex="улаан" gr="A" trans_ru="красный"></ana>УЛААН</w> <w><ana lex="морин" gr="N,pl,nom" trans_ru="лошадь"></ana>МОРИД</w></se>
        <se lang="ru" variant_id="1">КРАСНЫЕ ВСАДНИКИ</se>
      </para>
    </body>
  </html>


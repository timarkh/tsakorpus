Data model
==========

Introduction
------------

There are three major kinds of objects in Tsakorpus: *documents*, *sentences* and *tokens*. Normally, a document represents one text, a sentence represents, well, one sentence, and tokens represent words or punctuation marks. However, you can interpret these objects differently. For example, a *sentence* might correspond to one intonational unit or one line of verse. Note that it is only possible to search for multiple words inside one sentence. It is impossible not to split the text into sentences, since sentence is the basic search unit.

A corpus should be a collection of JSON or gzipped JSON files structured according to the rules described below. A corpus may contain any number of files scattered across a file system subtree starting with ``/corpus/%corpus_name%``. The files must be stored in UTF-8 without BOM.

Each JSON file contains a dictionary representing one corpus document. Each dictionary should have the following keys:

- ``meta`` -- a dictionary with the document-level metadata.
- ``sentences`` -- a list of sentences the document consists of.

The document has, therefore, the following structure:

.. code-block:: javascript
  :linenos:

  {
    "meta": {...},
    "sentences": [...]
  }

Metadata
--------

The value of the ``meta`` key is a dictionary where keys are the names of the metadata fields and the values are strings. All fields listed in the ``viewable_meta`` array in ``/conf/corpus.json`` must be present in each document of the corpus. Other than that, there are no restrictions on metadata; the array may even be empty. However, there are several field names which get special treatment in Tsakorpus:

- The value of ``filename`` is never included in the search results to avoid accidentally compromising the data of corpus developers.
- By default, the ``title`` and ``author`` fields are displayed as document identifiers next to each context in the search results.
- The value of ``year`` should be integer.
- If in your corpus you have texts for which the exact year of creation is unknown, or which contain parts written in different years, you may use fields ``year_from`` and ``year_to`` as lower and upper bounds for the year. If the difference between them is less than 2 and the document does not have the ``year`` field, it will be created and filled automatically.

Sentence list
-------------

The list of sentences is the main part of the document. Each sentence is a dictionary with the following keys:

- ``text`` -- a string with the full text of the sentence.
- ``words`` -- a list of objects, each representing a token (word or punctuation mark) in the sentence together with all the annotation. There are several reasons why the text of the sentence (or at least most of it) is actually stored twice, first in the ``text`` field and second inside the word objects. One of them is allowing multiple (ambiguous) tokenization options for a single sentence. Another is allowing easy full-text search, which would have been impossible in elasticsearch without the ``text`` field. Yet another is the possibility of normalizing the tokens so that they can look differently in the sentence and in the analysis.
- ``lang`` -- a one-byte integer representing the language the sentence is written in. This number should be a valid index for the ``languages`` array in ``/conf/corpus.json``.
- ``meta`` -- a dictionary with sentence-level metafields. Sentence-level metafields may include, for example, speaker data for multi-tier (dialogue) files or year in a document that includes data from different years. All metafields listed in the ``sentence_meta`` array in ``/conf/corpus.json`` must be present in this dictionary. The values should be strings.
- ``para_alignment`` (only in parallel corpora, i.e. corpora with several languages where all or some of the sentences in one language are aligned to sentences in another language) -- a list with dictionaries, each representing an alignment of some part of the sentence with a part of another sentence in the corpus.
- ``src_alignment`` (only for media-aligned corpora) -- a list with dictionaries, each representing an alignment of some part of the sentence with a segment of a video or sound file.
- ``style_spans`` (optional) -- a list with dictionaries, each representing a segment of the sentence text that should be displayed in a non-default style, e.g. in italics or in superscript.

The order of the sentences is important. The sentences should be grouped by language, and within each language they should be ordered exactly as they are ordered in the document. When the sentence collection is indexed, each sentence is assigned the keys ``_id``, ``prev_id`` and ``next_id``, the latter two being filled based on the mutual position of the sentences in the JSON file.

The elements of the ``sentences`` array therefore look like this:

.. code-block:: javascript
  :linenos:

  {
    "text": "...",
    "words": [...],
    "lang": ...,
    "meta": {...},
    "para_alignment": [...],
    "src_alignment": [...],
    "style_spans": [...]
  }

Words
-----

Each word in the ``words`` list is a dictionary with the following keys and values:

- ``wf`` -- a string with the token (word form), used for word search.
- ``wtype`` -- type of the token. Currently, two values are possible: "word" and "punct".
- ``off_start``, ``off_end`` -- character offsets indicating to which segment of the ``text`` string the word corresponds. As mentioned earlier, this can be useful for multiple overlapping tokenization variants, or when the ``wf`` value is normalized for search.
- ``next_word`` -- an integer or a list of integers indicating the index (in the ``words`` array) of the token immediately following the current token. This is also important for multiple tokenization variants.
- ``sentence_index`` -- an integer or an array of integers (again, for multiple tokenizations) indicating the 0-based position of the token in the sentence, not counting the leading and the tail punctuation marks (which do not have to have this field).
- ``sentence_index_neg`` -- same as ``sentence_index``, but used when the user enters a negative number in the *Position in sentence* field. Should equal *1* for the last word in the sentence, *2* for the one before the last, etc.
- ``ana`` -- a list of possible annotation variants for this word. If the word has no annotation, this key may be omitted.

Additionally, the word may have following fields which may be relevant for certain corpora:

- ``wf_display`` -- a string with the token in HTML. It can be used if the displayed version of the token should look different from the one used for search. The displayed version is non-searchable and is displayed exactly as written, without HTML escaping that takes place otherwise. For example, if part of the token has to be in superscript, ``wf_display`` may include ``<sup>`` and ``</sup>`` tags. All HTML tags used should be closed in the same token. If you use transliteration, you should make sure the tags in ``wf_display`` are not transliterated. This field only determines what the token looks like in the popup, but not the baseline.

Overall, a word dictionary looks like this:

.. code-block:: javascript
  :linenos:

  {
    "wf": "...",
    "wf_display": "...",   // optional
    "wtype": "word|punct",
    "off_start": ...,
    "off_end": ...,
    "next_word": ...,
    "sentence_index": ...,
    "sentence_index_neg": ...,
    "ana": [...]           // optional
  }


Analyses
--------

A word can have more than one analysis variant. Usually a word having multiple analyses is the result of automatic morphological annotation without subsequent disambiguation. However, this option is useful even in manually annotated corpora when there is no way to distinguish between several homonymous forms, or when the annotator has doubts (which happens especially often when annotating historical corpora). Search queries will find all words that have at least one analysis conforming to the query.

Each analysis is a dictionary with the following keys and values:

- ``lex`` -- lemma (dictionary form), a string.
- any number of keys starting with ``gr.`` (such as ``gr.pos`` or ``gr.case``) -- strings or arrays of strings that contain values of grammatical or lexical categories expressed in the word. The name of the category, as well as the value, should be listed in the ``categories.json`` file for the language the sentence is written in, otherwise this information will not be searchable. Each category can have multiple values (this can happen e.g. in case compounding when a stem attaches several case markers).
- ``gloss``, ``parts`` and ``gloss_index`` (only for corpora with glossing) -- strings representing the glosses for the word (``gloss``), segmentation of the word into morphemes (``parts``) and the combination of these two fields used during search (``gloss_index``). The ``gloss`` field should contain glossing according to the Leipzig glossing rules (the glosses can be arbitrary, but the format should be correct). You might want to gloss the stem as STEM instead of a short English translation, otherwise it would be impossible to make queries such as "find a genitive marker immediately following the stem". It is okay to only do that in the ``gloss_index``, which is used for search, but not in ``gloss``, which is used for displaying the glosses. Glossing and segmentation into morphemes should not contain empty morphemes and glosses for them; all categories that are not overtly expressed in the word should be tagged using the ``gr.`` fields. The string ``gloss_index`` has the following format: GLOSS1{morpheme1}-GLOSS2{morpheme2}-... Each gloss is accompanied by the corresponding morpheme in curly brackets. All glosses are separated by hyphens; there should also be a hanging hyphen at the end of the string.
- any number of other keys with string values, such as ``trans_en``. All fields used here have to be listed in the ``word_fields`` list in ``conf/corpus.json``, and their additional properties can be specified through optional ``kw_word_fields``, ``word_table_fields`` and ``accidental_word_fields`` parameters in the same file. You cannot have a field named ``gr``.

Parallel alignment
------------------

If all or some of the documents in your corpus have several parallel tiers, e.g. original text and its translations into other languages, the tiers have to be assigned different language IDs, starting from zero. These IDs should correspond to the names of the languages in the ``languages`` array in ``conf/corpus.conf`` file. The sentences of all tiers should be stored in one JSON file, but independently. The sentences in the file should be ordered by language ID. In order to indicate that a certain part of a sentence is aligned with a certain part of another sentence in another tier, these sentences should contain the following dictionary in their ``para_alignment`` arrays:

.. code-block:: javascript
  :linenos:

  {
    "off_start": ...,
    "off_end": ...,
    "para_id": ...
  }

The ``off_start`` and ``off_end`` parameters are integers that determine the aligned span in characters. The ``para_id`` parameter is an integer uniquely (at the document level) identifying a bunch of aligned segments: it should have the same value in all tiers of an aligned segment. The aligned segment may be shorter or longer than the sentence. In the first case, the sentence will contain several dictionaries in the ``para_alignment`` array. In the second case, several consecutive sentences in the same tier will have alignments with the same ``para_id``.


Source alignment
----------------

If all or some of the documents in your corpus were aligned with sound or video, the aligned sentences (in all tiers, if there are several) should contain the following dictionary in their ``src_alignment`` lists:

.. code-block:: javascript
  :linenos:

  {
    "off_start_src": ...,
    "off_end_src": ...,
    "off_start_sent": ...,
    "off_end_sent": ...,
    "mtype": "audio|video",
    "src_id": "...",
    "src": "..."
  }


The ``off_start_src`` and ``off_end_src`` parameters are numbers (float) that determine the relevant segment in the media file in seconds. The ``off_start_sent`` and ``off_end_sent`` parameters are integers that determine the aligned span in the sentence in characters. The ``mtype`` is a string that says if the media is a sound file or a video file. The ``src_id`` parameter is a string uniquely (at the document level) identifying an aligned segment. The ``src`` parameter is the name and the relative path to the media file. All media files have to be located in the ``search/media/%corpus_name%`` directory. Just as with ``para_alignment``, it is possible to have several aligned segments in a sentence or several sentences in an aligned segment.


Style spans
-----------

The baseline of the sentence may contain :doc:`style spans </styles>`, i.e. segments that should be displayed in a style other than the default, e.g. in italics or in superscript. Each dictionary in the ``style_spans`` list represents one such segment. It looks like this:

.. code-block:: javascript
  :linenos:

  {
    "off_start": ...,
    "off_end": ...,
    "span_class": "...",
    "tooltip_text": "..."  // optional
  }

The ``off_start`` and ``off_end`` parameters are integers that define the offset of the relevant segment in the ``text`` value in characters. ``span_class`` is a string that defines the style. When displayed in a search hit, the relevant segment is put inside a ``<span>`` element with the ``class`` attribute set to ``style_%SPAN_CLASS%``. For example, if ``span_class`` equals ``i``, the actual span tag will look like ``<span class="style_i">``. The classes should be defined in ``/search/web_app/static/css/span_styles.css``. Predefined classes are ``style_i`` (italics), ``style_b`` (bold), ``style_sup`` (superscript), ``style_sub`` (subscript), and ``style_txt_hX`` for ``X`` = ``1``, ``2`` and ``3`` (headers). ``tooltip_text`` can be used to display a tooltip for that span. See :doc:`styles` for more.


Sentence example
----------------

Here is an example of a sentence. It contains both parallel alignment (the text is aligned with its Russian translation) and media alignment.

.. code-block:: javascript
  :linenos:

  {
    "text": "[нрзб] tačʼe taos.",
    "words": [
      {
        "wf": "[",
        "wtype": "punct",
        "off_start": 0,
        "off_end": 1,
        "next_word": 1
      },
      {
        "wf": "нрзб",
        "wtype": "word",
        "off_start": 1,
        "off_end": 5,
        "next_word": 2,
        "sentence_index": 0,
        "sentence_index_neg": 3
      },
      {
        "wf": "]",
        "wtype": "punct",
        "off_start": 5,
        "off_end": 6,
        "next_word": 3,
        "sentence_index": 1
      },
      {
        "wf": "tačʼe",
        "wtype": "word",
        "off_start": 7,
        "off_end": 12,
        "next_word": 4,
        "sentence_index": 2,
        "sentence_index_neg": 2,
        "ana": [
          {
            "lex": "tačʼe",
            "gr.pos": "PRO",
            "gr.number": "sg",
            "gr.case": "nom",
            "parts": "tačʼe",
            "gloss": "STEM",
            "gloss_index": "STEM{tačʼe}-",
            "trans_ru": "такой"
          }
        ]
      },
      {
        "wf": "taos",
        "wtype": "word",
        "off_start": 13,
        "off_end": 17,
        "next_word": 5,
        "sentence_index": 3,
        "sentence_index_neg": 1,
        "ana": [
          {
            "lex": "ta",
            "gr.pos": "PRO",
            "gr.proType": "pers",
            "gr.number": "pl",
            "gr.case": "nom",
            "parts": "ta-os",
            "gloss": "STEM-PL",
            "gloss_index": "STEM{ta}-PL{os}-",
            "trans_ru": "он, она"
          }
        ]
      },
      {
        "wf": ".",
        "wtype": "punct",
        "off_start": 17,
        "off_end": 18,
        "next_word": 6
      }
    ],
    "lang": 0,
    "meta": {
      "speaker": "AP",
      "gender": "M",
      "year": "2017"
    },
    "para_alignment": [
      {
        "off_start": 0,
        "off_end": 18,
        "para_id": 616
      }
    ],
    "src_alignment": [
      {
        "off_start_src": "0.05",
        "off_end_src": "1.3",
        "off_start_sent": 0,
        "off_end_sent": 18,
        "mtype": "audio",
        "src_id": "50_1300",
        "src": "AP_AS_2017.01.06_words_YZ_training-0-0.mp4"
      }
    ]
  }

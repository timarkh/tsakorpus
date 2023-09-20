Source convertors
=================

Introduction
------------

Before indexing, your corpus data has to be transformed into :doc:`Tsakorpus JSON </data_model>` format. Tsakorpus includes customizable source conversion scripts for a number of source file formats. However, if your format is not supported or you do not get the result you expected, you will have to write a convertor yourself.

All files related to the convertors are located in ``/src_convertors``.

This is how it works:

1. You put your source files into the appropriate folder.
2. You edit configuration files.
3. You pick one of the Python scripts in ``/src_convertors``, based on your data format, and run it.
4. You get the JSON files. If your corpus has media files, you also get cut and compressed media files.

Paths
-----

If you want to convert your corpus with one of the source convertors, you have to put your files into right folders. Start by creating an empty ``/src_convertors/corpus`` directory if it is not already there. After that, there are two possibilities:

Option 1 (default): single corpus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this scenario, you are going to work with a single corpus in this Tsakorpus instance. In this case, all files pertaining to your corpus could be put directly to ``/src_convertors/corpus``. All configuration files then will be located in ``/src_convertors/corpus/conf_conversion``. If you have a ``/src_convertors/conf_conversion`` folder, you may delete it, or make sure that ``corpus_name`` in ``/src_convertors/conf_conversion/conversion_settings.json`` is empty.

Option 2: multiple corpora in one Tsakorpus instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(This option is mostly useful for development purposes, so probably you do not need it.)

In this case, each corpus will occupy a separate folder in ``/src_convertors/corpus``. For each corpus, you have to create a directory called ``/src_convertors/corpus/%corpus_name%``. Two sets of configuration files are used, one located in ``/src_convertors/conf_conversion`` (global) and the other, in ``/src_convertors/corpus/%corpus_name%/conf_conversion`` (local). Whenever the two configuration files have the same keys, the one located inside the corpus directory overrides the global one. The main purpose of the ``/src_convertors/conf_conversion/conversion_settings.json`` file (the one higher up in the tree) is to tell the converter where to look for the source files, which is why the parameters ``corpus_dir`` (which equals ``corpus`` by default) and ``corpus_name`` (set it to your current ``%corpus_name%``) have to be specified there. All the rest can be put to the lower configuration file. In what follows, replace ``src_convertors/corpus/%corpus_name%`` with ``src_convertors/corpus/%corpus_name%``.

Source files
------------

All source files have to have the same format and extension. If you want to include different types of files in the corpus, you have to create a separate corpus folder for each type, see Option 2 above.

The source files should be placed in ``/src_convertors/corpus/%ext%``, where ``%ext%`` is their extension. If the extension is ``json``, you have to name this directory ``json_input`` to avoid name collision with the target directory. This directory can have any number of subdirectories of arbitrary depth. After the files have been converted, the resulting JSON files will be located in ``/src_convertors/corpus/json``. If you run CG3 disambiguation after that, the disambiguated JSON files will be located in ``src_convertors/corpus/json_disamb``. If you have a media-aligned corpus, the source media files have to be located next to the corresponding ELAN/EXMARaLDA/TEI files (and referenced there). The resulting media files (compressed and split into pieces) will appear in the directory that you set through the ``output_media_dir`` parameter. If this parameter is not set, they will appear in ``/src_convertors/corpus/media``.

Configuration files
-------------------

The obligatory configuration files are ``conversion_settings.json`` and ``categories.json``. The latter describes which tags correspond to which grammatical categories and has the same format as ``categories.json`` in the main configuration directory (see :doc:`/categories`). ``conversion_settings.json`` contains a number of key-value pairs that describe the contents of the corpus and tell the convertors how to deal with it. Here is a common list of parameters; see also format-specific parameters in the description of individual convertors.

General parameters
~~~~~~~~~~~~~~~~~~

- ``corpus_name`` (string) -- the name of the corpus. During source conversion, this parameter is only used to determine the path to the corpus files. If it does not exist or equals an empty string, it is assumed that you have only one corpus, which is located in ``src_convertors/corpus``. If you have multiple corpora (*Option 2* above), then this field should be present in the global configuration file (``src_convertors/conf_conversion/conversion_settings.json``).

- ``json_indent`` (integer) -- sets the number of whitespaces in one indent in the output JSON files. A value of ``-1`` means no indentation and no newlines. You only need indentation if you want to look at the output files in a text editor; otherwise, do not turn it on to save disk space.

- ``gzip`` (Boolean) -- whether the resulting JSON file should be gzipped (which will take slightly more time, but much less disk space).

- ``languages`` (list of strings) -- names of the languages in your corpus. The order is important, since integer IDs are used instead of language names in the JSON files. Index in this list is used as an ID for each language. The actual language names are used in some other parameters in ``conversion_settings.json``.

Metadata
~~~~~~~~

In most cases, it is expected that metadata for your texts (such as title, author or genre) are stored in a single file in ``src_convertors/corpus``.

- ``meta_filename`` (string) -- the name of the metadata file. CSV and `Coma <https://exmaralda.org/en/corpus-manager-en/>`_ formats are recognized. In the case of CSV, the file should have tab-delimited format where each line represents one source file, the first column contains the name of the file and other columns contain all the metadata, one column per metadata field. In the case of a Coma file, see also ``coma_meta_conversion`` parameter below.

- ``meta_fields`` (list of strings) -- list of metadata field names. The values for the listed fields should appear in the metadata file in the same order: value for the first field in the first column, and so on. The name of the first metadata field should be ``filename``. In the metadata file, it corresponds to the first column that contains the name of the file being described by that line.

- ``integer_meta_fields`` (list of strings) -- list of metadata fields whose values have to interpreted as integers rather than strings. All fields that start with ``year`` are included in this list automatically. See the eponymous parameter in :doc:`corpus configuration </configuration>`.

- ``notokenize_meta_fields`` (list of strings) -- list of metadata fields whose string values should not be tokenized by Elasticsearch. This affects how they can be searched. E.g. if you search for ``newspaper`` in a tokenized field, values like ``press,newspaper`` will appear in the search. If the field is not tokenized, only ``newspaper`` will match. Tokenized type works well for tag-like fields such as genre, while non-tokenized type can be useful for full-text fields such as author or title. The field ``title`` is always included in this list.

- ``meta_files_ext`` (Boolean) -- whether the filenames in the metadata file have extensions.

- ``meta_files_dir`` (Boolean) -- whether the filenames in the metadata file have their full path relative to ``/src_convertors/corpus/%ext%`` specified (without trailing slashes). If it is set to ``false``, it is assumed that the names of the source files are unique regardless of where they exist within the subtree.

- ``meta_files_case_sensitive`` (Boolean) -- whether the filenames in the metadata file should be treated as case sensitive.

- ``nometa_skip`` (Boolean, optional) -- whether the files not referenced in the metadata should be skipped. Defaults to ``false``.

- ``exclude_by_meta`` (list of dictionaries, optional) -- list of dictionaries, each of which contains a rule that determines which input documents should be skipped based on their metadata values. A document is skipped if it conforms to at least one rule. A document conforms to the rule if its metadata contains all the key-value pairs present in the rule, while possibly containing other keys. Defaults to empty list.

- ``coma_meta_conversion`` (dictionary, optional) -- determines which communication-level description fields from a Coma metadata file have to be used and what metadata fields they map to. Only usable with the Coma metadata files.

- ``speaker_meta_filename`` (string, optional) -- the name of the JSON file with metadata for individual speakers (for the ELAN convertor). The file should contain a dictionary where the keys are the codes of the speakers and the values are dictionaries with their metadata (fields and plain string/integer values). Here is an example of how such a file could look like:

.. code-block:: javascript
  :linenos:

  {
    "AB": {
      "gender": "F",
      "origin": "Moscow"
    },
    "PR": {
      "gender": "M",
      "origin": "New York"
    }
  }


Tokenization, sentence segmentation and cleaning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These parameters are taken into account in scenarios where Tsakorpus performs tokenization and/or sentence splitting itself (which is not always the case).

- ``sent_end_punc`` (string) -- regexp used to decide if current token ends the sentence. It could equal something like ``(?:[.!?;;]+(?:[)\\]}>/»]|$)|\\\\n)``.

- ``sent_start`` (string) -- regexp used to decide if current token can start the sentence. It could equal something like ``^[A-Z]``. If ``sent_end_punc`` matches a token, but ``sent_start`` does not match the next token, no sentence break is inserted.

- ``abbreviations`` (list of strings) -- list of tokens that should be considered abbreviations, so that a fullstop following them does not count as a sentence breaker.

- ``newline_ends_sent`` (Boolean) -- whether a newline character should break the sentence no matter what. This is relevant e.g. for article or chapter headers, which usually do not end with any punctuation.

- ``transparent_punctuation`` (string, optional) -- regexp that determines which punctuation should be considered "transparent", i.e. should not be counted when calculating distances between words for a multiword query. This parameter influences the assignment of ``sentence_index`` values, which are added to words and punctuation marks at conversion time and then used in multiword queries at search time. Defaults to ``^ *$``.

- ``non_word_internal_punct`` (list of strings, optional) -- list of non-letter characters that should never be treated as word-internal during tokenization (if built-in tokenization is used). Defaults to the newline character; whitespace is always included. For example, a tokenizer with default options will consider words like *bla-bla-bla* to constitute single tokens, but if you add hyphen to this list, *bla-bla-bla* will be split into three tokens.

- ``special_tokens`` (dictionary, optional) -- determines which tokens have to be treated in a special way when performing automatic tokenization. Each key is a regex, and the corresponding value is a dictionary that should be inserted in the JSON files as an object representing that token. E.g. ``"<(REPOST|USER|LINK)>": {"wtype": "punct"}`` would lead to tokens ``<REPOST>``, ``<USER>`` and ``<LINK>`` being tokenized as such (i.e. the angle brackets will not become separate tokens) and being treated as punctuation.

- ``split_tokens`` (list of string, optional) -- determines which character segments should be split into several tokens. Each string is a regex. Each token that conforms to one of the regex will be split into several parts, each part being one of the regex groups. E.g. an expression ``(hello)(world)`` will split the string ``helloworld`` into ``hello`` and ``word`` (no whitespaces).

- ``capitalize_sentences`` (Boolean, optional) -- whether the first letter of the first word in each sentence should be automatically capitalized. Defaults to ``false``.

- ``convert_quotes`` (Boolean) -- whether simple quotation marks should be converted to something typographically better-looking. This makes sense for some European languages, e.g. German, French or Russian.

- ``left_quot_mark`` (string) -- a replacement for a left-side double quotation mark (such as ``«`` or ``»``).

- ``right_quot_mark`` (string) -- a replacement for a right-side double quotation mark (such as ``«`` or ``»``).

- ``char_replacements`` (dictionary, optional) -- describes characters that should be replaced. Keys are characters to be replaced, values are strings they should be replaced with. Can be used e.g. for replacing lookalike special characters.

- ``add_contextual_flags`` (Boolean, optional) -- whether punctuation-related ``flags`` field should be added automatically to each word. There is a pre-defined set of punctuation-related flags, e.g. ``comma``, ``quest_mark`` or ``quote`` (see ``src_convertors/simple_convertors/sentence_splitter.py`` for details). For example, if a word is preceded by a comma and followed by a question mark, it will get ``a:comma`` and ``b:quest_mark`` strings in the ``flags`` field. This way, the users can take punctuation into account when searching. This option only works in some of the convertors for now. 

Morphological analysis
~~~~~~~~~~~~~~~~~~~~~~

These parameters are relevant in the scenarios where you have no POS tagging / morphological annotation in the texts yet, but would like to add some at the conversion stage. The only way of doing so right now is providing Tskorpus convertors with a pre-analyzed word list (or several lists, if you have multiple languages). Analyses from that list will be inserted into the JSON files. You have to put analyzed word list(s) to ``src_convertors/copus``. If some of the words have multiple ambiguous analyses and you would like to disambiguate them using CG3_, you can also put a CG3 rule list to the same folder. Note that you have to install CG3 to use it (``apt-get install cg3`` on Linux; download it and put the path to the binary to the ``PATH`` variable on Windows).

.. _CG3: https://visl.sdu.dk/cg3/single/

- ``parsed_wordlist_filename`` (string, optional) -- the name of the file with the morphologically annotated word list. If you have several lists for different languages, the value should be a dictionary where keys are the names of the languages and values are the names of the files.

- ``parsed_wordlist_format`` (string, optional) -- the format of the annotated word list. Currently, only the ``xml_rnc`` option is available, which means a list of XML-represented words in the format used in Russian National Corpus. See the description of this format :doc:`here </parsed_wordlist_format>`.

- ``gramtags_exclude`` (list of strings, optional) --  grammatical tags that should be excluded from the analyses. Defaults to empty list.

- ``cg_disambiguate`` (Boolean, optional) -- whether your corpus has to be disambiguated with the Constraint Grammar rules after the annotation. Defaults to ``false``.

- ``cg_filename`` (dictionary, optional) -- names of the CG3 rule files (if you want to disambiguate your corpus). The files should be located in ``src_convertors/corpus/``. The value of this field is a dictionary where the keys are the names of the languages and the values are the names of the corresponding files. You are not required to list all the languages you have.

Media
~~~~~

If your texts are aligned with sound or video files, the following parameters are relevant:

- ``media_length`` (integer) -- the length of one media file piece in seconds. All media files will be split into overlapping pieces of that length, so that the user does not have to download the entire file to listen for one sentence.

- ``media_dir`` (string, optional) -- path to the media files to be cut, if they are located in a different folder than the ELAN files.

- ``output_media_dir`` (string, optional) -- path to the directory where cut media files will be stored, if different from the default (``/src_convertors/corpus/media``).

If not absolute, the directory paths are relative to ``src_convertors``.

The convertors
--------------

There are several source convertors for different input formats. Each of them is implemented as a class and is located in one Python file:

Commonly used convertors
~~~~~~~~~~~~~~~~~~~~~~~~

- :doc:`Plain text convertor </txt2json>`: ``txt2json.py``.
- :doc:`ELAN media-aligned files convertor </eaf2json>`: ``eaf2json.py``.
- :doc:`Fieldworks FLEX glossed texts convertor </xml_flex2json>`: ``xml_flex2json.py``.
- :doc:`Convertor of morphologically annotated XML (possibly parallel) </xml_rnc2json>` in one of the formats used by Russian National Corpus: ``xml_rnc2json.py``.

Project-specific and ad-hoc convertors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- :doc:`HZSK ISO/TEI media-aligned files convertor </iso_tei_hamburg2json>`: ``iso_tei_hamburg2json.py``.
- EXMARaLDA media-aligned files convertor (works only for non-segmented EXB files where events coincide with segments): ``exmaralda_hamburg2json.py``.
- Convertor for JSON files obtained by harvesting social media with a `VK text harvester <https://github.com/timarkh/vk-texts-harvester>`_: ``social_networks2json.py``.
- Plain-text questionnaire convertor: ``txt_questionnaires2json.py``.
- Convertor for a YAML-like format used by the Morphy annotator: ``morphy_yaml2json.py``.

Please see the documentation pages for individual convertors to find out how they can be used. The following pages also may be relevant:

- :doc:`/parsed_wordlist_format`
- :doc:`/src_convertors_gloss`

Running a convertor
-------------------

When you are ready with the configuration and the source files are stored in the relevant folder, all you have to do is to run the corresponding Python file and wait until it terminates. If your corpus consists of several parts stored in different formats, you may process them one by one with different source convertors and put the resulting JSONs in one place. The resulting files will be stored in ``/src_convertors/corpus/json`` or, if you used CG3 disambiguation, in ``/src_convertors/corpus/json_disamb``.

Individual convertor settings
-----------------------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   parsed_wordlist_format
   tags_vs_glosses
   src_convertors_gloss
   txt2json
   eaf2json
   xml_flex2json
   xml_rnc2json
   iso_tei_hamburg2json
   exmaralda_hamburg2json

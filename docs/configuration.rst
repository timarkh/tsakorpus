Corpus configuration
====================

This page describes the settings used by the :doc:`indexator </indexator>` and the search interface. You should configure them if you already have corpus files in JSON ready for indexing. For source convertors configuration, please see :doc:`src_convertors`.

Configuration files
-------------------

There are two configuration files you need before you launch your corpus: ``/conf/corpus.json`` and ``/conf/categories.json``. The latter describes tags and categories; you can find more :doc:`here </categories>`. This page describes ``corpus.json``.

Note that in some cases, you may also want to change the default values of some Elasticsearch parameters (see below).

Configuring your corpus
-----------------------

Since Tsakorpus is developed for many usage scenarios in mind, many things in it are customizable. As a consequence, there are a lot of parameters that you have to configure. They define how Tsakorpus looks and behaves.

One way of configuring the parameters is manually editing ``/conf/corpus.json``. You will find a full alphabetical list of parameters below. Some parameter changes will only take effect after you reindex your corpus, but most (especially those connected to the interface) will only require apache2/nginx reload. Before you reload the server, make sure you have valid JSON in ``/conf/corpus.json``, e.g. using JSONLint_.

.. _JSONLint: https://jsonlint.com/

However, a more human-friendly way of configuring your corpus is doing that through a simple web interface. To do so, launch ``/search/tsakorpus.wsgi`` as a Python file on your local machine. You do not have to have Elasticsearch running. This will start a local web-server. Open your browser and type ``http://127.0.0.1:7342/config``. You will see a configuration page. Note that it is only accessible from your local machine.

This page contains (almost) all possible parameters separated into rubrics. Fill in the boxes with the values you need and click "Save" in the bottom slide. You can save the page many times. After you click the button, a new ``corpus.json`` file will appear in ``/USER_CONFIG`` (*not* in ``/conf``). When you are ready, move it to ``/conf``. Filling all relevant boxes (especially those related to tag selection tables) can take a lot of time; please be patient.

Apart from ``corpus.json``, it will generate :doc:`translation files </interface_languages>` in ``/USER_CONFIG/translations``. Edit them and replace files in ``/search/web_app/translations/`` with them in your :doc:`fork </forks>`.

When you are done with basic configuration and translations, you could also set up :doc:`automatic transliterations </transliteration>`, :doc:`input methods </input_methods>`, :doc:`virtual keyboards </keyboards>` and :doc:`style spans </styles>` in separate files.

List of parameters
------------------

``corpus.json`` contains a dictionary. Most keys are optional (there is a default value for each key, see ``/search/web_app/corpus_settings.py``.) The following keys are allowed:

- ``accidental_word_fields`` (list of strings) -- names of the word-level analysis fields that should not be taken into account in word searches, even if they are searchable in the sentences. For example, such a field might contain indication that a word precedes or follows a punctuation mark: it can be useful in sentence search, but hardly relevant for word search. Defaults to empty list.

- ``all_language_search_enabled`` (Boolean) -- whether the user may make language-inspecific queries. Relevant only in a corpus with multiple languages.

- ``ambiguous_analyses`` (Boolean) -- whether there are tokens in the corpus which have multiple (ambiguous) analyses. In this case, the user can select if they want to search only among unambiguously analyzed words.

- ``author_metafield`` (string) -- name of the second-important metadata field whose value will be displayed next to the title in headers of hit results. Defaults to ``author``.

- ``citation`` (string) -- an HTML string that answers the question "How to cite the corpus". If it is present, a quotation mark image will appear at the top of the page. The citation information will appear as a dialogue if the user clicks that image.

- ``context_header_rtl`` (Boolean) -- whether context headers for search hits, which contain metadata such as author and title, should be displayed in right-to-left direction. Defaults to ``false``.

- ``corpus_name`` (string, **obligatory**) -- name of the corpus, which determines the name of Elasticsearch indexes used for indexing or searching. The indexes used by the corpus are ``%corpus_name%.docs``, ``%corpus_name%.words`` and ``%corpus_name%.sentences``.

- ``debug`` (Boolean) -- whether additional debug elements, such as "Show JSON query / Show JSON response", are turned on in the web interface. Defaults to ``false``.

- ``default_locale`` (string) -- code of the default :doc:`interface language </interface_languages>`.

- ``default_values`` (dictionary) -- dictionary where keys are names of text boxes in the word search panel and values are the strings that should appear there by default. Currently, it only works for simple string-valued sentence-level metadata fields. The text boxes should be called by the IDs they have in the HTML, e.g. ``sent_meta_speaker`` rather than ``speaker`` if ``speaker`` is a sentence-levele metadata field.

- ``default_view`` (string) -- whether the sentences are displayed as simple text with analysis popups (``standard``) or as inerlinear text with glosses (``glossed``). Defaults to ``standard``.

- ``detect_lemma_queries`` (Boolean) -- whether the search engine should recognize word queries which only look for one particular lemma (possibly with additional constraints) and lift the cap on the number of hits displayed. (The cap is actually increased to ``InterfaceQueryParser.maxQuerySize``, see ``/search/search_engine/query_parser.py``.) Defaults to ``false``.

- ``display_freq_rank`` (Boolean) -- whether the quantile / frequency rank column should be displayed for word/lemma query hits. Defaults to ``true``.

- ``elastic_url`` (string) -- by default, Tsakorpus connects to the Elasticsearch running on ``localhost:9200`` without user authentication. If you want to connect to Elasticsearch running on another host or port, or if you want to supply username and password, you can put a URL to be used here, e.g. ``http://user:password@localhost:9200/``. Make sure ``corpus.json`` does not have too broad read permissions. Defaults to empty string.

- ``fulltext_search_enabled`` (Boolean) -- boolean value that determines whether a text box for full-text search should be displayed. Defaults to ``true``.

- ``fulltext_view_enabled`` (Boolean) -- whether it is allowed to view entire annotated texts. If turned on, HTML rendering is generated for texts at indexation time (which can slow down the process significantly). Full texts are only generated for those JSON files that have ``fulltext_id`` metadata field filled in. The name of the resulting file is its value. Defaults to ``false``.

- ``generate_dictionary`` (Boolean) -- whether a dictionary of lexemes should be generated at indexation time for each of the languages. If true, the dictionary is stored in the ``search/web_app/templates`` directory and could be accessed by clicking the book glyph in the web interface. Defaults to ``false``.

- ``gloss_search_enabled`` (Boolean) -- whether the gloss search text box should be present in the word query form. Should be enabled for glossed corpora.

- ``images`` (Boolean) -- whether the corpus contains any aligned image files and, therefore, whether the aligned images should appear next to the search results. The images should be located in ``/search/img/%corpus_name%``, and the filename is taken from the ``img`` parameter in the sentence-level metadata. Defaults to ``false``.

- ``input_format`` (string) -- the format of the corpus files. Currently supported values are ``json`` (:doc:`Tsakorpus JSON files </data_model>`) and ``json-gzip`` (gzipped Tsakorpus JSON files).

- ``input_methods`` (list of strings) -- list of supported input methods, aka user input transliterations. Each input method corresponds to a function that has to be applied to any value typed in any of the text fields of the search query form, such as *Word* or *Lemma*, before this value is passed to the search. The functions are allowed to make a regular expression out of the value. For each input method, there should be a function in ``/search/web_app/transliteration.py`` named ``input_method_%INPUT_METHOD_NAME%`` that takes the name of the query field, the text and the name of the language as input and returns transliterated text.

- ``integer_meta_fields`` (list of strings) -- names of the sentence-level metadata fields that have integer values and therefore should be represented by ranges rather than by single text boxes in the query interface.

- ``interface_languages`` (list of strings) -- list with codes of all available :doc:`web interface languages </interface_languages>`.

- ``keep_lemma_order`` (Boolean) -- whether the order of multiple analyses should be kept when a string with the lemmata is concatenated for displaying. Defaults to ``false``. For example, if a word has 3 analyses with the lemmara *B*, *A* and *B*, ``false`` means that the output string of lemmata will look like *A/B*, and ``true``, *B/A/B*. The latter may be needed if multiple analyses actually refer to different parts of a graphic word, e.g. host and clitics if they are represented as a single token.

- ``keyboards`` (dictionary) -- defines virtual keyboards for all or some of the languages of the corpus. Keys are language names, and values are IDs of the keyboard files in ``/search/web_app/static/keyboards``. See :doc:`keyboards` for details. If a virtual keyboard exists for a language, it can be switched on in *Word*, *Lemma* and *Full-text search* text boxes by clicking on a keyboard sign.

- ``kw_word_fields`` (list of strings) -- list with names of the word-level analysis fields that should be treated as keywords rather than text, except ``lex``, ``parts``, ``gloss`` and the grammatical fields that start with ``gr.``. Full-text search in these fields will be impossible. Defaults to empty list.

- ``lang_props`` -- dictionary where keys are the names of the languages and values are dictionaries with language-specific properties. Here is what each dictionary may contain:

    - ``dictionary_categories`` (list of strings) -- names of dictionary (lexical) grammatical categories (without the ``gr.`` prefix), such as nominal gender. Values of these categories will appear on the same line with the part of speech in grammatical popups, separate from the other (inflectional) categories.

    - ``exclude_fields`` (list of strings) -- names of non-grammatical analysis fields that should not be displayed in analysis popups. Defaults to empty list.

    - ``gloss_selection`` (dictionary) -- dictionary that describes what should appear in the Gloss selection popup. Currently, its only key is ``columns``, where the value is a list containing lists of tag descriptors, each of these inner lists representing a single column in the popup. Each descriptor is a dictionary with possible keys ``type`` (obligatory), ``value`` and ``tooltip``. The corresponding values are strings. ``type`` parameter can equal ``tag`` (description of a gloss tag), ``header`` (description of a header for a group of gloss tags), or ``separator`` (a line that separates one group of tags from another). ``value`` and ``tooltip`` determine what text will appear on the tag an on the tooltip.

    - ``gloss_shortcuts`` (dictionary) -- dictionary where keys are shortcuts for gloss search and values are the regexes they should translate into when searching. The shortcuts can, for example, be umbrella tags like ``CASE`` that should be replaced by a disjunction of actual case tags like ``(NOM|ACC|DAT)``. These transformations are applied to the contents of the Gloss search input before further processing.

    - ``gr_fields_order`` (list of strings) -- list of names of :doc:`category names </categories>` (without the ``gr.`` prefix) which defines in which order their values should be displayed in word analyses. (Since they are stored in a nested object, they are unordered in the database).

    - ``gramm_shortcuts`` (dictionary) -- dictionary where keys are shortcuts for grammatical tags and values are the Boolean expressions they should translate into when searching. The shortcuts can, for example, be umbrella tags like ``case`` that should be replaced by a disjunction of actual case tags like ``(nom|gen|dat)``. Or they can stand for a traditional category label that is annotated differently in your data, e.g. ``aorist`` could translate into ``pst,pfv``. These transformations are applied to the contents of the Grammar search input before further processing.

    - ``gramm_selection`` (dictionary) -- what should appear in the Grammar selection popup. Has almost the same structure as ``gloss_selecton``. Its only key is ``columns``, where the value is a list containing lists of tag descriptors, each of these inner lists representing a single column in the popup. Each descriptor is a dictionary with possible keys ``type`` (obligatory), ``value``, ``category`` and ``tooltip``. The corresponding values are strings. ``type`` parameter can equal ``tag`` (description of a tag), ``header`` (description of a header for a group of gloss tags), or ``separator`` (a line that separates one group of tags from another). ``value`` and ``tooltip`` determine what text will appear on the tag an on the tooltip. ``category`` is used for logical grouping of tags and can contain arbitrary strings (not necessarily those that you have in :doc:`categories.json </categories>`), which will not be visible to the user. Whenever several tags from the same category are selected, they get into the query with a logical *OR* between them; tags from different categories are united with an *AND*.

    - ``lexical_fields`` (list of strings) -- names of non-grammatical analysis fields that should appear in analysis popups between the lines with dictionary categories and (inflectional) grammatical categories. Defaults to empty list. All fields that do not belong to this list are displayed below the grammatical line.

    - ``lexicographic_order`` (list of strings) -- list of characters ordered alphabetically for sorting words and lemmata. If absent, standard Unicode ordering is applied. "Characters" are actually arbitrary strings and may include e.g. digraphs.

    - ``other_fields_order`` (list of strings) -- list of names of non-grammatical analysis fields which defines in which order their values should be displayed in word analyses. If the field is missing, the fields are sorted alphabetically. If present, this field must contain all field names that exist in the corpus.

- ``languages`` (list of strings) -- names of the languages used in the corpus. The order of the languages determines how they are encoded in the index (the code of the language is its index in this list) and, in the case of parallel corpora, in which order they are displayed within one parallel context.

- ``line_plot_meta`` (list of strings) -- names of the metadata fields whose values are numerical and should be represented in statistics by a line plot rather than by a histogram. Defaults to ``["year"]``.

- ``max_context_expand`` (integer) -- how many times the user may expand a context from search results. This can be important if there are copyright restrictions on the texts. Negative values mean unlimited expanding.

- ``max_distance_filter`` (integer) -- if the user specifies distances between search terms in the query with the "distance requirements are strict" checkbox checked, and the distance constraints are sufficiently complex (meaning that there is no single word in their intersection), Tsakorpus first gets the search results for the same query without restrictions and then filters them one by one to leave out those that do not satisfy the restrictions. If the raw search result count is too high, this may take significant time and memory. This parameter determines the maximum raw search result count that allows further filtering. Negative values mean no threshold. If your entire corpus has less than 100,000 sentences, it is probably safe to turn off the threshold, but with larger corpora I recommend checking if no threshold is ok for your server.

- ``max_hits_retrieve`` (integer) -- the maximal number of hits (sentences or words/lemmata) that the user will be able to see. Defaults to ``10000``. The total number of hits will be reflected in statistics anyway. **Important**: if you want to increase it, you will also have to increase the Elasticsearch ``index.max_result_window`` `parameter <https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules.html>`_, which defaults to 10000. Doing so may lead to very high memory consumption if the user actually wants to see these examples, so don't do it. If you want to look past the example number 10,000, it almost certainly means that you should narrow down your query or change the sorting method. (I don't know of anyone who would like to actually sift through more than 10,000 examples looking at each of them.)

- ``max_words_in_sentence`` (integer) -- when building a multi-word query with specific distances or distance ranges between the search terms, Tsakorpus has to produce a huge query of the kind "(word1 is blah-blah-blah and its index in the sentence is 0, word2 is blah-blah and its index in the sentence is 1 or 2) or (word1 is blah-blah-blah and its index in the sentence is 1, word2 is blah-blah and its index in the sentence is 2 or 3) or ...". The reason for that is that there is no way to impose distance constraints when looking inside a list in Elasticsearch, since the lists are interpreted as mere sacks with values. The integer ``max_words_in_sentence`` defines which sentence positions should be enumerated in multi-word queries. This is not an actual upper bound on the sentence length (there is none), but the tails of longer sentences will not be available for some multi-word queries.

- ``media_length`` (integer) -- duration of media files in seconds. During indexing, source media files are split into overlapping pieces of equal duration (recommended duration is 1-3 minutes). This parameter is required at search time in order to recalculate offsets of neighboring sentences that were aligned with different pieces.

- ``media_youtube`` (Boolean) -- if ``media`` is true, determines whether the media files are stored on Youtube. Since plain audio/video files and Youtube videos require different player settings, all your media files have to be either uploaded to Youtube, or stored as media files on the server.

- ``media`` (Boolean) -- whether the corpus contains any aligned media (sound or video) files and, therefore, whether the media player should appear next to the search results. Defaults to ``false``. See also the ``video`` option.

- ``multiple_choice_fields`` (dictionary) -- describes tag selection tables for sentence-level metadata fields or word-level fields (other that *Grammar* or *Gloss*). Keys are field names, values are structured in the same way as ``gramm_selection`` above.

- ``negative_search_enabled`` (Boolean) -- whether the negative search button should be present in the word query form. Defaults to ``true``.

- ``query_log`` (Boolean) -- whether queries should be logged. When turned on, query type, query arguments and timestamps are appended to ``search/query_log.txt`` after each query. No personal data (such as IP address) are saved. Defaults to ``true``.

- ``query_timeout`` (integer) -- the upper bound on sentence search query execution in seconds. This bound is applied strictly for the Elasticsearch query execution and not so strictly when postprocessing results found by Elasticsearch.

- ``regex_simple_search`` (string) -- regex which is applied to all strings of a query to determine how they should be dealt with. By default, a text query is treated as containing wildcards and Boolean operators if it only contains regular characters and either a star or Boolean operators; as a regex if it contains any special regex characters other than a star; and as simple text otherwise. If ``regex_simple_search`` matches the query, it will be processed as simple text. You would want to change this parameter if you have tokens with stars, dots, parentheses etc. that you need to search. Defaults to ``^[^\[\]()*\\{}^$.?+~|,&]*$``.

- ``rtl_languages`` (list of strings) -- list of languages which use right-to-left writing direction. Defaults to empty list.

- ``sample_size`` (real number between ``0`` and ``1``) -- if you only launch your corpus for testing purposes and do not want to index all source files, you can indicate the proportion of files you want to use. Files will be randomly selected at indexation time. E.g. if ``sample_size`` is set to ``0.1``, only about 10% of the source files will be indexed. Defaults to ``1``.

- ``search_meta`` (dictionary) -- describes what should appear on different tabs of the "Select subcorpus" dialogue:

   - ``columns`` -- list with column-by-column description of what options should appear on the "Specify parameters" tab;
   - ``stat_options`` -- list with the names of the metadata fields that should be available for plotting statistics on the "Subcorpus statistics" tab.

- ``search_remove_whitespaces`` (Boolean) -- whether all whitespaces should be deleted from the search textbox before making a non-keyword query, such as word or lemma query. Defaults to ``true``. The whitespaces are trimmed at the ends of the textboxes regardless of this parameter.

- ``sent_id_sort_enabled`` (Boolean) -- whether the "sort by sentence ID" option is enabled in sentence search. Defaults to ``false``. If enabled, hits will be sorted in by document, and inside one document, in the order of their appearance there. Re-indexing needed if switching from ``false`` to ``true``. **ATTENTION!** If enabled, this option will allow to view sentences of the entire corpus in the correct sequence. Do not enable it if your texts are copyright-protected.

- ``sentence_meta_values`` (dictionary) -- dictionary where keys are names of sentence-level metadata fields and values are lists of their respective values. You should use this dictionary for metadata fields that have short lists of allowed values. Instead of text boxes, such metadata fields will be represented by selectors where all values will be listed in the order specified in the lists.

- ``sentence_meta`` (list of strings) -- list with names of the sentence-level metadata fields that should be available in word-level search queries.

- ``session_cookie_domain`` (string) -- value of the Flask's ``SESSION_COOKIE_DOMAIN`` parameter, if different from the base domain name of your resource. You may want to set it if you have multiple corpora on different subdomains.

- ``start_page_url`` (string) -- a string with the URL of the start page of the corpus, if there is one. It is used to link the header of the search page to the start page.

- ``transliterations`` (list of strings) -- list of supported transliterations. For each transliteration, there should be a function in ``/search/web_app/transliteration.py`` named ``trans_%TRANSLITERATION_NAME%_baseline`` that takes the text and the name of the language as input and returns transliterated text.

- ``try_restart_elastic`` (Boolean) -- if local Elasticsearch is used and it seems to be down (no connection can be established when a client opens the search page), try starting it by running ``search/restart_elasticsearch.sh`` (only in Linux). Defaults to ``true``. Note that starting a service requires sudo privileges. In order for this to work without you manually entering your sudo password, the user who runs the app has to be allowed to use sudo without a password in this case. This can be achieved by running ``sudo visudo`` and adding the following line::

    your_username   ALL=NOPASSWD:/usr/bin/systemctl start elasticsearch.service

If you edit ``search/restart_elasticsearch.sh`` to use a different way of starting Elasticsearch service, you have to modify this line accordingly.

- ``video`` (Boolean) -- whether the corpus has aligned video files. Defaults to ``false``. If it does, do not forget to set ``media`` to ``true``.

- ``viewable_meta`` (list of strings) -- names of the document-level metadata fields that should be shown in search results.

- ``wf_analyzer_pattern`` (string) -- regex to be used by the Elasticsearch analyzer to split word forms and lemmata into simple tokens for storage and search purposes. By default, it equals ``[.\n()\[\]/]``. It is used in indexation only. The idea is that if a token in your corpus contains e.g. a slash, it should be possible to find it by searching both parts, the one before the slash and the one after it.

- ``wf_lowercase`` (Boolean) -- whether all tokens should be stored in lowercase. Defaults to ``true``. It is used in indexation only. If set to false, the wordform search will be case sensitive.

- ``word_fields_by_tier`` (dictionary) -- if there is more than one language/tier with different annotation, describes which word-level search fields should be turned on for which tier. Each tier that does not support all of the word search fields (e.g. does not support Lemma search because it has no lemmatization) has to appear in this dictionary as a key. The corresponding value is a list of all search fields that should be switched on when searching in this tier. This includes all main and additional word-level search fields, except for wordform (``wf``), which is always available. When the user selects a tier, the fields not supported by it, as well as their labels, turn grey (but are not actually disabled).

- ``word_fields`` (list of strings) -- names of the word-level analysis fields that should be available in word-level search queries. These include all fields that can occur inside the ``ana`` nested objects, except ``lex``, ``parts``, ``gloss`` and the grammatical fields that start with ``gr.``.

- ``word_search_display_gr`` (Boolean) -- whether the grammar column should be displayed for word/lemma query hits. Defaults to ``true``.

- ``word_table_fields`` (list of strings) -- names of the word-level analysis fields that should be displayed in the table with Word search results, along with the wordform and lemma, which appear automatically. Defaults to empty list.

- ``year_sort_enabled`` (Boolean) -- whether the "sort by year" option is enabled in sentence search. Defaults to ``false``. If enabled, sentences can be sorted by the ``year_from`` field (or just ``year``, if there is no ``year_from``) of their document in the decreasing order. Only makes sense if all documents are dated.

Elasticsearch configuration
---------------------------

In most cases, default settings will work just fine. However, there are several parameters that you may want to change. They deal with certain limitations set as safeguards against unexpectedly high memory use. You can add or change these parameters by creating `index templates <https://www.elastic.co/guide/en/elasticsearch/reference/current/index-templates.html>`_ and/or in ``elasticsearch.yml`` (``/etc/elasticsearch/elasticsearch.yml`` by default on Linux).

- ``index.mapping.nested_objects.limit`` (defaults to 10000) -- the maximum number of `nested JSON objects <https://www.elastic.co/guide/en/elasticsearch/reference/current/nested.html>`_ that a single document can contain. If you have very large documents and indexation crashes because the number exceeds the limit, you can either split them into smaller parts or increase this parameter.

- ``index.max_result_window`` (defaults to 10000) -- the maximum number of `hits <https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules.html>`_ you can retrieve. The default value means you cannot see search results pages past 1000 (which you usually don't need). If you change it, do not forget to change the ``max_hits_retrieve`` parameter in ``corpus.json`` as well.

- `various search settings <https://www.elastic.co/guide/en/elasticsearch/reference/current/search-settings.html>`_ can be adjusted if you experience problems when making very complex queries.

This is how you could change settings for all new indices (details may vary)::

   curl -X PUT "localhost:9200/_settings?pretty" -H 'Content-Type: application/json' -d'
   {
       "index": {
           "mapping.nested_objects.limit": 50000
       }
   }
   '

Further configuration
---------------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   interface_languages
   transliteration
   input_methods
   keyboards
   styles
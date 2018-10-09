## Configuration files
All configuration files for the search interface and indexator are stored in the ./conf directory. All of them have JSON format. The main configuration file is corpus.json.

### corpus.json
The following parameters (dictionary keys) are recognized in corpus.json:

* ``corpus_name`` -- the name of the corpus, which determines the name of Elasticsearch indexes used for indexing or searching. The indexes used by the corpus are ``%corpus_name%.docs``, ``%corpus_name%.words`` and ``%corpus_name%.sentences``.

* ``input_format`` -- determines which format the input files have and which input processor should be used when indexing. Currently supports "json" (tsakorpus JSON files) and "json-gzip" (gzipped tsakorpus JSON files).

* ``debug`` (true/false) -- determines whether additional debug elements, such as "Show JSON query / Show JSON response", are turned on in the web interface.

* ``media`` (true/false) -- determines whether the corpus contains any aligned media (sound or video) files and, therefore, whether the media player should appear next to the search results.

* ``media_youtube`` (true/false) -- if ``media`` is true, determines whether the media files are stored on Youtube. Since plain audio/video files and Youtube videos require different player settings, all your media files have to be either uploaded to Youtube, or stored as media files on the server.

* ``media_length`` -- an integer that determines the duration of media files in seconds. During indexing, source media files are split into overlapping pieces of equal duration (recommended duration is 1-3 minutes). This parameter is required at search time in order to recalculate offsets of neighboring sentences that were aligned with different pieces.

* ``max_context_expand`` -- an integer that determines how many times the user may expand a context from search results, which can be important if there are copyright restrictions on the texts. Negative values mean unlimited expanding.

* ``query_timeout`` -- an integer that determines the upper bound on sentence search query execution in seconds. This bound is applied stricly for the Elasticsearch query execution and not so strictly when postprocessing results found by Elasticsearch.

* ``max_distance_filter``. When the user specifies distances between search terms in the query and clicks "the distance requirements are strict" checkbox, and the distance constraints are sufficiently complex (there is no single word in their intersection), tsakorpus first gets the search results for the same query without restrictions and then filters them one by one to leave out those that do not satisfy the restrictions. If the raw search result count is too high, this may take significant time and memory. This parameter determines the maximum raw search result count that allows further filtering. Negative values mean no threshold. If your entire corpus has less than 100,000 sentences, it is probably safe to turn off the threshold, but with larger corpora I recommend checking if no threshold is ok for your server.

* ``max_words_in_sentence``. When building a multi-word query with specific distances or distance ranges between the search terms, tsakorpus has to produce a huge query of the kind "(word1 is blah-blah-blah and its index in the sentence is 0, word2 is blah-blah and its index in the sentence is 1 or 2) or (word1 is blah-blah-blah and its index in the sentence is 1, word2 is blah-blah and its index in the sentence is 2 or 3) or ...". The reason for that is that there is no way to impose distance constraints when looking inside a list in Elasticsearch, as the lists are interpreted as mere sacks with values. The integer ``max_words_in_sentence`` defines which sentence positions should be enumerated in multi-word queries. This is not an actual upper bound on the sentence length (there is none), but the tails of longer sentences will not be available for some multi-word queries.

* ``viewable_meta`` -- list with names of the document-level metainformation fields that should be shown in search results.

* ``sentence_meta`` -- list with names of the sentence-level metainformation fields that should be available in word-level search queries.

* ``search_meta`` -- dictionary with the description of what should appear on different tabs of the "Select subcorpus" dialogue:
 * ``search_meta.columns`` -- array with column-by column description of what options should appear on the "Specify parameters" tab;
 * ``search_meta.stat_options`` -- array with the names of the metafields that should be available for plotting statistics on the "Subcorpus statistics" tab.

* ``author_metafield`` (optional) -- string which defines the second-important metafield which will be displayed next to the title in headers of hit results. Defaults to ``author``.

* ``word_fields`` -- list with names of the word-level analysis fields that should be available in word-level search queries. These include all fields that can occur inside the ``ana`` nested objects, except ``lex``, ``parts``, ``gloss`` and the grammatical fields that start with ``gr.``.

* ``word_table_fields`` (optional) -- list with names of the word-level analysis fields that should be displayed in the table with Word search results, along with the wordform and lemma, which appear automatically.

* ``keep_lemma_order`` (true/false; optional) -- determines whether the order of multiple analyses should be kept when a string with the lemmata is concatenated for displaying. Defaults to false. For example, if a word has 3 analyses with the lemmara B, A and B, ``false`` means that the output string of lemmata will look like A/B, and ``true``, B/A/B. The latter may be needed if multiple analyses actually refer to different parts of a graphic word, e.g. host and clitics if they are represented as a single token.

* ``languages`` -- list of names of the languages used in the corpus. The order of the languages determines how they are encoded in the index (the code of the language is its index in this list) and, in the case of parallel corpora, in which order they are displayed within one parallel context.

* ``interface_languages`` -- dictionary with all available web interface languages. The keys are the codes of the languages, the values are their names.

* ``transliterations`` -- list of supported transliterations. For each transliteration, there should be a function in search/web_app/transliteration.py named trans_%TRANSLITERATION_NAME%_baseline that takes the text and the name of the language as input and returns transliterated text.

* ``input_methods`` -- list of supported input methods, aka user input transliterations. Each input method corresponds to a function that has to be applied to any value typed in any of the text fields of the search query form, such as Word or Lemma, before this value is passed to the search. The function are allowed to make a regular expression out of the value. For each input method, there should be a function in search/web_app/transliteration.py named input_method_%INPUT_METHOD_NAME% that takes the name of the query field, the text and the name of the language as input and returns transliterated text.

* ``all_language_search_enabled`` -- boolean value that determines if the user may make language-inspecific queries. Relevant only in a corpus with multiple languages.

* ``gloss_search_enabled`` -- boolean value that determines if the gloss search textbox should be present in the word query form. Should be enabled for glossed corpora.

* ``ambiguous_analyses`` -- boolean value that has to be set to true if there are tokens in the corpus which have multiple (ambiguous) analyses. In this case, the user can select if they want to search only among unambiguously analyzed words.

* ``lang_props`` -- dictionary where keys are the names of the languages and values are dictionaries with language-specific properties (see below).

* ``wf_analyzer_pattern`` (optional) -- string with a regex to be used by the elasticsearch's analyzer to split word forms and lemmata into simple tokens for storage and search purposes. By default, it equals ``[.\n()\[\]/]``. It is used in indexation only. The idea is that if a token in your corpus contains e.g. a slash, it should be possible to find it by searching both parts, the one before the slash and the one after it.

* ``wf_lowercase`` (optional) -- boolean value that determines if all tokens should be stored in lowercase. Defaults to true. It is used in indexation only. If set to false, the wordform search will be case sensitive.

* ``regex_simple_search`` (optional) -- string with a regex which is applied to all strings of a query to determine how they should be dealt with. By default, a text query is treated as containing wildcards if it only contains regular characters and a star, as a regex if it contains any special regex characters other than a star, and as simple text otherwise. If ``regex_simple_search`` matches the query, it will be processed as simple text. You would want to change this parameter if you have tokens with stars, dots, parentheses etc. that you need to search.

* ``search_remove_whitespaces`` (optional) -- boolean value that determines if all whitespaces should be deleted from the search textbox before making a non-keyword query, such as word or lemma query. Defaults to true. The whitespaces are trimmed at the ends of the textboxes regardless of this parameter.

* ``detect_lemma_queries`` (optional) -- boolean value that determines if the search engine should recognize word queries which only look for one particular lemma (possibly with additional constraints) and lift the cap on the number of hits displayed. (The cap is actually increased to ``InterfaceQueryParser.maxQuerySize``, see ``search/search_engine/query_parser.py``.) Defaults to false.

* ``display_freq_rank`` (optional) -- boolean value that determines if the quantile / frequency rank column should be displayed for word/lemma query hits. Defaults to true.

#### The ``lang_props`` dictionary
For each language in the corpus, the ``lang_props`` dictionary should contain a dicrionary whose keys are the names of the parameters. The following parameters are available:

* ``dictionary_categories`` (optional) -- list with the names of dictionary (lexical) grammatical categories (without the ``gr.`` prefix), such as nominal gender. Values of these categories will appear on the same line with the part of speech in grammatical popups, separate from the other (inflectional) categories.

* ``lexical_fields`` (optional) -- list with the names of non-grammatical analysis fields that should appear in analysis popups between the lines with dictionary categories and (inflectional) grammatical categories. Defaults to empty list. All fields that do not belong to this list are displayed below the grammatical line.

* ``exclude_fields`` (optional) -- list with the names of non-grammatical analysis fields that should not be displayed in analysis popups. Defaults to empty list.

* ``gr_fields_order`` -- list with the names of grammatical categories (without the ``gr.`` prefix) which defines in which order their values should be displayed in word analyses (since they are stored in a nested object, they are unordered in the database).

* ``other_fields_order`` (optional) -- list with the names of non-grammatical analysis fields which defines in which order their values should be displayed in word analyses. If the field is missing, the fields are sorted alphabetically. If present, this field must contain all field names that exist in the corpus.

* ``gloss_shortcuts`` -- dictionary where keys are shortcuts for gloss search and values are the regexes they should translate into when searching. The shortcuts can, for example, be umbrella tags like "case" that should be replaced by a disjunction of actual case tags like "(nom|gen|dat)". These transformations are applied to the contents of the gloss search input before further processing.

* ``gloss_selection`` -- dictionary that describes what should appear in the Gloss selection popup. Currently, its only key is ``columns``, where the value is a list containing lists of tag descriptors, each of these inner lists representing a single column in the popup. Each descriptor is a dictionary with possible keys ``type`` (obligatory), ``value`` and ``tooltip``. The corresponding values are strings. ``type`` parameter can equal ``gloss`` (description of a gloss tag), ``header`` (description of a header for a group of gloss tags), or ``separator`` (a line that separates one group of tags from another). ``value`` and ``tooltip`` determine what text will appear on the tag an on the tooltip.

* ``gramm_selection`` -- dictionary that describes what should appear in the Grammar selection popup. Has same contents as ``gloss_selecton``, but the ``type`` of grammatical tags is ``gramm`` rather than ``gloss``.


### categories.json
This file contains a description of all grammatical tags and categories used in each of the languages in the corpus. The keys are the names of the languages. The value for each language is a dictionary where keys are grammatical tags and values are names of the corresponding grammatical categories. This file is used for splitting grammatical analysis/queries like "N,sg,gen" when indexing the corpus and when translating the user's query into Elasticsearch JSON query.

## Configuration files
All configuration files for the search interface and indexator are stored in the ./conf directory. All of them have JSON format. The main configuration file is corpus.json.

### corpus.json
The following parameters (dictionary keys) are recognized in corpus.json:

* ``corpus_name`` -- the name of the corpus, which determines the name of ElasticSearch indexes used for indexing or searching. The indexes used by the corpus are ``%corpus_name%.docs``, ``%corpus_name%.words``, ``%corpus_name%.word_freqs`` and ``%corpus_name%.sentences``.

* ``input_format`` -- determines which format the input files have and which input processor should be used when indexing. Currently supports "json" (tsakorpus json files) and "json-gzip" (gzipped tsakorpus json files).

* ``media`` (true/false) -- determines whether the corpus contains any aligned media (sound or video) files and, therefore, whether the media player should appear next to the search results.

* ``media_length`` -- an integer that determines the duration of media files in seconds. During indexing, source media files are split into overlapping pieces of equal duration (recommended duration is 1-3 minutes). This parameter is required at search time in order to recalculate offsets of neighboring sentences that were aligned with different pieces.

* ``max_context_expand`` -- an integer that determines how many times the user may expand a context from search results, which can be important if there are copyright restrictions on the texts. Negative values mean unlimited expanding.

* ``query_timeout`` -- an integer that determines the upper bound on sentence search query execution in seconds.

* ``max_distance_filter``. When the user specifies distances between words in the search query and clicks "the distance requirements are strict" checkbox, tsakorpus first gets the search results for the same query without restrictions and then filters them one by one to leave out those that do not satisfy the restrictions. If the raw search result count is too high, this may take significant time and memory. This parameter determines the maximum raw search result count that allows further filtering. Negative values mean no threshold. If your entire corpus has less than 100,000 sentences, it is probably safe to turn off the threshold, but with larger corpora I recommend checking if no threshold is ok for your server.

* ``viewable_meta`` -- list with names of the document-level metainformation fields that should be shown in search results.

* ``languages`` -- list of names of the languages used in the corpus. The order of the languages determines how they are encoded in the index (the code of the language is its index in this list) and, in the case of parallel corpora, in which order they are displayed within one parallel context.

* ``transliterations`` -- list of supported transliterations. For each transliteration, there should be a function in search/web_app/transliteration.py named trans_%TRANSLITERATION_NAME%_baseline that takes the text and the name of the language as input and returns transliterated text.

* ``all_language_search_enabled`` -- boolean value that determines if the user may make language-inspecific queries. Relevant only in a corpus with multiple languages.

* ``gloss_search_enabled`` -- boolean value that determines if the gloss search textbox should be present in the word query form. Should be enabled for glossed corpora.

* ``lang_props`` -- a dictionary where keys are the names of the languages and values are dictionaries with language-specific properties (see below).

External links
==============

You can define some additional, custom functions (beyond :doc:`transliteration` and :doc:`input methods </input_methods>`) in ``additional_functions.json``. Right now, there are two functions there: ``dictionary_link_wf`` and ``dictionary_link_lemma``. They are called every time an analysis ``div`` is built for a word in a sentence. If they return a non-empty string, it is interpreted as a URL leading to an external page, such as a dictionary entry for this word or lemma. Both are called with similar parameters: ``lang`` (current language, as in the ``languages`` list in :doc:`corpus.json </configuration>`), ``wf`` (current word), ``analyses`` or ``ana`` (current analyses or analysis) and ``sent_meta`` (sentence- and document-level metadata in a single dictionary). The lemma, if any, can be found in ``ana['lex']``.

Also see :doc:`input_methods`.
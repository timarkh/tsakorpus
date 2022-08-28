Indexing
========

How to index your corpus
------------------------

When your corpus JSON files are ready, they must be indexed in Elasticsearch before the corpus becomes available. You have to follow these steps:

1. :doc:`Configure the corpus </configuration>` by filling out a configuration page in the browser or editing ``/conf/corpus.json``.
2. Edit :doc:`categories.json </categories>` (or copy an existing one) and put it to ``/conf``.
3. Make sure all interface messages are :doc:`translated </interface_languages>` into all interface languages.
4. Make sure all :doc:`transliterations </transliteration>`, :doc:`input methods </input_methods>` and :doc:`virtual keyboards </keyboards>` mentioned in ``corpus.json`` exist.
5. Put the JSON files to ``/corpus/%corpus_name%``.
6. If you have media files cut by the source convertors, put them to ``/search/media/%corpus_name%`` or symlink this folder to the place where they are stored.
7. Run ``/indexator/indexator.py``.

Indexing may take a while; you will see messages in the process. If you have a large corpus and would like to disconnect from the server until indexation is complete, you can launch it with ``nohup``::

    cd indexator
    nohup python3 indexator.py -y > index.log 2>&1 &

If you are setting up the corpus for the first time, do not forget to set up apache/nginx/... configuration files, so that some URL resolves to your corpus, and switch it on. If you are reindexing the corpus, **reload apache/nginx** after the indexation is complete.

What indexator does
-------------------

1. It creates three Elasticsearch indexes called ``%corpus_name%.sentences``, ``%corpus_name%.docs`` and ``%corpus_name%.words``. If indexes with such names already exist, the indexator will ask you for permission to proceed. Use the ``-y`` option to overwrite existing indexes without asking.
2. It puts the contents of your JSON files to the indexes. Sentences are transferred to the database almost without changes.
3. It calculates word and lemma statistics and puts it to the indexes. The statistics is kept in memory during the indexation, so the larger your corpus, the more memory indexation will require.
4. It generates full-text representations and dictionaries, if you chose so in the configuration.

PyBabel :doc:`translations of the interface </interface_languages>`, which used to be compiled at indexation time, are now generated and compiled each time the corpus app is launched.

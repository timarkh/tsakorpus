Getting started
===============

Tsakorpus in a nutshell
-----------------------

Tsakorpus consists of a set of source convertors, an indexator and a web interface with a search engine.

Source convertors are a completely separate part of the package. Since the indexator processes files in a certain :doc:`JSON format </data_model>`, you will probably need to convert your corpus files into it. You can do so yourself if you'd like to, but there are a number of scripts in the ``/src_convertors`` folder that can process some widely used formats.

Each JSON file contains a dictionary with the metadata for that document and a list of sentences (or sentence-like segments, such as ELAN/EXMARaLDA aligned segments) with annotation. It is not possible to have documents without sentence segmentation because the sentence is the basic search unit: when you search for contexts that contain some words, you get a list of sentences as a result.

When your JSON files are ready, the indexator puts them into an Elasticsearch database together with the frequency data for words and lemmata that it calculates on the fly. The web interface, written in Python+flask, allows the user to make complex queries using GUI and view the search results. The search queries are sent to the backend as GET queries and transformed to JSON Elasticsearch queries on the server. The search results are partly transformed to HTML on the server, sent back to the frontend as JSON through Ajax requests and displayed on the results page by a set of JavaScript/jQuery functions.

Installation
------------

Tsakorpus does not require installation. All you have to do is make sure all the dependencies are installed and copy the entire contents of the repository to a directory on your computer. This concerns both Linux and Windows. For indexing and searching operations you need the Elasticsearch service running. On Windows, this may mean manually launching ``elasticsearch.bat`` in the ``bin`` directory of your Elasticsearch installation before you are going to work with Tsakorpus.

Installing dependencies
~~~~~~~~~~~~~~~~~~~~~~~

If you don't have Elasticsearch, you can download it `here <https://www.elastic.co/downloads/elasticsearch>`_. Make sure you are downloading Elasticsearch 7.x. Tsakorpus 2.x is not compatible with other major versions.

Python modules can be installed with the help of the ``requirements.txt`` file in the root folder::

    pip3 install -r requirements.txt

If you need to convert a corpus that includes media files, you have to install ffmpeg_. If you are working on Windows, `make sure <https://www.howtogeek.com/118594/how-to-edit-your-system-path-for-easy-command-line-access/>`_ the path to the ``ffmpeg`` binary is in the ``PATH`` environment variable.

.. _ffmpeg: https://www.ffmpeg.org/download.html

Forking the repository
----------------------

If you just want to play around, you can download Tsakorpus and start working in that folder. However, if you are going to publish a real corpus, it is **strongly recommended** to fork or duplicate the original repository and keep your project files in that fork. This way, you will be able to easily incorporate Tsakorpus updates into it. If you are new to repositories, you could read `the Github introduction <https://guides.github.com/introduction/git-handbook/>`_ first. See more about forking :doc:`here </forks>`.

Pipeline
--------

If you have a corpus in one of several accepted formats, this is the typical pipeline:

1. The :doc:`source conversion part </src_convertors>` (``src_convertors`` directory, may be performed on any computer).

    - You manually configure the source convertor (``conversion_settings.json`` and ``categories.json``, and possibly other files).
    - You put your source files to the appropriate folder and run the appropriate convertor. You get a folder with JSON files as a result.
    - If there is no convertor available for your data, you will have to write one yourself (see :doc:`here </data_model>` for the description of Tsakorpus JSON format).

2. The :doc:`indexation part </indexator>` (outside of ``src_convertors`` directory, should be performed on the server with Elasticsearch service running).

    - If you have multiple corpora, a separate Tsakorpus instance (i.e. Tsakorpus directory and apache config file) is needed for each of them.
    - You configure indexing and search by filling out a configuration page in the browser or editing ``/conf/corpus.json`` and copy the ``categories.json`` to ``/conf``.
    - You manually adjust and/or add interface translations by editing text files in language subdirectories of ``/search/web_app/translations`` (see :doc:`interface_languages`).
    - If you want to use custom transliteration for input or output, you have to edit the scripts in ``/search/transliterators`` and ``/search/web_app/transliteration.py`` (see :doc:`transliteration` and :doc:`input_methods`).
    - If you want to add virtual keyboard(s), you have to edit keyboard files in ``/search/web_app/static/keyboards`` (see :doc:`keyboards`).
    - If you have annotations that span over multiple words, you can define how they should be displayed with CSS styles in ``/search/web_app/static/css/span_styles.css`` (see :doc:`styles`).
    - If you want to add a header, a footer or custom css/js links to your search page, you can do that in ``/search/web_app/templates/header.html`` (the header), ``/search/web_app/templates/footer.html`` (the footer) and ``/search/web_app/templates/head_add.html`` (code that has to be added to the ``<head>`` element in ``index.html``). You can also edit ``/search/web_app/templates/index.html`` directly, but then it can be more difficult to update the platform in the future.
    - You put the JSON files to the appropriate folder inside ``/corpus``.
    - You run ``/indexator/indexator.py``.
    - If you are setting up the corpus for the first time, you set up apache/nginx/... configuration files, so that some URL resolves to your corpus, and switch it on.
    - You reload apache/nginx, wait a little and check if the search works.

Source convertors
-----------------

You can generate JSON files yourself, or use one of the several convertors that come with Tsakorpus. The convertors are located in the ``src_convertors`` directory. A convertor takes a collection of files in one of the source formats, as well as a number of additional setting files, and converts them to the Tsakorpus JSON. You can find out more :doc:`here </src_convertors>`.

Normally, conversion takes 1-10 minutes per million tokens. However, if the source convertor has to cut media files, this may take much longer (up to several hours per million tokens).


Indexing
--------

In order to index a copus, you have to :doc:`adjust settings </configuration>` in the ``conf`` directory and put plain or gzipped JSON files to ``corpus/%corpus_name%``. It is important to choose a unique name for the corpus, as it defines the names of the Elasticsearch database indexes where it is stored.

After these preliminary steps, you have to launch ``indexator/indexator.py`` and wait until it reports that the corpus has been successfully indexed or that something went wrong. The indexator basically transfers the source JSON files to the database with minor technical additions. Besides, it calculates statistics such as word frequencies, which it also puts to the database. In the course of indexing, it stores all word types with their statistics in the memory, which can lead to huge memory consumption in the case of large corpora (>> 50 million tokens; see the subsection below).

If you have lots of files and only want to test Tsakorpus on a small sample of them before putting it to production, you can set the ``sample_size`` parameter in :doc:`corpus.json </configuration>`.

The indexator creates following elasticsearch indexes:

- ``%corpus_name%.sentences`` -- main index: all sentences of the corpus;
- ``%corpus_name%.docs`` -- metadata for corpus documents;
- ``%corpus_name%.words`` -- contains three types, ``lemma``, ``word`` and ``word_freq``. The instances of the first two are all lemma / word types with statistics (identical word forms with different annotations are considered different types). Each instance of the latter contains frequency statistics for each (word, document) tuple.

You can find out more :doc:`here </indexator>`.

Memory and disk space consumption
---------------------------------

(If your corpus contains less than 1 million tokens or 100,000 sentences, you may safely skip this subsection.)

During the indexation phase, there are following primary causes of memory consumption:

- Elasticsearch server, which processes requests of the Python indexator;
- The word types, which are temporarily stored in memory by the indexator until the entire corpus has been indexed;
- The source JSON documents, each of which is normally first read and loaded into memory, and only then processed.

Loading a source JSON document may require significantly more memory than it takes to store it on a hard drive. Consequently, loading large documents (> 100 Mb, which can happen in the case of e.g. long novels with heavy annotation) may lead to memory errors. If a memory error occurs, the file will still be indexed, but with a much slower iterative JSON parser (``ijson``).

Memory consumed by Elasticsearch does not depend on the size of the corpus. Under default settings, it occupies 2 Gb of memory. You have to increase that amount in the Elasticsearch settings (``jvm.options`` file, the parameters are called ``Xms`` and ``Xmx``) if you have a large corpus (e.g. at least 4 Gb for 20 million tokens or 8 Gb for 200 million tokens).

Memory consumed by the indexator itself non-linearly depends on several parameters (number of tokens, number of sentences and number of documents), but for the sake of simplicity it can be thought of as depending on the number of tokens more or less linearly. The constant depends, of course, on the amount of annotation you have. In case of full morphological annotation, a ratio of 60-80 Mb per million tokens (for corpora containing 10-50 million tokens) can be expected.

The disk space required by the index depends primarily on the size of the corpus. Again, in case of full morphological annotation, you can expect 1 million tokens to take 0.5-0.7 Gb of disk space.

The time needed to index a corpus may vary significantly depending on the amount of annotation and your hardware characteristics. Very roughly, you can expect 5-10 minutes per million tokens on an ordinary desktop computer.

Interface translation
---------------------

If you want your web interface to have several language options, you have to provide translations for all captions and messages. English and Russian translations for the main part of the interface are included in the distribution. See more :doc:`here </interface_languages>`.

Transliterations
----------------

If you want the texts of your corpus to be available in several transliterations, you can write your own transliteration functions in Python and integrate them in the platform. See more :doc:`here </transliteration>`.

Running Tsakorpus
-----------------

You can use Tsakorpus either locally or as a web service available from outside. In the first case, it is sufficient to run ``tsakorpus.wsgi`` as a Python file. This will start a flask web server, after which the corpus will be accessible at ``http://127.0.0.1:7342/search``.

In the case of the web service, it is recommended to configure your apache2_ or nginx_ server for working with your corpus (supposing you have a Linux server). If you work with apache, you have to install and enable ``mod_wsgi`` for Python3. (Note that you cannot have ``mod_wsgi`` for both Python2 and Python3 on the same server, at least not that easy.) Then you have to specify the URL under which your corpus is going to be available and the path to the corpus files in an apache .conf file (normally by creating a new ``.conf`` file in the apache ``sites-available`` directory). The directory where your corpus is stored should have relevant read and execute permissions. Here is a sample configuration that you should put to the ``.conf`` file::

  WSGIDaemonProcess %some_unique_process_name% user=%you% group=www-data home=%path_to_corpus_directory%/search
  WSGIScriptAlias /%url_for_your_corpus% %path_to_corpus_directory%/search/tsakorpus.wsgi
  
  <Directory %path_to_corpus_directory%/search>
      WSGIProcessGroup %some_unique_process_name%
      WSGIApplicationGroup %{GLOBAL}
      Require all granted
      Allow from all
  </Directory>


After enabling this configuration and reloading apache, your corpus should be available at ``%your_website_url%/%url_for_your_corpus%/search``. All search queries the user makes are passed to the backend as Ajax GET-queries.

.. _apache2: https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/
.. _nginx: https://flask.palletsprojects.com/en/1.1.x/deploying/fastcgi/#configuring-nginx

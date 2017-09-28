## How to use tsakorpus
This document describes in brief which steps are required for deploying your corpus under tsakorpus platform. It covers installation, converting and indexing the source files and running.

### Installation
Tsakorpus does not require installation. All you have to do is make sure all the dependencies are installed (see readme.md) and copy the entire contents of the repository to a directory on your computer. This concerns both Linux and Windows. For indexing and searching operations you need the elasticsearch service running. On Windows, this may mean manually launching elasticsearch.bat in the elasticsearch/bin directory before you are going to work with tsakorpus.

### Source files
In order to be available for search, your corpus has to be uploaded to the elasticsearch database, which is done by the indexator. The corpus passed to the indexator should consist of a number of JSON documents or gzipped JSON documents. Each of the documents contains a dictionary with the metadata for that document and an array of sentences (or sentence-like segments, such as ELAN/Exmaralda aligned segments) with annotation. It is not possible to have documents without sentence segmentation because the sentence is the basic search unit: when you search for contexts that contain some words, you get a list of sentences as a result. You can find the detailed specification of the JSON format used by tsakorpus in input_format.md.

You can generate JSON files yourself, or use one of the several convertors that come with tsakorpus. The convertors are located in the ``src_convertors`` directory. A convertor takes a collection of files in different source formats, as well as a number of additional setting files, and converts them to the tsakorpus JSON. Currently, the following convertors are available:

* Plain text convertor (``txt2json.py``). It processes an unannotated corpus as a collection of plain UTF8-encoded text files. Apart from the source files, you can provide a separate XML wordlist with (non-disambiguated) analyses for all or some of the tokens in the corpus, and a separate CSV file with metadata for the corpus documents.

* Morphologically annotated parallel XML convertor (``xml_rnc2json.py``). It processes a (possibly annotated) parallel corpus in the (quite simple) XML format used in Russian National Corpus.

* Exmaralda media-aligned files convertor (``exmaralda_hamburg2json.py``). It processes a corpus of manually morphologically annotated and glossed media-aligned files in the Exmaralda format. The names of the tiers and some other details are expected to follow the conventions used at IFUU in Hamburg.

* ELAN media-aligned files convertor (``eaf2json.py``). It processes a corpus of media-aligned files in ELAN format. The files can have translation of the segments into multiple languages or sentence-level comments, but are not expected to be morphologically analyzed. As in the case of the Plain text convertor, this convertor takes a separate XML wordlist with analyses for all or some of the tokens in the corpus, and a separate CSV file with metadata.

* Plain text questonnaire convertor (``txt_questionnaires2json.py``). This is an ad hoc plain text convertor for Beserman Udmurt files that contain single usage examples from the dictionary together with their translations.

Before you run a convertor, you have to adjust settings in the ``src_convertors/conf`` directory and put your source corpus files to the ``src_convertors/corpus/%corpus_name%`` directory. See src_convertors.md for further details.

### Indexing
In order to index a copus, you have to adjust settings in the ``conf`` directory (see configuration.md) and put the source JSON or gzipped JSON filed to ``corpus/%corpus_name%``. It is important to choose a unique name for the corpus, as it defines the names of the elasticsearch database indexes where it is stored. Since there is no authorization in elasticsearch, accidentally choosing a name coinciding with another corpus that already exists on the server will lead to the destruction of the latter, even if it was not yours.

After these preliminary steps, you have to launch ``indexator/indexator.py`` and wait until it reports that the corpus has been successfully indexed or that something went wrong. The indexator basically transfers the source JSON files to the database with minor technical additions. Besides, it calculates statistics such as word frequencies, which it also puts to the database. In the course of indexing, it stores all word types with their statistics in the memory, which can lead to huge memory consumption in the case of large corpora (>> 10 million tokens).

The indexator creates following elasticsearch indexes:

* ``%corpus_name%.sentences`` -- main index: all sentences of the corpus;
* ``%corpus_name%.docs`` -- metadata for corpus documents;
* ``%corpus_name%.words`` -- contains two types, ``word`` and ``word_freq``. The instances of the former are all word types with statistics (identical word forms with different annotations are considered different types). Each instance of the latter contains frequency statictics for each (word, document) tuple.

### Running tsakorpus
You can use tsakorpus either locally or as a web service available from outside. In the first case, it is sufficient to run tsakorpus.wsgi as a Python file. This will start a flask web-server, after which the corpus will be accessible at <http://127.0.0.1:7342/search>.

In the case of the web service, it is recommended to configure your apache server for working with your corpus (supposing you have a Linux server). You have to install and enable mod_wsgi for Python3. (Note that you cannot have mod_wsgi for both Python2 and Python3 on the same server, at least not that easy.) Then you have to specify the URL under which your corpus is going to be available and the path to the corpus files in an apache .conf file (normally by creating a new .conf file in the apache ``sites-available`` directory). The directory where your corpus is stored should have relevant read and execute permissions. Here is a sample configuration that you should put to the .conf file:

```
WSGIDaemonProcess %some_unique_process_name% user=%you% group=www-data home=%path_to_corpus_directory%/search
WSGIScriptAlias /%url_for_your_corpus% %path_to_corpus_directory%/search/tsakorpus.wsgi

<Directory %path_to_corpus_directory%/search>
    WSGIProcessGroup %some_unique_process_name%
    WSGIApplicationGroup %{GLOBAL}
    Require all granted
    Allow from all
</Directory>
```

After enabling this configuration and reloading apache, your corpus should be available at %your_website_url%/%url_for_your_corpus%/search . All search queries the user makes are passed to the backend as Ajax GET-queries.

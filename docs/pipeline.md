## How to use tsakorpus
This document describes in brief which steps are required for deploying your corpus under tsakorpus platform. It covers installation, converting and indexing the source files and running.

### Installation
Tsakorpus does not require installation. All you have to do is make sure all the dependencies are installed (see readme.md) and copy the entire contents of the repository to a directory on your computer. This concerns both Linux and Windows. For indexing and searching operations you need the elasticsearch service running. On Windows, this may mean manually launching elasticsearch.bat in the elasticsearch/bin directory before you are going to work with tsakorpus.

### Updates
Tsakorpus is regularly updated. If you are going to make your corpus publicly available and maintain it, it is strongly recommended that you **create a fork** of this repository for your corpus before you start working with tsakorpus. Read more about forking in ``forks.md``.

### Pipeline overview
If you have a corpus in one of several accepted formats (see *Source files* below), this is the typical pipeline:

1. The source conversion part (``src_convertors`` directory, may be performed on any computer).

    * You manually prepare settings for the source convertor (``conversion_settings.json`` and ``categories.json``, and possibly other files).

    * You put your source files to the appropriate folder and run the appropriate convertor. You get a folder with JSON files as a result.

    * If there is no convertor available for your data, you will have to write one yourself (see ``docs/input_format.md`` for the information on the output JSON format).

2. The indexing part (outside of ``src_convertors`` directory, should be performed on the server with Elasticsearch service running).

    * If you have multiple corpora, a separate tsakorpus instance (i.e. tsakorpus directory and apache config file) is needed for each of them.

    * You manually prepare settings for the indexing and search (``conf/corpus.json``) and copy the ``categories.json`` to ``conf``.

    * You manually adjust and/or add interface translations by editing ``messages.po`` files in language subdirectories of ``search/web_app/translations`` (see ``docs/interface_languages.md``).

    * If you want to use custom transliteration for input or output, you have to edit the scripts in ``search/transliterators`` and ``search/web_app/transliteration.py`` (see Transliteration section below).

    * You put the JSON files to the appropriate folder inside ``corpus``.

    * You run ``indexator/indexator.py``.

    * If you are setting up the corpus for the first time, you set up apache/nginx/... configuration files so that some URL would resolve to your corpus and switch it on.

    * You reload apache/nginx, wait a little and check if the search works.

### Source files
In order to be available for search, your corpus has to be uploaded to the elasticsearch database, which is done by the indexator. The corpus passed to the indexator should consist of a number of JSON documents or gzipped JSON documents. Each of the documents contains a dictionary with the metadata for that document and an array of sentences (or sentence-like segments, such as ELAN/EXMARaLDA aligned segments) with annotation. It is not possible to have documents without sentence segmentation because the sentence is the basic search unit: when you search for contexts that contain some words, you get a list of sentences as a result. You can find the detailed specification of the JSON format used by tsakorpus in input_format.md.

You can generate JSON files yourself, or use one of the several convertors that come with tsakorpus. The convertors are located in the ``src_convertors`` directory. A convertor takes a collection of files in one of the source formats, as well as a number of additional setting files, and converts them to the tsakorpus JSON. Currently, the following convertors are available:

* Plain text convertor (``txt2json.py``). It processes an unannotated corpus as a collection of plain UTF8-encoded text files. Apart from the source files, you can provide a separate XML wordlist with (non-disambiguated) analyses for all or some of the tokens in the corpus, and a separate CSV file with metadata for the corpus documents.

* Morphologically annotated XML convertor (``xml_rnc2json.py``). It processes a (possibly annotated) corpus in one of (quite simple) XML formats used in Russian National Corpus. Currently, basic format ("main subcorpus") and parallel format are supported.

* ELAN media-aligned files convertor (``eaf2json.py``). It processes a corpus of media-aligned files in ELAN format. The files can have translation of the segments into multiple languages or sentence-level comments, but are not expected to be morphologically analyzed. As in the case of the Plain text convertor, this convertor takes a separate XML wordlist with analyses for all or some of the tokens in the corpus, and a separate CSV file with metadata.

* Fieldworks FLEX glossed texts convertor (``xml_flex2json.py``). It processes an XML file with the corpus exported from FLEX. Additionally, it can use user-defined rules for adding grammatical tags (e.g. for categories that do not have overt marking and thus are absent from the glosses).

* Toolbox glossed texts convertor (``toolbox2json.py``). It processes a corpus of .tbt glossed files made in Toolbox. This convertor is not finished yet. Currently, it only processes the baseline and the free translations, but does not process glosses.

* Exmaralda media-aligned files convertor (``exmaralda_hamburg2json.py``). It processes a corpus of manually morphologically annotated and glossed media-aligned files in the Exmaralda format. The names of the tiers and some other details are expected to follow the conventions used at IFUU in Hamburg.

* Plain text questonnaire convertor (``txt_questionnaires2json.py``). This is an ad hoc plain text convertor for Beserman Udmurt files that contain single usage examples from the dictionary together with their translations. You probably don't need it.

Before you run a convertor, you have to adjust settings in the ``src_convertors/conf_conversion`` directory and put your source corpus files to the ``src_convertors/corpus/%corpus_name%`` directory or, if you are going to have only one corpus, to ``src_convertors/corpus``. See src_convertors.md for further details.

Normally, conversion takes 1-10 minutes per million tokens. However, if the source convertor has to cut media files, this may take much longer (several hours per million tokens).

### Indexing
In order to index a copus, you have to adjust settings in the ``conf`` directory (see configuration.md) and put the source JSON or gzipped JSON filed to ``corpus/%corpus_name%``. It is important to choose a unique name for the corpus, as it defines the names of the elasticsearch database indexes where it is stored. Since there is no authorization in elasticsearch, accidentally choosing a name coinciding with another corpus that already exists on the server will lead to the destruction of the latter, even if it was not yours.

After these preliminary steps, you have to launch ``indexator/indexator.py`` and wait until it reports that the corpus has been successfully indexed or that something went wrong. The indexator basically transfers the source JSON files to the database with minor technical additions. Besides, it calculates statistics such as word frequencies, which it also puts to the database. In the course of indexing, it stores all word types with their statistics in the memory, which can lead to huge memory consumption in the case of large corpora (>> 50 million tokens; see the subsection below).

The indexator creates following elasticsearch indexes:

* ``%corpus_name%.sentences`` -- main index: all sentences of the corpus;
* ``%corpus_name%.docs`` -- metadata for corpus documents;
* ``%corpus_name%.words`` -- contains three types, ``lemma``, ``word`` and ``word_freq``. The instances of the first two are all lemma / word types with statistics (identical word forms with different annotations are considered different types). Each instance of the latter contains frequency statictics for each (word, document) tuple.

#### Memory and disk space consumption
(If your corpus contains less than 1 million tokens or 100,000 sentences, you may safely skip this subsection.)

During the indexation phase, there are following primary causes of memory consumption:

* Elasticsearch server which processes requests of the Python indexator;
* The word types which are temporarily stored in memory by the indexator until the entire corpus has been indexed;
* The source JSON documents, each of which is normally first read and loaded into memory, and only then processed.

Loading a source JSON document may require significantly more memory than it takes to store it on a hard drive. Consequently, loading large documents (> 100 Mb, which can happen in the case of e.g. long novels with heavy annotation) may lead to memory errors. If a memory error occurs, the file will still be indexed, but a much slower iterative JSON parser (ijson) will be used to process it.

Memory consumed by Elasticsearch does not depend on the size of the corpus. Under default settings, it occupies 2 Gb of memory. You have to increase that amount in the Elasticsearch settings (``jvm.options`` file, the parameters are called ``Xms`` and ``Xmx``) if you have a large corpus (e.g. 4 Gb for 20 million tokens or 8 Gb for 200 million tokens will probably do).

Memory consumed by the indexator itself non-linearly depends on several parameters (number of tokens, number of sentences and number of documents), but for the sake of simplicity it can be thought of as depending on the number of tokens more or less linearly. The constant depends, of course, on the amount of annotation you have. In case of full morphological annotation, a ratio of 60-80 Mb per million tokens (for corpora containing 10-50 million tokens) can be expected.

The disk space required by the index depends primarily on the size of the corpus. Again, in case of full morphological annotation, you can expect 1 million tokens to take 0.5-0.7 Gb of disk space.

The time needed to index a corpus may vary significantly depending on the amount of annotation and your hardware characteristics. Very roughly, you can expect 5-10 minutes per million tokens on an ordinary desktop computer.

### Translation
If you want your web interface to have several language options, you have to provide translations for all captions and messages. English and Russian translations for the main part of the interface is included in the distribution. If you do not intend to have other languages in the interface, you have to do the following:

* Edit ``search/web_app/translations/%language_code%/LC_MESSAGES/messages.po`` for each of the two languages, adding there the title of the corpus and translations for all corpus-specific labels (such as metadata field names and values, transliteration option names, etc.). The changes take effect after compilation, which starts automatically whenever you index the corpus.

* Edit ``search/web_app/templates/help_dialogue_%language_code%.html`` files if you want the help adapted to your corpus data (you may leave it as is if you prefer so).

See more on translating labels in ``interface_languages.md``.

### Transliterations
(If you are not going to have multiple input or output transliteration options, you may skip this section.)

If you want the texts of your corpus to be available in several transliterations, you can write your own transliteration functions in Python and integrate them in the platform. It can be done as follows.

In the ``search/web_app/transliterators`` directory, add your own Python 3.x files that contain transliteration functions. There are no limitations on what these functions look like or what resources they can use. Then, for each transliteration option, add a simple function in the ``search/web_app/transliteration.py`` file. The functions should be called ``trans_%TRANSLITERATION_NAME%_baseline``, they have to have two string arguments and return a string. The arguments are the text to be transliterated and the language of that text. The text can come either from the ``text`` field of the sentence or from any of the string word-level fields, such as ``wf`` or ``ana.lex``. The idea is that these simple functions will call actual transliteration functions imported from the ``search/web_app/transliterators`` directory. Finally, add available transliteration names to the ``transliterations`` array in ``corpus.json`` and add the translations of these names to the interface translation files (see ``translation.md``).

The functions described above only transliterate the output, i.e. the search results. If you want to transliterate, or alter in any other way, the text that the user inputs in the query form, before the search is performed, you have to add "input methods" in a similar fashion. An input method is basically any function that transforms user input. For each input method, you have to add a function called ``input_method_%INPUT_METHOD_NAME%`` in ``search/web_app/transliteration.py``. These functions take as its parameters the name of the search field, text to be transliterated and the name of the language/tier the user is searching in, and return a transliterated string. Names of the input methods should be listed in the ``input_methods`` array in ``corpus.json`` and translated in the translation files.

Whenever the platform cannot find a function for a transliteration or an input method, it just leaves the text to be transliterated unchanged.

### Running tsakorpus
You can use tsakorpus either locally or as a web service available from outside. In the first case, it is sufficient to run tsakorpus.wsgi as a Python file. This will start a flask web-server, after which the corpus will be accessible at <http://127.0.0.1:7342/search>.

In the case of the web service, it is recommended to configure your apache/nginx server for working with your corpus (supposing you have a Linux server). If you work with apache, you have to install and enable mod_wsgi for Python3. (Note that you cannot have mod_wsgi for both Python2 and Python3 on the same server, at least not that easy.) Then you have to specify the URL under which your corpus is going to be available and the path to the corpus files in an apache .conf file (normally by creating a new .conf file in the apache ``sites-available`` directory). The directory where your corpus is stored should have relevant read and execute permissions. Here is a sample configuration that you should put to the .conf file:

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

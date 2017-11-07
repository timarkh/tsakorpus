## Source convertors
This document describes how to run the srcipts that convert files in various input formats to the tsakorpus JSON. All of the convertors are located in the ``src_convertors`` directory.

### Paths
If you want to convert your corpus named ``%corpus_name%`` with one of the source convertors, you have to create a directory ``src_convertors/corpus/%corpus_name%``. All source files have to have the same type and extension. The source files should be placed in ``src_convertors/corpus/%corpus_name%/%ext%``, where ``%ext`` is their extension. This directory can have any number of subdirectories of arbitrary depth. The configuration files are located in ``src_convertors/conf`` and ``src_convertors/corpus/%corpus_name%/conf``. Whenever the two configuration files have the same fields, the one located inside the corpus directory overrides the general one. After the files have been converted, the resulting JSON files will be located in ``src_convertors/corpus/%corpus_name%/json``. If you run disambiguation after that, the disambiguated JSON files will be located in ``src_convertors/corpus/%corpus_name%/json_disamb``. If you have a media-aligned corpus, the source media files have to be located next to the corresponding ELAN or Exmaralda files (and referenced there). The resulting media files (compressed and split into pieces) will appear in ``src_convertors/corpus/%corpus_name%/media``.

### Configuration files
The configuration files are ``corpus.json`` and ``categories.json``. The latter describes which tags correspond to which grammatical categories and has the same format as ``categories.json`` in the main configuration directory (see ``configuration.md``). The ``corpus.json`` has slightly different set of fields:

* ``corpus_name`` -- the name of the corpus. During source conversion, this parameter is only used to determine the path to the corpus files. This field should be present in the general configuration file (``src_convertors/conf/corpus.json``).

* ``meta_filename`` -- the name of the metadata file. This file should be located in ``src_convertors/corpus/%corpus_name%/``. The file should have tab-delimited format where each line represents one source file, the first column contains the name of the file and other columns contain all the metadata, column per metafield.

* ``meta_fields`` -- the list of metafield names. The values for the listed fields should appear in the metadata file in the same order (value for the first field in the second column, and so on).

* ``meta_files_ext`` -- boolean value that determines whether the filenames in the metadata file have extensions.

* ``meta_files_dir`` -- boolean value that determines whether the filenames in the metadata file have full paths starting from ``src_convertors/corpus/%corpus_name%/%ext%``. If it is set to false, it is assumed that the names of the source files are unique regardless of where they exist within the subtree.

* ``meta_files_case_sensitive`` -- boolean value that determines whether the filenames in the metadata file should be treated as case sensitive.

* ``parsed_wordlist_filename`` -- the name of the file with the morphologically annotated word list (for the converters which accept such a file).

* ``parsed_wordlist_format`` -- the format of the annotated word list (currently, only the "xml_rnc" option is available, which means a list of XML-represented words in the format used in Russian National Corpus).

* ``speaker_meta_filename`` -- the name of the JSON file with metadata for individual speakers (for the ELAN convertor). The file should contain a dictionary where the keys are the codes of the speakers and the values are dictionaries with their metadata (fields and plain string/integer values).

* ``languages`` -- an array with the names of the languages which exist in the corpus.

* ``cg_disambiguate`` -- boolean value that determines whether your corpus has to be disambiguated with the Constraint Grammar rules after the annotation.

* ``cg_filename`` -- the names of the files with the Constraint Grammar rules (if you want to disambiguate your corpus). This files should be located in ``src_convertors/corpus/%corpus_name%/``. The value of this field is a dictionary where the keys are the names of the languages and the values are the names of the corresponding files. It is not obligatory to list all the languages you have.

* ``json_indent`` -- an integer that determines the number of whitespaces in one indent in the output JSON files. A value of -1 means no indentation and no newlines. You only need indentation if you want to look at the output files in a text editor; otherwise, do not turn it on to save disk space.

* ``gzip`` -- boolean value that determines if the resulting JSON file should be gzipped (which will take slightly more time, but much less disk space).

### The convertors
There are several source convertors for different input formats (see ``pipeline.md``). Each of them is a class located in one Python file:

* Plain text convertor: ``txt2json.py``.

* Morphologically annotated parallel XML convertor: ``xml_rnc2json.py``.

* Exmaralda media-aligned files convertor: ``exmaralda_hamburg2json.py``.

* ELAN media-aligned files convertor: ``eaf2json.py``.

* Plain text questonnaire convertor: ``txt_questionnaires2json.py``.

When you are ready with the configuration and the source files are stored in the relevant folder, all you have to do is to run the corresponding Python file and wait until it terminates. If your corpus consists of several parts stored in different formats, you may process them one by one with different source convertors and put the resulting JSONs in one place.


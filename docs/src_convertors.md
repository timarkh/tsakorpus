## Source convertors
This document describes how to run the srcipts that convert files in various input formats to the tsakorpus JSON. All of the convertors are located in the ``src_convertors`` directory.

### Paths
If you want to convert your corpus named ``%corpus_name%`` with one of the source convertors, you have to create a directory ``src_convertors/corpus/%corpus_name%``. All source files have to have the same type and extension. The source files should be placed in ``src_convertors/corpus/%corpus_name%/%ext%``, where ``%ext`` is their extension. This directory can have any number of subdirectories of arbitrary depth. The configuration files are located in ``src_convertors/conf`` and ``src_convertors/corpus/%corpus_name%/conf``. Whenever the two configuration files have the same fields, the one located inside the corpus directory overrides the general one. After the files have been converted, the resulting JSON files will be located in ``src_convertors/corpus/%corpus_name%/json``. If you run disambiguation after that, the disambiguated JSON files will be located in ``src_convertors/corpus/%corpus_name%/json_disamb``. If you have a media-aligned corpus, the source media files have to be located next to the corresponding ELAN or Exmaralda files (and referenced there). The resulting media files (compressed and split into pieces) will appear in ``src_convertors/corpus/%corpus_name%/media``.

### Configuration files
The configuration files are ``corpus.json`` and ``categories.json``. The latter describes which tags correspond to which grammatical categories and has the same format as ``categories.json`` in the main configuration directory (see ``configuration.md``). The ``corpus.json`` has slightly different set of fields compared to the homonymous file in the main configuration directory:

* ``corpus_name`` -- the name of the corpus. During source conversion, this parameter is only used to determine the path to the corpus files. This field should be present in the general configuration file (``src_convertors/conf/corpus.json``).

* ``meta_filename`` -- the name of the metadata file. This file should be located in ``src_convertors/corpus/%corpus_name%/``. The file should have tab-delimited format where each line represents one source file, the first column contains the name of the file and other columns contain all the metadata, one column per metafield.

* ``meta_fields`` -- list of metafield names. The values for the listed fields should appear in the metadata file in the same order (value for the first field in the second column, and so on).

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

* Plain text questionnaire convertor: ``txt_questionnaires2json.py``.

When you are ready with the configuration and the source files are stored in the relevant folder, all you have to do is to run the corresponding Python file and wait until it terminates. If your corpus consists of several parts stored in different formats, you may process them one by one with different source convertors and put the resulting JSONs in one place.

### Parsed word list
Convertors that read raw text (from .txt, .eaf and so on) allow you to have a separate file with morphological (or any other word-level) annotation for all or some of the word forms. The only available option for now is xml_rnc. An annotated word list in this format is a plain text file where each line describes one unique word form. The lines should look as follows:

```
<w><ana lex="..." gr="..." ...></ana>[<ana..../ana>]*wordform</w>
```

Each word form starts with ``<w>`` and ends with ``</w>``. First, it has an analysis in the ``<ana>`` tag, or a concatenated list of possible analyses. The annotations is stored as attributes of the ``<ana>`` element. There are four reserved attribute names: ``lex`` for lemma, ``gr`` for comma-separated list of grammatical tags, ``parts`` for word segmentation into morphemes, and ``gloss`` for the glossing. All these fields are optional. If you have glossing, the number of morphemes should be equal to the number of glosses (hence, no hyphens in the stem are allowed). Apart from that, you can have any number of other attributes, e.g. ``trans_en`` for an English translation of the word. The actual word form must be located at the end, after the analyses.

### Disambiguation
If you choose to disambiguate your files using a Constraint Grammar file, they will be disambiguated after the primary conversion to JSON is complete. Your JSON files will be translated into CG format and stored in the ``cg`` directory, which will have language subdirectories. Multilanguage files will be split abd sentences in different languages will end up in different subdirectories. CG will process these files and put them to ``cg_disamb``. When this process is finished, the disambiguated files will be assembled, transformed back into JSON and stored in the ``json_disamb`` directory.

Disambiguation requires that you have a [CG3 executable](https://visl.sdu.dk/cg3/chunked/installation.html) and its directory is in the system PATH variable.

### ELAN files conversion (eaf2json)
Currently, the convertor only supports ELAN files that may have translation/comment tiers, but do not have morphological annotation (such annotation can be added to the texts with the help of a parsed word list, see above). Since text in different tiers belongs to different speakers and languages, it is important that you carefully describe where is what. First, all tiers should have the "participant" attribute filled in with the code of the speaker. The codes should be explained in the speaker metadata file whose name is specified by the ``speaker_meta_filename`` parameter. Here is an example of how such a file could look like:

```
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
```

Second, tier types should be consistent throughout your corpus. If you have translations/comments, then translation/comment tiers should have a type of their own and have to be aligned with the main (transcription) tiers. The names of the tiers should be described in the following parameters in ``corpus.json``:

* ``main_tiers`` -- an array with the names of the tiers that must be treated as transcription baseline. Normally, this array will contain only one name.

* ``aligned_tiers`` -- an array with the names of translation/comment tiers that have a main tier as their parent.

* ``tier_languages`` -- a dictionary where keys are the names of the tier types (listed in the above two arrays) and the values are the names of their languages.

The source audio/video files will be split into small pieces with [ffmpeg](https://www.ffmpeg.org/). You have to have it installed, and its directory should be in the system PATH variable.

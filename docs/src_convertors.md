## Source convertors
This document describes how to run the srcipts that convert files in various input formats to the tsakorpus JSON. All of the convertors are located in the ``src_convertors`` directory.

### Paths
If you want to convert your corpus with one of the source convertors, you have to put your files into right folders. Start by creating an empty ``src_convertors/corpus`` directory if it is not already there. After that, there are two possibilities:

#### Option 1: you are going to work with a single corpus in this Tsakorpus instance
In this case, all files pertaining to your corpus could be put directly to ``src_convertors/corpus``. All configuration files then will be located in ``src_convertors/corpus/conf_conversion``. If you have a ``src_convertors/conf_conversion`` folder, you may delete it, or make sure that ``corpus_name`` in ``src_convertors/conf_conversion/conversion_settings.json`` is empty. In what follows, replace ``src_convertors/corpus/%corpus_name%`` with ``src_convertors/corpus``.

#### Option 2: you may have to work with multiple corpora in this Tsakorpus instance
In this case, each corpus will occupy a separate folder in ``src_convertors/corpus``. For each corpus, you have to create a directory ``src_convertors/corpus/%corpus_name%``. Two sets of configuration files are used, one located in ``src_convertors/conf_conversion`` (global) and the other, in ``src_convertors/corpus/%corpus_name%/conf_conversion`` (local). Whenever the two configuration files have the same fields, the one located inside the corpus directory overrides the global one. The main purpose of the ``src_convertors/conf_conversion/conversion_settings.json`` file (the one higher up in the tree) is to tell the converter where to look for the source files, which is why the parameters ``corpus_dir`` (which equals ``corpus`` by default) and ``corpus_name`` (set it to your current ``%corpus_name%``) have to be specified there. All the rest can be put to the lower configuration file.

### Source files
All source files have to have the same type and extension. The source files should be placed in ``src_convertors/corpus/%corpus_name%/%ext%``, where ``%ext%`` is their extension. If the extension is ``json``, you have to name this directory ``json_input`` to avoid name collision with the target directory. This directory can have any number of subdirectories of arbitrary depth. After the files have been converted, the resulting JSON files will be located in ``src_convertors/corpus/%corpus_name%/json``. If you run disambiguation after that, the disambiguated JSON files will be located in ``src_convertors/corpus/%corpus_name%/json_disamb``. If you have a media-aligned corpus, the source media files have to be located next to the corresponding ELAN/ EXMARaLDA/TEI files (and referenced there). The resulting media files (compressed and split into pieces) will appear in ``src_convertors/corpus/%corpus_name%/media``.

### Configuration files
The configuration files are ``conversion_settings.json`` and ``categories.json``. The latter describes which tags correspond to which grammatical categories and has the same format as ``categories.json`` in the main configuration directory (see ``configuration.md``). The ``conversion_settings.json`` has a number of key-value pairs that describe the contents of the corpus and tell the convertors how to deal with it:

* ``corpus_name`` -- the name of the corpus. During source conversion, this parameter is only used to determine the path to the corpus files. If it equals an empty string, it is assumed that you have only one corpus, which is located in ``src_convertors/corpus``. This field should be present in the global configuration file (``src_convertors/conf_conversion/conversion_settings.json``).

* ``meta_filename`` -- the name of the metadata file. This file should be located in ``src_convertors/corpus/%corpus_name%/``. CSV and Coma formats are recognized. In the case of CSV, the file should have tab-delimited format where each line represents one source file, the first column contains the name of the file and other columns contain all the metadata, one column per metafield. In the case of a Coma file, see also ``coma_meta_conversion`` parameter below.

* ``meta_fields`` -- list of metafield names. The values for the listed fields should appear in the metadata file in the same order (value for the first field in the first column, and so on). The name of the first metafield should be ``filename``. In the metadata file, it corresponds to the first column that contains the name of the file being described by that line.

* ``meta_files_ext`` -- boolean value that determines whether the filenames in the metadata file have extensions.

* ``meta_files_dir`` -- boolean value that determines whether the filenames in the metadata file have full paths starting from ``src_convertors/corpus/%corpus_name%/%ext%``. If it is set to false, it is assumed that the names of the source files are unique regardless of where they exist within the subtree.

* ``meta_files_case_sensitive`` -- boolean value that determines whether the filenames in the metadata file should be treated as case sensitive.

* ``nometa_skip`` (optional) -- boolean value that determines if the files not referenced in the metadata should be skipped. Defaults to ``false``.

* ``exclude_by_meta`` (optional) -- list of dictionaries, each of which contains a rule that determines what input documents should be skipped based on its metadata. The document is skipped if it conforms to at least one rule. A document conforms to the rule if its metadata contains all the key-value pairs present in the rule, while possibly containing other keys. Defaults to empty list.

* ``coma_meta_conversion`` (optional) -- dictionary that determines which communication-level description fields from a Coma metadata file have to be used and what metafield parameters they map to. Only usable with the Coma metadata files.

* ``parsed_wordlist_filename`` (optional) -- the name of the file with the morphologically annotated word list (for the converters which accept such a file). If you have several lists for different languages, the value should be a dictionary where keys are the names of the languages and values are the names of the files.

* ``parsed_wordlist_format`` (optional) -- the format of the annotated word list (currently, only the "xml_rnc" option is available, which means a list of XML-represented words in the format used in Russian National Corpus).

* ``gramtags_exclude`` (optional) -- list of strings that determines which gramtags should be excluded from the analyses. Defaults to empty list.

* ``speaker_meta_filename`` -- the name of the JSON file with metadata for individual speakers (for the ELAN convertor). The file should contain a dictionary where the keys are the codes of the speakers and the values are dictionaries with their metadata (fields and plain string/integer values).

* ``languages`` -- an array with the names of the languages which exist in the corpus.

* ``cg_disambiguate`` (optional) -- boolean value that determines whether your corpus has to be disambiguated with the Constraint Grammar rules after the annotation. Defaults to ``false``.

* ``cg_filename`` (optional) -- the names of the files with the Constraint Grammar rules (if you want to disambiguate your corpus). This files should be located in ``src_convertors/corpus/%corpus_name%/``. The value of this field is a dictionary where the keys are the names of the languages and the values are the names of the corresponding files. It is not obligatory to list all the languages you have.

* ``json_indent`` -- an integer that determines the number of whitespaces in one indent in the output JSON files. A value of -1 means no indentation and no newlines. You only need indentation if you want to look at the output files in a text editor; otherwise, do not turn it on to save disk space.

* ``gzip`` -- boolean value that determines if the resulting JSON file should be gzipped (which will take slightly more time, but much less disk space).

* ``transparent_punctuation`` (optional) -- regexp that determines which punctuation should be considered "transparent", i.e. should not be counted when calculating distances between words for a multiword query. This parameter influences the assignment of ``sentence_index`` values, which is added to words and punctuation marks at conversion time and then used in multiword queries at search time. Defaults to ``^ *$``.

* ``non_word_internal_punct`` (optional) -- list of non-letter characters that should never be treated as word-internal during tokenization (if built-in tokenization is used). Defaults to the newline character; whitespace is always included. For example, a tokenizer with default options will consider words like *bla-bla-bla* to constitute single tokens, but if you add hyphen to this list, *bla-bla-bla* will be split into three tokens.

* ``one_morph_per_cell`` (optional, for the ELAN convertor) -- boolean value that determines whether the annotation tiers contain one cell per morpheme/gloss (true) or one cell per entire glossing (false). For example, if the morpheme segmentation of the German word *ge-schloss-en* is kept in three different cells (*ge-*, *schloss* and *-en*), this value should be set to true. Defaults to ``false``.

* ``special_tokens`` (optional) -- dictionary that determines which tokens have to be treated in a special way when performing automatic tokenization. Each key is a regex, and the corresponding value is a dictionary that should be inserted in the JSON files as an object representing that token. E.g. ``"<(REPOST|USER|LINK)>": {"wtype": "punct"}`` would lead to tokens ``<REPOST>``, ``<USER>`` and ``<LINK>`` being tokenized as such (i.e. the angle brackets will not become separate tokens) and being treated as punctuation.

* ``capitalize_sentences`` (optional) -- Boolean value that determines if the first letter of the first word in each sentence should be automatically capitalized. Defaults to ``false``.

### The convertors
There are several source convertors for different input formats (see ``pipeline.md``). Each of them is a class located in one Python file:

* Plain text convertor: ``txt2json.py``.

* Convertor of morphologically annotated XML (possibly parallel) in one of the formats used by Russian National Corpus: ``xml_rnc2json.py``.

* HZSK ISO/TEI media-aligned files convertor: ``iso_tei_hamburg2json.py``.

* EXMARaLDA media-aligned files convertor (works only for non-segmented EXB files where events coincide with segments): ``exmaralda_hamburg2json.py``.

* ELAN media-aligned files convertor: ``eaf2json.py``.

* Fieldworks FLEX glossed texts convertor: ``xml_flex2json.py``.

* Convertor for JSON files obtained by harvesting social networks with my scripts: ``social_networks2json.py``.

* Plain text questionnaire convertor: ``txt_questionnaires2json.py``.

* Convertor for a YAML-like format used by the Morphy annotator: ``morphy_yaml2json.py``.

When you are ready with the configuration and the source files are stored in the relevant folder, all you have to do is to run the corresponding Python file and wait until it terminates. If your corpus consists of several parts stored in different formats, you may process them one by one with different source convertors and put the resulting JSONs in one place.

### Parsed word list
Convertors that read raw text (from .txt, .eaf and so on) allow you to have a separate file with morphological (or any other word-level) annotation for all or some of the word forms. The only available option for now is xml_rnc. An annotated word list in this format is a plain text file where each line is a valid XML that describes one unique word form. The lines should look as follows:

```
<w><ana lex="..." gr="..." ...></ana>(<ana....></ana>)*wordform</w>
```

Each word form starts with ``<w>`` and ends with ``</w>``. At the beginning, it has an analysis in an ``<ana>`` tag, or a concatenated list of possible analyses. The annotations is stored as attributes of the ``<ana>`` element. There are four reserved attribute names: ``lex`` for lemma, ``gr`` for comma-separated list of grammatical tags, ``parts`` for word segmentation into morphemes, and ``gloss`` for the glossing. All these fields are optional. If you have glossing, the number of morphemes should be equal to the number of glosses (hence, no hyphens in the stem are allowed). Apart from that, you can have any number of other attributes, e.g. ``trans_en`` for an English translation of the word. The actual word form must be located at the end, after the analyses.

### Disambiguation
If you choose to disambiguate your files using a Constraint Grammar file, they will be disambiguated after the primary conversion to JSON is complete. Your JSON files will be translated into CG format and stored in the ``cg`` directory, which will have language subdirectories. Multilanguage files will be split abd sentences in different languages will end up in different subdirectories. CG will process these files and put them to ``cg_disamb``. When this process is finished, the disambiguated files will be assembled, transformed back into JSON and stored in the ``json_disamb`` directory.

Disambiguation requires that you have a [CG3 executable](https://visl.sdu.dk/cg3/chunked/installation.html) and its directory be in the system PATH variable.

### RNC XML convertor
The RNC XML convertor understands XML files with morphologically annotated text in the format of Russian National Corpus. Currently, files with simple annotated texts ("Main subcorpus" and similar subcorpora) and parallel texts are supported. All data is contained in an ``<html>`` node, which has ``<head>`` and ``<body>`` daughters. ``<head>`` may contain metadata, which alternatively can be stored in a separate CSV table. Each metadata field is stored as ``<meta name="..." content="..."/>``.

In the case of simple annotated files, ``<body>`` contains paragraphs (``<p>``, possibly with a class attribute), which, in turn, contain sentences (``<se>``). Sentences contain words (``<w>``, see "Parsed word list" above), while punctuation is placed between the word nodes. If there are newlines between the words, they are ignored.

In parallel corpora, ``<body>`` contains translation units (``<para>``), which contain aligned setences. Each sentence has to have a ``lang`` attribute. The sentences are structures in the same way as in the case of simple texts. There may also be a ``<p>`` layer between ``<body>`` and ``<para>``.

Additional settings available for this convertor are the following:

* ``corpus_type`` -- string that says whether the corpus is parallel (``parallel``) or not (``main``). Defaults to ``main``.

* ``meta_in_header`` -- Boolean value that determines if the metadata should be searched in the XML header. If it is found, it undergoes certain name changes to comply with the tsakorpus requirements, see ``get_meta_from_header`` function in ``xml_rnc2json.py``.

* ``multivalued_ana_features`` -- list of strings that determines which analysis attributes have to be treated as carrying multiple values separated by a whitespace.

* ``language_codes`` -- dictionary that contains correspondences between the attribute values used to identify the language and the language names as specified in the ``languages`` list.

* ``clean_words_rnc`` -- Boolean value that determines if the tokens should undergo additional RNC-style cleaning (such as removal of the stress marks).

### Processing glossed text (xml_flex2json, iso_tei_hamburg2json, exmaralda_hamburg2json, eaf2json)
The default way of representing word-level morphological information in corpus linguistics is to assign each word a grammatical tag or a set of tags. Each tag represents one value of one particular morphosyntactic category. Part-of-speech (POS) tags are the most common example, but corpora of morphologically rich languages often have tags for other categories, such as tense, number or case. Information about lexical classes, such as animate nouns or motion verbs, can also be encoded in such a way. In tsakorpus, each tag is a string, and all tags are split into classes (e.g. "case tags") in ``categories.json`` (see ``configuration.md``).

In typology and language documentation, however, another approach is often used, which is called glossing. Glossing means that each word is split into morphemes, and each morpheme gets a label, called gloss, that summarizes the morphosyntactic values expressed in it. Stems/roots are usually glossed with their English translation, although translations in other major metalanguages are also common. The most widely adopted glossing styleguide is the [Leipzig glossing rules](https://www.eva.mpg.de/lingua/resources/glossing-rules.php).

However, if only glosses are present in the annotation, it may affect the search functionality of the corpus in a negative way. To address this problem, tsakorpus source convertors offer a possibility of converting one's glosses into grammatical tags. Please refer to ``gloss2tags.md`` for more detailed explanations and the format of the conversion rules.

### ELAN files conversion (eaf2json)
The convertor supports either ELAN files that have translation/comment tiers, but no morphological or other word-level annotation (such annotation can be added to the texts with the help of a parsed word list, see above), or ELAN files that also contain annotation (no parsed word list is needed in this case). Please refer to ``eaf2json.md`` for a detailed description of the ELAN tier structure expected by the convertor and a list of possible options.

Since text in different tiers belongs to different speakers and languages, it is important that you carefully describe where is what. First, all time-aligned tiers should have the "participant" attribute filled in with the code of the speaker. The codes may be explained in the speaker metadata file whose name is specified by the ``speaker_meta_filename`` parameter. Here is an example of how such a file could look like:

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

Second, tier types should be consistent throughout your corpus. If you have translations/comments, then translation/comment tiers should have a type of their own and have to be aligned with the main (transcription) tiers. The names of the tiers should be described in the following parameters in ``conversion_settings.json``:

* ``main_tiers`` -- an array with the names of the tiers that must be treated as transcription baseline. Names can be specified with regexes. Normally, this array will contain only one name.

* ``aligned_tiers`` -- an array with the names of translation/comment tiers that have a main tier as their parent. Names can be specified with regexes.

* ``analysis_tiers`` (optional) -- a dictionary describing which ELAN tiers correspond to which word-level analysis fields. The keys are the tier names (or regexes), and the possible values are currently ``word`` (tokens), ``parts`` (morpheme segmentation) and ``gloss`` (glosses).

* ``tier_languages`` -- a dictionary where keys are the names of the tier types (listed in the above two arrays) and the values are the names of their languages.

* ``ignore_tokens`` -- a string with a regex that describes which tokens should be skipped when aligning a token tier with a text tier.

* ``sentence_segmentation`` -- Boolean value that determines whether the convertor should resegment your text into sentences based on sentence-final punctuation set in ``sent_end_punc``. If ``false`` or absent, the time-aligned segments are treated as sentences.

* ``media_dir`` (optional) -- a string that indicates the path to the media files to be cut, if they are located in a different folder than the ELAN files.

The source audio/video files will be split into small pieces with [ffmpeg](https://www.ffmpeg.org/). You have to have it installed, and its directory should be in the system PATH variable.

### Fieldworks FLEX files conversion (flex2json)
To convert your FLEX database, you first have to export it using the "Verifiable generic XML" option. When exporting, the "Interlinear texts" section should be active, the "Analyze" tab should be open, and all relevant annotation tiers should be switched on and visible.

There are several problems with Fieldworks files. First, XMLs coming from different versions of Fieldworks look differently. Second, the exported XML does not have any connection to the dictionary (there should be one, but it does not work as of now), so any dictionary information not present in the interlinear will be lost. Third, Fieldworks does not have the lemma concept, so either you will have stems instead of lemmata, or you will have to somehow reconstruct lemmata from stems and grammatical information yourself. Fourth, all inflectional morphological information is stored in the glosses, so if some category is not overtly marked (which is common for e.g. singular, nominative/absolutive or imperative) and you do not have null morphemes, you will not be able to search for it unless you reconstruct it.

Tsakorpus FLEX convertor addresses the first problem by using flexible data extraction that was tested on different kinds of XML. Nevertheless, I cannot guarantee that it will work with any FLEX XML. I do not have any solution for second and third problems. The fourth problem can be solved by writing a set of rules which will allow the convertor to reconstruct hidden categories (see ``gloss2tags.md``).



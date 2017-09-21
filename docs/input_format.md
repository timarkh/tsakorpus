## Input JSON format
A corpus which can be indexed by tsakorpus is a collection of JSON or gzipped JSON files structured according to the rules described below. The corpus may contain any number of files scattered across a file system subtree starting with ``corpus/%your_corpus_name%``.

Each JSON file stores a dictionary representing one corpus document. Each dictionary should have the following keys:

* ``meta`` -- a dictionary with the metadata for the document.
* ``sentences`` -- an array of sentences the document consists of.

The document has, therefore, the following structure:

```
{
  "meta": {...},
  "sentences": [...]
}
```

### The metadata
The value of the ``meta`` key is a dictionary where keys are the names of the metafields and the values are strings. All metafields listed in the ``viewable_meta`` array in ``conf/corpus.json`` must be present in each document of the corpus. Other than that, there are no restrictions on metadata; the array may even be empty. However, there are several field names which get special treatment in tsakorpus:

* The value of ``filename`` is never included in the search results to avoid accidentally compromising the data of the author of the corpus.
* The ``title`` and ``author`` fields are displayed as document identifiers next to each context in the search results.

### The sentence list
The array with sentences is the main part of the document. Each sentence is a dictionary with the following keys:

* ``text`` -- a string with full text of the sentence.
* ``words`` -- an array with objects, each representing a token (word or punctuation mark) in the sentence together with all the annotation. There are several reasons why the text of the sentence (or at least most of it) is actually stored twice, first in the ``text`` field and second inside the word objects. One of them is allowing multiple (ambiguous) tokenization options for a single sentence. Another is allowing easy full-text search, which would have been impossible in elasticsearch without the ``text`` field. Yet another is the possibility of normalizing the tokens so that they can look differently in the sentence and in the analysis.
* ``lang`` -- a one-byte integer representing the language the sentence is written in. This number should be a valid index for the ``languages`` array in ``conf/corpus.json``.
* ``meta`` -- a dictionary with sentence-level metafields. Sentence-level metafields may include, for example, speaker data for multi-tier (dialogue) files or year in a document that includes data from different years. All metafields listed in the ``sentence_meta`` array in ``conf/corpus.json`` must be present in this dictionary. The values should be strings.
* ``para_alignment`` (only in parallel corpora, i.e. corpora with several languages where all or some of the sentences in one language are aligned to sentences in another language) -- a list with dictionaries, each representing an alignment of some part of the sentence with a part of another sentence in the corpus.
* ``src_alignment`` (only for media-aligned corpora) -- a list with dictionaries, each representing an alignment of some part of the sentence with a segment of a video or sound file.

The order of the sentences is important. The sentences should be grouped by language, and within each language they should be ordered exactly as they are ordered in the document. When the sentence collection is indexed, each sentence is assigned the keys ``_id``, ``prev_id`` and ``next_id``, the latter two being filled in based on the mutual position of the sentences in the JSON file.

The elements of the ``sentences`` array therefore look like this:

```
{
  "text": "...",
  "words": [...],
  "lang": ...,
  "meta": {...},
  "para_alignment": [...],
  "src_alignment": [...]
}
```

### Words
Each word in the ``words`` array is a dictionary with the following keys and values:

* ``wf`` -- a string with the token (word form), used for word search.
* ``wtype`` -- type of the token. Currently, two values are possible: "word" and "punct".
* ``off_start``, ``off_end`` -- character offsets indicating to which segment of the ``text`` string the word corresponds. As mentioned earlier, this can be useful for multiple overlapping tokenization variants, or when the ``wf`` value is normalized for search.
* ``next_word`` -- an integer or a list of integers indicating the index (in the ``words`` array) of the token immediately following the current token. This is also important for multiple tokenization variants.
* ``sentence_index`` -- an integer or an array of integers (again, for multiple tokenizations) indicating the 0-based position of the token in the sentence, not counting the leading and the tail punctuation marks (which do not have to have this field).
* ``ana`` -- a list of possible annotation variants for this word. If the word has no annotation, this key may be omitted.

Overall, a word dictionary looks like this:

```
{
  "wf": "...",
  "wtype": "word|punct",
  "off_start": ...,
  "off_end": ...,
  "next_word": ...,
  "sentence_index": ...,
  "ana": [...]
}
```

### Analyses
A word can have more than one analysis variant. Usually a word having multiple analyses is the result of automatic morphological annotation without subsequent disambiguation. However, this option is useful even in manually annotated corpora when there is no way to distinguish between several homonymous forms, or when the annotator has doubts (which happens especially often when annotating historical corpora). Search queries will find all words that have at least one analysis conforming to the query.

Each analysis is a dictionary with the following keys and values:

* ``lex`` -- lemma (dictionary form), a string.
* any number of keys starting with ``gr.`` (such as ``gr.pos`` or ``gr.case``) -- strings or arrays of strings that contain values of grammatical or lexical categories expressed in the word. The name of the category, as well as the value, should be listed in the ``categories.json`` file for the language the sentence is written in, otherwise this information will not be searchable. Each category can have multiple values (this can happen e.g. in case compounding when a stem attaches several case markers).
* ``gloss``, ``parts`` and ``gloss_index`` (only for corpora with glossing) -- strings representing the glosses for the word (``gloss``), segmentation of the word into morphemes (``parts``) and the combination of these two fields used during search (``gloss_index``). The ``gloss`` field should contain glossing according to the Leipzig glossing rules (the glosses can be arbitrary, but the format should be correct). The stem should be glossed as STEM instead of a short English translation, otherwise it would be impossible to make queries such as "find a genitive marker immediately following the stem". Glossing and segmentation into morphemes should not contain empty morphemes and glosses for them; all categories that are not overtly expressed in the word should be tagged using the ``gr.`` fields. The string ``gloss_index`` has the following format: GLOSS1{morpheme1}-GLOSS2{morpheme2}-... Each gloss is accompanied by the corresponding morpheme in curly brackets. All glosses are separated by hyphens; there should also be a hanging hyphen at the end of the string.
* any number of other keys with string values, such as ``trans_en``. All fields used here have to be listed in the ``word_fields`` array in ``conf/corpus.json``.

### Sentence example
Here is an example of a sentence from the Beserman corpus. It contains both parallel alignment (the texts are aligned with their Russian translations) and media alignment.

```
{
  "text": "[нрзб] tačʼe taos.",
  "words": [
    {
      "wf": "[",
      "wtype": "punct",
	  "off_start": 0,
      "off_end": 1,
      "next_word": 1,
      "sentence_index": 0
    },
    {
      "wf": "нрзб",
      "wtype": "word",
	  "off_start": 1,
      "off_end": 5,
      "next_word": 2,
      "sentence_index": 1
    },
    {
      "wf": "]",
      "wtype": "punct",
	  "off_start": 5,
      "off_end": 6,
      "next_word": 3,
      "sentence_index": 2
    },
    {
      "wf": "tačʼe",
      "wtype": "word",
	  "off_start": 7,
      "off_end": 12,
      "next_word": 4,
      "sentence_index": 3,
      "ana": [
        {
          "lex": "tačʼe",
          "gr.pos": "PRO",
          "gr.number": "sg",
          "gr.case": "nom",
          "parts": "tačʼe",
          "gloss": "STEM",
          "gloss_index": "STEM{tačʼe}-",
          "trans_ru": "такой"
        }
      ]
    },
    {
      "wf": "taos",
      "wtype": "word",
	  "off_start": 13,
      "off_end": 17,
      "next_word": 5,
      "sentence_index": 4,
      "ana": [
        {
          "lex": "ta",
          "gr.pos": "PRO",
          "gr.proType": "pers",
          "gr.number": "pl",
          "gr.case": "nom",
          "parts": "ta-os",
          "gloss": "STEM-PL",
          "gloss_index": "STEM{ta}-PL{os}-",
          "trans_ru": "он, она"
        }
      ]
    },
    {
      "wf": ".",
      "wtype": "punct",
	  "off_start": 17,
      "off_end": 18,
      "next_word": 6
    }
  ],
  "lang": 0,
  "meta": {
    "speaker": "AP",
	"gender": "M",
    "year": "2017"
  },
  "para_alignment": [
    {
      "off_start": 0,
      "off_end": 18,
      "para_id": 616
    }
  ],
  "src_alignment": [
    {
      "off_start_src": "0.05",
      "off_end_src": "1.3",
      "true_off_start_src": 0.05,
      "off_start_sent": 0,
      "off_end_sent": 18,
      "mtype": "audio",
      "src_id": "50_1300",
      "src": "AP_AS_2017.01.06_words_YZ_training-0-0.mp4"
    }
  ]
}
```
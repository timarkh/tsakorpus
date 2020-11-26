## ELAN convertor
This document explains what kind of ELAN files tsakorpus understands and how to convert them to tsakorpus JSON. See general information about source convertors and their settings files in ``src_convertors.md``.

### ELAN format
[ELAN](https://tla.mpi.nl/tools/tla-tools/elan/) is a widely adopted linguistic tool for transcribing audio or video. The sound-aligned transcription and (possibly) annotation are displayed in a set of hierarchically organized tiers and stored in XML files, which normally have the ``.eaf`` extension. The annotation may be carried out manually or exported from other tools, e.g. [FieldWorks](https://software.sil.org/fieldworks/).

The problem with the ELAN XML format is that the same data may be represented by multiple different tier structures, or by similar structures with different naming conventions. Different structures may look approximately the same from the user's perspective, but the convertor will have to process them differently. Therefore, it is impossible for a single convertor to accept any ELAN file. What follows is an explanation of what kind of structures the tsakorpus convertor understands.

* The file can be a transcription of a monologue (one speaker) or a dialogue (multiple speakers). If there are multiple speakers, then for each speaker, there should be a separate set of tiers that contains the transcription of their speech and the corresponding annotation.

* For each speaker, there should be only one time-aligned (independent, "main") tier. The "participant" attribute of this tier should contain a speaker ID (arbitrary string, e.g. their initials). The IDs of the speakers should be used consistently throughout the corpus, i.e. same speakers should have same IDs in different files, and different speakers should have different IDs. Other attributes (e.g. Annotator) are not taken into account. This main tier should contain either the transcription, or segment IDs (``ref`` tier, in FieldWorks/Toolbox terms). If it contains segment IDs, a transcription tier should be symbolically associated with it. If you use several representations of a transcription (e.g. in different scripts), you will have to treat one of them as primary.

* The level of segmentation granularity (duration of segments) is not important for the convertor and should be based on your linguistic needs. By default, one segment is treated as one sentence (i.e. basic search unit) in tsakorpus, so in a normal general-purpose corpus you would probably want to have one phrase / discourse unit / sentence per segment. There is also an option of conversion-time sentence segmentation (somewhat resembling the paradigm used in EXMARaLDA, where time alignment is decoupled from sentence segmantation). If you set ``sentence_segmentation`` parameter to ``true``, the convertor will join adjacent segments that do not have sentence-final punctuation (which is set as a regex in the ``sent_end_punc`` parameter). In this case, you can have multiple media alignment units within one sentence, which could correspond e.g. to intonational units. However, it is not possible to use the time alignment units in search, i.e. it is not possible to look for several words inside one such unit.

* All parallel translations, as well as alternative representations of the same transcription, sentence-level notes and sentence-level metadata, should reside in separate tiers symbolically associated with the main tier.

* If there is word-level annotation, e.g. morphological analysis, there should be a tokenized tier, which should be a symbolic subdivision of the "main" tier. You can list all tokens or just word tokens there. There should be no mismatches between words in the "main" tier and in the tokenized one, i.e. same words should look the same in the two tiers. All further annotation tiers (morpheme segmentation, glosses, POS, lemma etc.) should subdivide or be symbolically associated with this tokenized tier. If there are tokens with multiple analyses (e.g. resulting from a rule-based automatic morphological annotation that does not disambiguate based on the context), the next tier down the hierarchy (e.g. lemma) should subdivide the token. You will have as many lemmata as you have analyses for that token; each lemma cell will head one of the analyses. If you always have at most one analysis per token (which is the case for Fieldworks corpora), symbolic association can be used.

* You should explain the convertor which tier contain which information. There are several parameters in ``conversion_settings.json`` that do that: ``main_tiers``, ``aligned_tiers``, ``analysis_tiers`` and ``tier_languages``. Here is how they are used:

  * In what follows, "tier name" means either a string or a regular expression used to identify tiers in your EAFs. The convertor first looks for exact coincidences among tier types. If it does not find a match, it then uses the "tier name" as a regex to search among tier IDs. (Although having consistent and informative tier types throughout your corpus is best practice, there are corpora where you can only distinguish between e.g. lemma and POS tiers based on their IDs because they have the same type. This regex thing is a workaround for such cases.)
  
  * ``main_tiers`` is an array with the names of the top-level / time-aligned tiers. Normally, this array will contain only one name. There may be multiple such tiers in each file, each corresponding to one participant, but they normally have the same type and/or the same naming pattern, e.g. ``tx@.*``. "Main tiers" usually means "transcription tiers", but not always. For example, it is common to have the "reference tier" as a top-level tier and the transcription tier as its daughter in FLEX corpora. If you want to reorder the tiers in the web interface (e.g. make the transcription appear at the top and the sentence IDs on the bottom), you can do that by ordering corresponding languages in the ``languages`` array.

  * ``aligned_tiers`` is an array with the names of translation/comment/transcription tiers that have a main tier as their parent.

  * ``analysis_tiers`` (optional) is a dictionary describing which ELAN tiers correspond to which word-level analysis fields. The keys are the tier names (or regexes), and the possible values are currently ``word`` (tokens), ``lemma``, ``pos`` (part of speech), ``gramm`` (any number of comma-separated grammatical tags; may include part of speech as well), ``parts`` (morpheme segmentation) and ``gloss`` (glosses).

  * ``tier_languages`` is a dictionary where keys are the names of the tier types (listed in ``main_tiers`` and ``analysis_tiers``) and the values are the names of their languages.

* If you have glossing, there is another relevant parameter in ``conversion_settings.json``: ``one_morph_per_cell``. It is a boolean value that indicates whether each morpheme and each morpheme gloss occupy exactly one cell (``true``) or the whole morpheme segmentation / glossing is written inside one cell with hyphens as separators (``false``).

Here is an example of a relevant part of the ``conversion_settings.json`` file:

```
{
...
  "languages": ["klingon", "english", "english_note", "ref"],
  "tier_languages": {"tx@.*": "klingon", "ft@.*": "english", "not@.*": "english_note", "ref@.*": "ref"},
  "main_tiers": ["ref@.*"],
  "aligned_tiers": ["tx@.*", "ft@.*", "not@.*"],
  "analysis_tiers": {
    "word@.*": "word",
    "ps@.*": "pos",
    "mb@.*": "parts",
    "ge@.*": "gloss"
  },
  "one_morph_per_cell": true,
...
}
```

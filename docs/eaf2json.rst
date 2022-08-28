ELAN convertor
==============

This document explains what kind of ELAN files Tsakorpus understands and how to convert them to Tsakorpus JSON. See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Convertor: ``/src_convertors/eaf2json.py``.

ELAN format
-----------

ELAN_ is a widely adopted linguistic tool for transcribing audio or video recordings. The sound-aligned transcription and (possibly) annotation are displayed in a set of hierarchically organized tiers and stored in XML files, which normally have the ``.eaf`` extension. The annotation may be carried out manually or exported from other tools, e.g. FieldWorks_.

.. _ELAN: https://tla.mpi.nl/tools/tla-tools/elan/
.. _FieldWorks: https://software.sil.org/fieldworks/

The problem with the ELAN XML format is that the same data may be represented by multiple different tier structures, or by similar structures with different naming conventions. Different structures may look approximately the same from the user's perspective, but the convertor will have to process them differently. Therefore, it is impossible for a single convertor to accept any ELAN file. What follows is an explanation of what kind of structures the Tsakorpus convertor understands.

The file can be a transcription of a monologue (one speaker) or a dialogue (multiple speakers). If there are multiple speakers, then for each speaker, there should be a separate set of tiers that contains the transcription of their speech and the corresponding annotation.

The level of segmentation granularity (duration of segments) is not important for the convertor and should be based on your linguistic needs. By default, one segment is treated as one sentence (i.e. basic search unit) in Tsakorpus, so in a normal general-purpose corpus you would probably want to have one phrase, intonational unit or sentence per segment. However, there is an option of conversion-time sentence segmentation (somewhat resembling the paradigm used in EXMARaLDA_, where time alignment is decoupled from sentence segmentation). If you set ``sentence_segmentation`` parameter to ``true``, the convertor will join adjacent segments that do not have sentence-final punctuation (which is set as a regex in the ``sent_end_punc`` parameter). In this case, you can have multiple media alignment units within one sentence, which could correspond e.g. to intonational units. However, it is not possible to use the time alignment units in search, i.e. it is not possible to look for several words inside one such unit.

.. _EXMARaLDA: https://exmaralda.org/en/

Tier hierarchy
--------------

For each speaker, there should be only one time-aligned (independent, "main") tier. The ``PARTICIPANT`` attribute of this tier should contain a speaker ID (arbitrary string, e.g. their initials or a code like ``apk1948_m``). The IDs of the speakers should be used consistently throughout the corpus, i.e. same speakers should have same IDs in different files, and different speakers should have different IDs. Other attributes (e.g. ``ANNOTATOR``) are not taken into account. This main tier should contain either the transcription, or segment IDs (``ref`` tier, in FieldWorks/Toolbox terms). If it contains segment IDs, a transcription tier should be `symbolically associated <https://www.mpi.nl/corpus/html/elan/ch02.html>`_ with it. If you use several representations of a transcription (e.g. in different scripts), you will have to treat one of them as primary.

All translations into metalanguages, as well as alternative representations of the same transcription, sentence-level notes and sentence-level metadata, should reside in separate tiers symbolically associated with the main tier.

If you do not have tiers with token segmentation or word-level annotation (e.g. morphology), Tsakorpus will tokenize the text for you. If you provide a list of annotated word forms, it will also be annotated. See :doc:`src_convertors` for the list of relevant parameters.

If you do have word-level annotation, e.g. morphological analysis, there should be a tokenized tier, which should be a *symbolic subdivision* of the "main" tier. You can list all tokens (including punctuation) or just word tokens there. There should be no mismatches between words in the "main" tier and in the tokenized one, i.e. same words should look the same in the two tiers. All further annotation tiers (morpheme segmentation, glosses, POS, lemma etc.) should *subdivide* or *be symbolically associated with* this tokenized tier. If there are tokens with multiple analyses (e.g. resulting from a rule-based automatic morphological annotation that does not disambiguate based on the context), the next tier down the hierarchy (e.g. lemma) should subdivide the token. You will have as many lemmata as you have analyses for that token; each lemma cell will head one of the analyses. If you always have at most one analysis per token (which is the case for most manually annotated corpora), *symbolic association* can be used.

Configuration
-------------

Basic tier configuration
~~~~~~~~~~~~~~~~~~~~~~~~

You should explain the convertor which tier contain which information. There are several parameters in ``conversion_settings.json`` that do that. In what follows, *tier name* means either a string or a regular expression used to identify tiers in your EAFs. The convertor first looks for exact coincidences among `tier types <https://www.mpi.nl/corpus/html/elan_ug/ch03.html>`_. If it does not find a match, it then uses the *tier name* as a regex to search among tier IDs. (Although having consistent and informative tier types throughout your corpus is best practice, there are corpora where you can only distinguish between e.g. lemma and POS tiers based on their IDs because they have the same type. This regex thing is a workaround for such cases.)

Note that the term *languages* in the case of ELAN files is synonymous with *(non-analysis) tiers*. For example, if you have a "reference tier", or a tier with an alternative orthography, they will have to be treated as different languages.
  
- ``main_tiers`` is a list with the names of the top-level / time-aligned tiers (except the privacy tier, see below). Normally, this array will contain only one name. There may be multiple such tiers in each file, each corresponding to one participant, but they normally have the same type and/or the same naming pattern, e.g. ``tx@.*`` or ``.*_Text``. "Main tiers" usually means "transcription tiers", but not always. For example, it is common to have the "reference tier" as a top-level tier and the transcription tier as its daughter in FieldWorks corpora. If you want to reorder the tiers in the web interface (e.g. make the transcription appear at the top and the sentence IDs on the bottom), you can do that by ordering the corresponding languages in the ``languages`` list.

- ``aligned_tiers`` is a list with the names of translation/comment/transcription tiers that have a main tier as their parent.

- ``analysis_tiers`` (optional) is a dictionary describing which ELAN tiers correspond to which word-level analysis fields. The keys are the *tier names* (plain strings or regexes), and the values are the names of the analysis fields where the annotations from those tiers should end up. Pre-defined values, i.e. field names, are the following:
   
   - ``word`` for tokens/words
   - ``lemma`` for lemmata
   - ``pos`` for part of speech
   - ``gramm`` for any number of comma-separated grammatical tags (this may include part of speech as well; do not include a ``pos`` tier in this case)
   - ``parts`` for morpheme segmentation
   - ``gloss`` for glosses

Annotations that belong to these tiers are processed in a special way, e.g. grammatical tags are sorted by category. Any other value (e.g. ``trans_en``) will be added to the analyses as a field with the same name, and the annotations will be transferred there without change. If you have glosses, but do not have grammatical tags, you can generate them with :doc:`gloss-to-tag rules </src_convertors_gloss>`.

- ``tier_languages`` is a dictionary where keys are the names of the tier types (listed in ``main_tiers`` and ``analysis_tiers``) and the values are the names of their languages.

- ``one_morph_per_cell`` (Boolean, optional; only if you have glossing) -- whether the annotation tiers contain one cell per morpheme/gloss (``true``) or the whole morpheme segmentation / glossing is written inside one cell with hyphens as separators (``false``). For example, if the morpheme segmentation of the German word *ge-schloss-en* is kept in three different cells (*ge-*, *schloss* and *-en*), this value should be set to true. Defaults to ``false``.

- ``privacy_tier`` (string) -- type or ID (no regexes) of a time-aligned "privacy tier". The sound in the segments of this tier will be replaced with a beep when cutting the media files (regardless of the segment annotation). This can be used to hide sensitive data (e.g. personal data) from a recording without damaging the original file. Note that video is left as is, only the sound is changed.

Here is an example of a relevant part of the ``conversion_settings.json`` file:

.. code-block:: javascript
  :linenos:

  {
    // ...
    "languages": ["klingon", "english", "english_note", "ref"],
    "tier_languages": {
      "tx@.*": "klingon",
      "ft@.*": "english",
      "not@.*": "english_note",
      "ref@.*": "ref"
    },
    "main_tiers": ["ref@.*"],
    "aligned_tiers": ["tx@.*", "ft@.*", "not@.*"],
    "analysis_tiers": {
      "word@.*": "word",
      "ps@.*": "pos",
      "mb@.*": "parts",
      "ge@.*": "gloss"
    },
    "one_morph_per_cell": true,
    // ...
  }

Other configuration
~~~~~~~~~~~~~~~~~~~

- ``ignore_tokens`` (string, optional) -- a regex that describes which tokens should be skipped when automatically aligning a token tier with a text tier. Defaults to common Western punctuation marks.

- ``sentence_segmentation`` (Boolean, optional) -- whether the convertor should resegment your text into sentences based on sentence-final punctuation set in ``sent_end_punc``. If ``false``, the time-aligned segments are treated as sentences. Defaults to ``false``.

- ``sentence_segmentation_languages`` (list of strings, optional) -- if ``sentence_segmentation`` is set to ``true``, you can list languages for which sentence segmentation ahould take place. By default, sentences in all languages will be segmented.

- ``insert_speaker_marks`` (Boolean, optional) -- whether speaker marks (i.e. contents of the ``PARTICIPANT`` attribute of ELAN tiers) in brackets should be prepended at the start of each turn. Speaker marks in the linearized transcription make it easier for the user to understand who is saying what without listening to the sound file. Defaults to ``true``.

- ``speaker_marks_languages`` (list of strings, optional) -- if ``insert_speaker_marks`` is ``true``, you can list languages for which speaker marks should be inserted. By default, sentences in all languages are processed.

Span annotations
~~~~~~~~~~~~~~~~

The previous section described what to do with sentence-level and word-level annotations. What if you have span annotations that may cover multiple words or even sentences, e.g. code switching or some kind of discourse annotation?

Tsakorpus generally allows for span annotations, but with serious limitations. Span annotations can be displayed in the search results, but they cannot be searched for directly, unlike word-level and sentence-level annotations. One way to partially make them searchable is add these annotations to the sentence-level metadata. This way, it will be possible to search for them just like you search e.g. for sentences belonging to a particular speaker. The downside of this approach is that Tsakorpus cannot count the number of spans found, only the number of sentences where such spans exist. It also cannot search for words within certain kinds of spans, only for words in sentences that contain those spans.

Another problem is the way such annotations are stored in ELAN. ELAN has no dedicated means for that: you can only subdivide cells in daughter tiers, but not unite them into one span. This is why there are dozens of ways such annotations can be stored in ELAN files, all of them far from ideal from the point of view of machine readability.

Tsakorpus understands one of them. In this approach, your span annotation resides in a separate *time-aligned* tier, where cell boundaries are *visually* aligned with the boundaries in the token tier. Visual alignment is bad because it is not machine-readable, and there can be tiny mismatches invisible to the naked eye, but no significantly better solution exists at the moment. Tsakorpus will try to match tokens with the cell boundaries in such tiers. Then it will put spans to the JSON sentence for display purposes and add something to the sentence-level metadata.

The way span tiers should be processed is defined by the ``span_annotation_tiers`` dictionary. Its keys are *tier names*, and values are dictionaries with several pre-defined keys:

- ``languages`` (list of strings) -- names of languages/tiers the spans should be added to.
- ``sentence_meta`` (string) -- name of a new sentence-level metadata field associated with this span tier. Values of its annotations will be stored under this key in the sentences with which they overlap.
- ``styles`` (dictionary) -- determines :doc:`style classes </styles>` for each annotation value. The keys are annotation values, the values are style class names. Styles determine how the spans will be highlighted in the search results. You may add styles only to certain values.

Here is an example:

.. code-block:: javascript
  :linenos:

  "span_annotation_tiers": {
    "rp@.*": {
      "languages": ["joola"],
      "sentence_meta": "rp",
      "styles": {
        "Discourse Report": "disc_rep",
        "Discourse Reporting Event": "disc_rep_event",
        "Quotative": "disc_rep_quotative",
        "Demonstrative": "disc_rep_demonstrative",
        "Other": "disc_rep_other"
      }
    }
  }

Here, all tiers whose name starts with ``rp@`` are treated as span tiers. The spans should only be added to the sentences in the ``joola`` language. The values from this tier's segments will be added to the sentence-level metadata field called ``rp``. Spans with five specific values will be additionally assigned certain style classes so that they can be highlighted in the search hits.

Media files
-----------

The source audio/video files will be split into small pieces with ffmpeg_. You have to have it installed. If you are working in Windows, then its directory should be in the ``PATH`` variable.

.. _ffmpeg: https://www.ffmpeg.org/


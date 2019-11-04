## ELAN convertor
This document explains what kind of ELAN files tsakorpus understands and how to convert them to tsakorpus JSON. See general information about source convertors and their settings files in ``src_convertors.md``.

### ELAN format
[ELAN](https://tla.mpi.nl/tools/tla-tools/elan/) is a widely adopted linguistic tool for transcribing audio or video. The sound-aligned transcription and (possibly) annotation are displayed in a set of hierarchically organized tiers and stored in XML files, which normally have the ``.eaf`` extension. The annotation may be carried out manually or exported from other tools, e.g. [FieldWorks](https://software.sil.org/fieldworks/).

The problem with the ELAN XML format is that the same data may be represented by multiple different tier structures, or by similar structures with different naming conventions. Different structures may look approximately the same from the user's perspective, but the convertor will have to process them differently. Therefore, it is impossible for a single convertor to accept any ELAN file. What follows is an explanation of what kind of structures the tsakorpus convertor understands.

* The file can be a transcription of a monologue (one speaker) or a dialogue (multiple speakers). If there are multiple speakers, then for each speaker, there should be a separate set of tiers that contains the transcription of their speech and the corresponding annotation.

* For each speaker, there should be only one time-aligned (independent, "main") tier. The "participant" attribute of this tier should contain a speaker ID (arbitrary string, e.g. their initials). The IDs of the speakers should be used consistently throughout the corpus, i.e. same speakers should have same IDs in different files, and different speakers should have different IDs. Other attributes (e.g. Annotator) are not taken into account. This main tier should contain either the transcription, or segment IDs (``ref`` tier, in FieldWorks/Toolbox terms). If it contains segment IDs, a transcription tier should be symbolically associated with it. If you use several representations of a transcription (e.g. in different scripts), you will have to treat one of them as primary.

* The level of segmentation granularity (duration of segments) is not important for the convertor and should be based on your linguistic needs. However, one segment is treated as one sentence (i.e. basic search unit) in tsakorpus, so in a normal general-purpose corpus you would probably want to have one phrase / discourse unit / sentence per segment.

* All parallel translations, as well as alternative representations of the same transcription and sentence-level metadata, should reside in separate tiers symbolically associated with the main tier.

* If there is word-level annotation, e.g. morphological analysis, there should be a tokenized tier, which should be a symbolic subdivision of the "main" tier. You can list all tokens or just word tokens there. There should be no mismatches between words in the "main" tier and in the tokenized one, i.e. same words should look the same in the two tiers. All further annotation tiers (morpheme segmentation, glosses, POS, lemma etc.) should subdivide or be symbolically associated with this tokenized tier.

(UNFINISHED)

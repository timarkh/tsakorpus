Tags or glosses?
================

Introduction
------------

The default way of representing word-level morphological information in mainstream corpus linguistics is to assign each word a grammatical *tag* or a set of tags. Each tag represents one value of one particular morphosyntactic category. Part-of-speech (POS) tags are the most common example, but corpora of morphologically rich languages often have tags for other categories, such as tense, number or case. Information about lexical classes, such as animate nouns or motion verbs, can also be encoded in such a way. In Tsakorpus, each tag is a string, and all tags are split into classes (e.g. "case tags") in :doc:`categories.json </categories>`.

In typology and language documentation, however, another approach is often used, which is called *glossing*. Glossing means that each word is split into morphemes, and each morpheme gets a label, called *gloss*, that summarizes the morphosyntactic values expressed in it. Stems/roots are usually glossed with their English translation, although translations in other major metalanguages are also common. The most widely adopted glossing styleguide is the `Leipzig glossing rules <https://www.eva.mpg.de/lingua/resources/glossing-rules.php>`_. Glossed texts is what you will have if you annotate your texts in FieldWorks or Toolbox.

Example
-------

Here is a simple Hungarian example:

- Wordform: **korpuszaimban** ("in my corpora")
- Morpheme breaks: **korpusz-aim-ban**, glosses: *corpus-PL.1sPOSS-INESS*
- Tags: *N,inanim,pl,1.p,sg.p,iness*

(The actual tags could be different, e.g. "1poss" or "p1" instead of "1.p"; there is no universally accepted list of tags. Also the format is different in different corpora; Tsakorpus uses comma-delimited lists.) This word contains three morphemes: the stem with the meaning "corpus", the portmanteau plural/possessive marker (**-aim-**) and the inessive case marker (**-ban**). It is an inanimate (tag *inanim*) noun (tag *N*) with four morphosyntactic values expressed by inflectional morphology: plural number (*pl*), first person of the possessor (*1.p*), plurality of the possessor (*pl.p*), and inessive case (*iness*).

Aren't glosses and grammatical tags basically the same thing?
-------------------------------------------------------------

Glosses and grammatical tags generally represent the same kind of information, i.e. which morphosyntactic categories are expressed in a word, but in a different way. Here are some of the differences:

- Tags constitute an unordered set, while glosses tell you how the exponents of certain values are positioned relative to one another inside one word.
- With tags, you do not know which category is expressed by which morpheme.
- Each tag ideally expresses one particular value of one particular category, while there is generally no one-to-one correspondence between categories and morphemes. One category can be expressed by several different morphemes, or several categories can be expressed by one morpheme.

It may seem that, putting aside lexical class glosses such *inanim* above, tags would be redundant compared to glosses. However, this is not always the case. If only glosses are present in the annotation, it may negatively affect the search functionality of the corpus. Consider, for example, Udmurt (Uralic > Permic) word **bi̮dtiśkemmi̮**. Here is how it could be glossed:

- morpheme breaks: **bi̮dt-iśk-em-mi̮**
- glosses: *finish-PASS-PST.EVID-1PL.POSS* (or *finish-PRS.12-PST.EVID-1PL.POSS*)

The word is actually a 1pl evidential past of the verb "to finish" and translates as "they say / it turns out that we finished (something)". The corresponding tags would be *V,pst.evid,1,pl*. The problem with these suffixes is that they actually participate in multiple different forms across verbal paradigm. **-iśk-** is a passive suffix, which also for historical reasons happens to be a part of 1sg, 1pl, 2sg and 2pl present tense markers. (Since it lost its passive meaning in these contexts, it can be considered a separate homonymous morpheme and glossed *PRS.12*). It is also normally present in the 1pl and 1sg forms of the evidential past, which is why we see it in this word. However, most linguists probably would not gloss it as "EVID.1" here because that would conceal its obvious connection to the 1/2 person present tense suffix. This is because glossing is generally thought of as a tool for labeling morphemes rather word forms. Similarly, the **-mi̮** suffix is actually a nominal possessive suffix: possessive suffixes together with historically derivational suffixes such as **-iśk-** are used to differentiate between persons and numbers of the subject in the evidential past and some other forms. This means that the user must understand that *1PL.POSS* in the context of the evidential past means "first person, plural number of the subject", while the same suffix on nouns means "first person, plural number of the possessor".

All of this makes it relatively difficult to interpret such forms without deep understanding of the grammar of the language. More importantly, it is almost impossible to search for some morphosyntactic values using glosses. For example, "first person forms of all verbs" could hardly be found because the person is expressed rather differently in different tense forms of Udmurt verbs.

There are also additional reasons why glosses are not always the most transparent tool for morphosyntactic annotation:

- With glosses, you have to split the word into segmental morphemes. Sometimes it not easy to do, especially in the case of non-concatenative morphology, or when using an established orthography where letter boundaries do not coincide with phoneme boundaries.
- There is an issue of values expressed by the *absence* of some morpheme or morphemes. Such values either have to be written as null morphemes (e.g. **table-0** glossed as *table-SG*) or have to be mentioned as glosses for covert categories in brackets (e.g. **table** glossed as *table[SG]*). The former option is so verbose that it is usually too incovenient to use. The latter is also difficult to use consistently; besides, it is not supported by software like FieldWorks.
- With glossing, it is not so easy to distinguish between lexical and grammatical/functional morphemes, at least for a machine. If you see a word glossed as *table-SG*, how does the computer now that *SG* is a grammatical gloss that has to be searchable as such, while *table* is a lexical gloss (translation of the stem)? Certain conventions could help, such as reserving the uppercase for grammatical glosses, but they do not yield unambiguous results. For example, the 1sg English pronoun *I* would be indistinguishable from a grammatical gloss because it is uppercase. Also, sometimes linguists gloss "small words" with uncertain meaning as e.g. *PTCL* or *INTERJ*.

Nevetheless, glosses can also be useful, for example because they provide positional information absent in the tags. The tags are usually interpreted as a sack of values: their mutual order has no connection to the mutual order of the morphemes that express those values (which comes as no surprise, since there is no one-to-one correspondence between morphemes and grammatical values). Glosses, on the other hand, contain this information. This might be important for morphologically rich languages. For example, Udmurt has a number of derivational verbal suffixes, such as passive or causative, that can have different mutual order, determined by their scope. If you have glosses, you can search for all verbs where a passive is followed by a causative, but not vice versa. With mere tags that would be impossible.

All in all, both representations of grammatical information can be useful, but tags are probably better suited for corpus search purposes.

Glosses-to-tags conversion
--------------------------

If you only have glosses in your corpus, Tsakorpus source convertors offer a possibility of :doc:`converting </src_convertors_gloss>` them into grammatical tags. This way, both kinds of information will be available for search. To do so, you will have to prepare a set of rules that will tell the source convertor which tags to add for which gloss or combination of glosses.

It is worth noting that the part-of-speech tag is present in the texts annotated in FieldWorks or Toolbox, so there is no need to extract the POS information from glosses (which would be very difficult).

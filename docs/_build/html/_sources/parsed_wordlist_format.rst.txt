Morphological analysis
======================

If your texts already have morphological annotation, you can skip this page.

Analyzed word lists
-------------------

Convertors that read raw text (from ``.txt``, ``.eaf`` and so on) allow you to have a separate file with morphological (or any other word-level) annotation for all or some of the word forms. The only available option for now is ``xml_rnc``, the XML format used in the Russian National Corpus. An annotated word list in this format is a plain text file where each line is a valid XML that describes one unique word form. The lines should look as follows::

    <w><ana lex="..." gr="..." ...></ana>(<ana....></ana>)*wordform</w>

Each word form starts with ``<w>`` and ends with ``</w>``. At the beginning, it has an analysis in an ``<ana>`` tag, or a concatenated list of multiple possible analyses. The annotation is stored in the attributes of the ``<ana>`` element. There are four reserved attribute names:

- ``lex`` for lemma
- ``gr`` for comma-separated list of :doc:`grammatical tags <tags_vs_glosses>`
- ``parts`` for word segmentation into morphemes
- ``gloss`` for the glossing.

All these fields are optional. If you have glossing, the number of morphemes should be equal to the number of glosses (hence, no hyphens in the stem are allowed). Apart from that, you can have any number of other attributes, e.g. ``trans_en`` for an English translation of the word. The actual word form must be located at the end, after the analyses.

Disambiguation
--------------

If you choose to disambiguate your files using a Constraint Grammar file, they will be disambiguated after the primary conversion to JSON is complete. Your JSON files will be translated into CG format and stored in the ``cg`` directory, which will have language subdirectories. Multilingual files will be split, and sentences in different languages will end up in different subdirectories. CG will process these files and put them to ``cg_disamb``. When this process is finished, the disambiguated files will be assembled, transformed back into JSON and stored in the ``json_disamb`` directory.

Disambiguation requires that you have CG3 installed. On Linux, you can just run ``apt-get install cg3``. On Windows, `download the executable <https://visl.sdu.dk/cg3/chunked/installation.html>`_ and add its path to the ``PATH`` variable.

Note that the convertors can only process certain types of CG3 output. Commands like ``REMOVE``, ``SELECT`` and ``ADD`` will definitely work.

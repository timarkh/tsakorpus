Plain text convertor
--------------------

This document explains how to convert plain text files to Tsakorpus JSON. See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Convertor: ``/src_convertors/txt2json.py``.

This is the simplest possible convertor. It processes unannotated plain text from ``.txt`` files. Files should be encoded in UTF-8 without BOM. If you want to add morphological analysis at the time of conversion, you have to prepare a :doc:`pre-analyzed word list </parsed_wordlist_format>`.
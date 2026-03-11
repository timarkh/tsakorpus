Praat TextGrid convertor
========================

This document explains how to convert TextGrid files to Tsakorpus JSON. See general information about source convertors and their configuration files :doc:`here </src_convertors>`.

Convertor: ``/src_convertors/textgrid2json.py``.

TextGrid format
---------------

You should *never* use Praat_ for sound-aligning corpus files. It is designed for phonetic analysis, not for storing or annotating corpus data. There is no way to align tiers to each other (e.g., translations with the source).

.. _Praat: https://www.fon.hum.uva.nl/praat/

Still, if you happen to be in possession of a heap of Praat files used exactly for this purpose, and they only have transcription (no translations or annotation), then you can use this convertor.

You can have any number of interval tiers, one per speaker. In addition, you can have one privacy tier. You can also exclude some tiers from conversion.

Configuration
-------------
Basic configuration
~~~~~~~~~~~~~~~~~~~

You should explain the convertor your tier configuration by editing ``conversion_settings.json``. The parameters are a small subset of the parameters used by the :doc:`ELAN convertor </eaf2json>`.
  
- ``main_tiers`` is a list with the names of the transcription tiers associated with speakers. It may contain strings or regexes.

- ``tier_languages`` is a dictionary where keys are the names of the tier types (listed in ``main_tiers``; possibly regexes) and the values are the names of their languages.

- ``privacy_tier`` (string) -- the name of a "privacy tier", if any. The sound in the segments of this tier will be replaced with a beep when cutting the media files (regardless of the segment annotation). This can be used to hide sensitive data (e.g., personal data) from a recording without damaging the original file. Note that video is left as is, only the sound is changed.

Other configuration
~~~~~~~~~~~~~~~~~~~

The following parameters work as in the :doc:`ELAN convertor </eaf2json>`: ``ignore_tokens``, ``sentence_segmentation``, ``sentence_segmentation_languages``, ``insert_speaker_marks``, ``speaker_marks_languages``.

Media files
-----------

The source audio/video files have to be named exactly like the corresponding TextGrid (except the extension) and be located in the same directory. They will be split into small pieces with ffmpeg_. You have to have it installed. If you are working in Windows, then its directory should be in the ``PATH`` variable.

.. _ffmpeg: https://www.ffmpeg.org/


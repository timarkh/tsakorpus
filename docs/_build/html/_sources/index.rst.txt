.. tsakorpus documentation master file, created by
   sphinx-quickstart on Tue Apr 13 09:23:05 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Tsakorpus
=========

Introduction
------------

Tsakorpus is a linguistic corpus platform. You can use it to publish your corpora online, so that linguists can search in them without downloading the source files or any software. The backend of Tsakorpus is written in Python (with flask_) and uses Elasticsearch_ for storing and querying data.

Here is a fact sheet about Tsakorpus:

* It's completely free and open-source.
* You can make complex queries through its web interface without having to learn any query language.
* Although corpus setup requires some technical knowledge, no actual programming is required.
* Tsakorpus supports `regular expressions <https://www.regular-expressions.info/>`_, multi-word queries with distances, subcorpus selection etc.
* Tsakorpus supports corpora with morphological annotation (including ambiguous analyses) and glossing.
* Tsakorpus supports parallel corpora with any number of languages/tiers.
* Tsakorpus supports sound- and video-aligned corpora.
* You can have multiple interface languages in Tsakorpus.
* Tsakorpus has been tested on corpora ranging from 0.01 to 300 million tokens. Larger corpora are probably ok if you give it more memory.
* Tsakorpus includes a number of source convertors that can turn raw or annotated texts in widely used formats in the JSON format it requires.
* Tsakorpus is only suitable for publishing and searching in your corpus, but **not for annotating or managing your corpus data**.

See :doc:`FAQ </faq>` for a short list of commonly asked questions, which can help you decide if Tsakorpus suits your purposes. If you want to learn how to set up Tsakorpus, please go to :doc:`overview`.

If you are not sure Tsakorpus is what you need, you can compare it to other common corpus analysis software:

- Online corpus platforms:
   - NoSketchEngine_
   - ANNIS_
   - `Corpus Workbench`_
   - SpoCo_
   - Korp_
- Tools for analyzing texts on your own computer:
   - AntConc_
   - TXM_

.. _Elasticsearch: https://www.elastic.co/downloads/elasticsearch
.. _flask: https://flask.palletsprojects.com/en/1.1.x/
.. _AntConc: https://www.laurenceanthony.net/software/antconc/
.. _TXM: https://sourceforge.net/projects/txm/
.. _NoSketchEngine: https://nlp.fi.muni.cz/trac/noske
.. _ANNIS: https://corpus-tools.org/annis/
.. _Corpus Workbench: http://cwb.sourceforge.net/index.php
.. _Korp: https://spraakbanken.gu.se/en/tools/korp/distribution-and-development
.. _SpoCo: https://bitbucket.org/michauw/spoco/src/master/

Requirements
------------

Tsakorpus was tested on Ubuntu and Windows. Its dependencies are the following:

- Elasticsearch 7.x (tested on 7.6-7.10)
- Python >= 3.5
- Python modules: ``elasticsearch 7.x``, ``flask``, ``Flask-Babel``, ``lxml``, ``ijson``, ``xlsxwriter`` (you can use ``requirements.txt``)
- for converting media-aligned corpora: ``ffmpeg``
- it is recommended to deploy Tsakorpus through `apache2 with wsgi`_ or nginx_

.. _apache2 with wsgi: https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/
.. _nginx: https://flask.palletsprojects.com/en/1.1.x/deploying/fastcgi/#configuring-nginx

The following resources are used by Tsakorpus, but do not need to be installed:

- jQuery_
- video.js_ media player
- videojs-youtube_ plugin
- `Bootstrap 5.0`_ toolkit
- D3.js_ visualization library

.. _jQuery: https://jquery.com/
.. _video.js: http://videojs.com/
.. _videojs-youtube: https://github.com/videojs/videojs-youtube
.. _Bootstrap 5.0: http://getbootstrap.com/
.. _D3.js: https://d3js.org/

License
-------

The software is distributed under MIT license.


.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   faq
   overview
   forks
   src_convertors
   parsed_wordlist_format
   tags_vs_glosses
   src_convertors_gloss
   txt2json
   eaf2json
   xml_flex2json
   xml_rnc2json
   iso_tei_hamburg2json
   data_model
   categories
   configuration
   indexator
   interface_languages
   transliteration
   styles


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

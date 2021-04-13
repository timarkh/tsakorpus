.. tsakorpus documentation master file, created by
   sphinx-quickstart on Tue Apr 13 09:23:05 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Tsakorpus
=========

Introduction
------------

Tsakorpus is a linguistic corpus platform. You can use it to publish your corpora online, so that linguists can search in them without downloading the source files or any software. The backend of Tsakorpus is written in Python (with flask) and uses elasticsearch for storing and querying data.

Here is a brief list of facts about Tsakorpus:

* It's completely free and open-source.
* You can make complex queries through its web interface without having to learn any query language.
* Although corpus setup requires some technical knowledge, no actual programming is required.
* Tsakorpus supports corpora with morphological annotation (including ambiguous analyses) and glossing.
* Tsakorpus supports parallel corpora with any number of languages/tiers.
* Tsakorpus supports sound- and video-aligned corpora.
* You can have multiple interface languages in Tsakorpus.
* Tsakorpus has been tested on corpora ranging from 0.01 to 300 million tokens. Larger corpora are probably ok if you give it more memory.
* Tsakorpus includes a number of source convertors that can turn raw or annotated texts in widely used formats in the JSON format it requires.
* Tsakorpus is only suitable for publishing and searching in your corpus, but **not for annotation**.

If you are not sure Tsakorpus is what you need, you can compare it to other common linguistic software:

* Antconc
* NoSketchEngine
* ANNIS
* Spoco
* MTAS

See ``docs/faq.md`` (or its Russian version, ``docs/faq_ru.md``) for a short FAQ list. See ``docs/pipeline.md`` for an overview of how to use tsakorpus.

## Requirements

Tsakorpus was tested on Windows and Ubuntu. Its dependencies are the following:

* elasticsearch 7.x (tested on 7.6 and 7.10)
* python >= 3.5
* python modules: elasticsearch 7.x, flask, lxml, ijson, Flask-Babel, xlsxwriter (you can use requirements.txt)
* for converting media-aligned corpora: ffmpeg
* it is recommended to deploy tsakorpus through apache2 with wsgi or nginx

Please note that right now, a somewhat outdated version of Elasticsearch is required. I am going to switch to Elasticsearch 7 by the end of 2020.

The following resources are used by tsakorpus, but do not need to be installed:

* [jQuery](https://jquery.com/) library
* [video.js](http://videojs.com/) media player
* [videojs-youtube](https://github.com/videojs/videojs-youtube) plugin
* [bootstrap](http://getbootstrap.com/) toolkit
* [D3.js](https://d3js.org/) visualization library

## License

The software is distributed under MIT license (see LICENSE.md).


.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

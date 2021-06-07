# Tsakorpus 2.0

If you want to use Tsakorpus, download the most recent version from this repository.

## Overview

Tsakorpus is a linguistic corpus search platform which uses elasticsearch for storing and querying data. It consists of a set of source convertors, an indexator and a web interface with a search engine. The source convertors transform a corpus in one of the several supported formats into a set of JSON documents in tsakorpus format. The indexator puts these documents into the database together with the frequency data for words that it calculates on the fly. The web interface, written in python+flask, allows the user to make complex queries using GUI and view the search results. The search queries are sent to the back-end as GET queries and transformed to JSON elasticsearch queries on the server. The search results are partly transformed to HTML on the server, sent back to the front-end as JSON through Ajax requests and displayed on the results page by a set of JavaScript/jQuery functions.

Tsakorpus supports corpora with morphological annotation, special gloss search, multi-word search, subcorpus selection, automatic transliteration, word distribution charts, parallel corpora, and media-aligned corpora. Multiple interface languages are supported with Flask-Babel.

## Documentation

All documentation is available [here](https://tsakorpus.readthedocs.io/en/latest/). If you are not sure if Tsakorpus is what you need, read the [FAQ](https://tsakorpus.readthedocs.io/en/latest/faq.html). If you want to set up a corpus, start [here](https://tsakorpus.readthedocs.io/en/latest/overview.html).

Feel free to ask questions or discuss Tsakorpus [on the Discussions page](https://github.com/timarkh/tsakorpus/discussions/) or post [issues](https://github.com/timarkh/tsakorpus/issues).

## Requirements

Tsakorpus was tested on Windows and Ubuntu. Its dependencies are the following:

* elasticsearch 7.x (tested on 7.6-7.12)
* python >= 3.5
* python modules: elasticsearch 7.x, flask, lxml, ijson, Flask-Babel, xlsxwriter (you can use requirements.txt)
* for converting media-aligned corpora: ffmpeg
* it is recommended to deploy tsakorpus through apache2 with wsgi or nginx

The following resources are used by tsakorpus, but do not need to be installed:

* [jQuery](https://jquery.com/) library
* [jQuery-Autocomplete](https://github.com/devbridge/jQuery-Autocomplete)
* [video.js](http://videojs.com/) media player
* [videojs-youtube](https://github.com/videojs/videojs-youtube) plugin
* [bootstrap](http://getbootstrap.com/) toolkit
* [D3.js](https://d3js.org/) visualization library
* [KioskBoard](https://github.com/furcan/KioskBoard) virtual keyboard

## License

The software is distributed under MIT license (see LICENSE).

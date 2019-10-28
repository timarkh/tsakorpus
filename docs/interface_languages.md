## How to translate the web interface
Tsakorpus uses flask-Babel for internationalization. The idea is that whenever you have some text in the HTML templates of the corpus that should look different in different languages, you write an expression like ``{{ _('Some text') }}`` instead of just ``Some text`` and then put translations for this label in  ``search/web_app/translations/%language_code%/LC_MESSAGES/messages.po`` files for each of the languages you have. This document discusses how and when you should edit these files.

All labels that can theoretically be used in any corpus already have translations into English and Russian, so you probably do not need to edit the HTML templates or the existing translations (although you can do so if you want to change the looks of the interface). However, there are corpus-specific labels that you have to describe for your corpus. You can do so by editing ``messages.po`` files in any plain-text editor (not MS Word please). In the beginning of each file, you will find several sections headed with comments starting with #. These comments describe what kind of data you have to put there. The sections are pre-populated so that you have an example of how to do that, but chances are you will have to add something there. Nothing bad happens if you leave some redundant translations there.

Each entry consists of two lines, the first starting with ``msgid``, the second with ``msgstr``. The ``msgid`` line contains the label in one of the HTML templates that has to be translated, and the ``msgstr`` contains the translation. Both should be in double quotes and can contain HTML tags and entities, if needed.

The following groups of labels have to be filled in:

* ``corpus_title``: the title of your corpus that will be displayed in the upper part of the search page.

* Labels starting with ``langname_``: names of the languages that you have in the corpus.

* Labels starting with ``translitname_``: names of the output transliteration options that you have in the corpus.

* Labels starting with ``inputmethod_``: names of the user input transliteration options that you have in the corpus.

* Labels starting with ``metafield_``: names of your metadata fields.

* Labels starting with ``metavalue_``: names of your non-numeric metadata values.

* Labels starting with ``wordfield_``: names of all additional word-level annotation fields you have (except Word, Lemma, Grammar and Gloss).

* Labels for each of the grammar/gloss tooltips you have in the Grammar selection or Gloss selection window (described in the ``gramm_selection`` and ``gloss_selection`` fields in ``corpus.json``).

### Languages other than English and Russian
If you want to add other languages to your interface, do the following:

* Make a copy of one of the language directories in ``search/web_app/translations`` and name it with the code of the new language.

* Translate the ``messages.po`` file in that directory into that language.

* Add the language code and name to the ``interface_languages`` dictionary in ``corpus.json``.

* If you want a language other than English to be the default option, change the string ``en`` in the line ``BABEL_DEFAULT_LOCALE='en'`` in ``search/web_app/__init__.py`` to the code of that language.

* Make a copy of one of the ``search/web_app/templates/help_dialogue_%language_code%.html`` files, filling in the code of the language, and translate it in any plain-text editor.

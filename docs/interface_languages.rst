Interface languages
===================

You can translate your interface into any languages you want. The user will be able to choose a language by clicking a language code link at the top of the search page. Basic interface translations into several languages are already built in:

- English (``en``);
- French (``fr``);
- Russian (``ru``);
- Chinese (``zh``, partial);
- Albanian (``sq``);
- Eastern Armenian (``hy``).

Configuring interface languages
-------------------------------

If all translations you need already exist, you have to adjust the following configuration parameters in :doc:`corpus.json </configuration>`:

- ``interface_languages`` -- list with codes of all web interface languages that should be available in your corpus.
- ``default_locale`` -- code of the default interface language.

Translating the interface
-------------------------

There are a number of files that have to be translated. All messages and short captions are translated with the help of `Flask-Babel`_. Language versions of long pages and popups are kept as separate HTML templates. Here is the list of files that have to be translated:

- ``Flask-Babel`` messages in multiple files in ``/search/web_app/translations/%LANG_CODE%`` (see below).
- Help page: ``search/web_app/templates/modals/help_dialogue_%LANG_CODE%.html``.
- Greeting popup: ``search/web_app/templates/index/greeting_%LANG_CODE%.html``.

.. _Flask-Babel: https://flask-babel.tkte.ch/

Messages and captions
~~~~~~~~~~~~~~~~~~~~~

Each language folder in ``/search/web_app/translations/`` contains a number of files that describe interface messages and captions. Each time you launch the corpus on the server, these files are joined in a special way to produce a single Flask-Babel translation file called ``messages.po`` and its compiled version, ``messages.mo``. The idea is that whenever you have some text in the HTML templates of the corpus that should look different in different languages, you write an expression like ``{{ _('Some text') }}`` instead of just ``Some text``. This placeholder is replaced by the translation found in the language-specific ``message.mo`` file under the key ``"Some text"``, depending on the language the user shooses.

- ``header.txt`` contains the header of the ``messages.po`` file and includes basic metadata and plural settings. You do not have to translate it, just add your name and language code and configure the plural rules. Plural rules describe how many different forms a message can have depending on the numerical value that goes with it. E.g. for English, there are usually two options: *1 sentence found*, but *2 sentences found*. This is how a corresponding rule looks like::

    "Plural-Forms: nplurals=2; plural=(n != 1)\n"

  It says that there are generally two distinct number forms available (numbered *0* and *1*). If the choice of the form depends on an integer number ``n``, the number of the form to be chosen is calculated with the expression ``n != 1``, which yields ``0`` for ``n = 1`` and ``1`` for other values of ``n``.

  A more complicated example can be found in Russian, where three different forms are used with numerals::

    "Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)\n"

- ``main.txt`` is a file in ``babel`` format that contains translations of most corpus-independent captions and messages. Each translation contains a key, identified by ``msgid``, and a value, ``msgstr``. ``msgid`` is a string that is written in an HTML template, and ``msgstr`` is how it should look like in this language. Here is a simple example::

    #: templates/index.html:22
    msgid "remove_word"
    msgstr "remove&nbsp;word"

  This rule describes an English translation for a label called ``remove_word``. Translations must be quoted and can contain HTML tags and entities. Make sure you do not have quotation marks inside a translation. A comment preceding the rule tells us where exactly this label can be found.

  For messages that have multiple number versions, you have to specify as many ``msgstr[...]`` strings as there are singular/plural form in your interface language. Here is an English example::

    #: templates/search_results/result_docs.html:3
    msgid "word found,"
    msgid_plural "words found,"
    msgstr[0] "word found,"
    msgstr[1] "words found,"

Corpus-specific captions
~~~~~~~~~~~~~~~~~~~~~~~~

All the rest are tab-delimited files with two columns: key on the left and value on the right. They contain corpus-specific data, i.e. values that are likely to be different in different corpora. These files are pre-populated in the existing translations. Nevertheless, you will probably have to adjust them before you launch your corpus anyway.

- ``corpus-specific.txt`` currently contains one line describing corpus title displayed in the upper left corner.
- ``languages.txt`` contains names of languages/tiers.
- ``word_fields.txt`` contains names of additional word-level fields.
- ``transliterations.txt`` contains names of :doc:`transliterations </transliteration>` you have.
- ``input_methods.txt`` contains names of :doc:`input methods </input_methods>` you have.
- ``metadata_fields.txt`` contains names of your metadata fields.
- ``metadata_values.txt`` contains names of your metadata values. **Important**: as of now, these translations are only used for sentence-level selector fields, i.e. those values that are described in the ``sentence_meta_values`` parameter in :doc:`corpus.json </configuration>`. In all other contexts, the values are displayed as is.
- ``tooltips.txt`` translates tooltips and headers in your gloss and tag selection popups.

When adding contents of these files to the single ``messages.po`` file, prefixes are added to their keys:

- ``langname_`` for language names;
- ``wordfield_`` for additional word-level annotation fields;
- ``translitname_`` for transliteration names;
- ``inputmethod_``: for input method names;
- ``metafield_`` for metadata field names;
- ``metavalue_`` for metadata value names;
- ``tooltip_`` for tooltips and headers.

So a placeholder for a language called ``klingon`` will look like ``{{ _('langname_klingon' )}}`` in the HTML templates.


HTML templates
~~~~~~~~~~~~~~

HTML templates (help page and greeting popup) must be translated as separate files.

Adjusting existing translations for your corpus
-----------------------------------------------

You will probably have many corpus-specific messages, e.g. tooltips in tag selection popups or language names. You have to add them to the tab-delimited files in ``/search/web_app/translations/`` (see above). Unless you want to change some default interface messages such as "Search sentences" or "Show statistics", you will not have to edit ``main.txt`` and ``header.txt`` in language folders.

A more user-friendly way of configuring translations for your corpus is running the ``config`` page (see :doc:`configuration </configuration>`). When you save the configuration, language folders with all necessary keys will be generatedin ``/USER_CONFIG/translations``. Edit them and replace files in ``/search/web_app/translations/`` with them in your :doc:`fork </forks>`.
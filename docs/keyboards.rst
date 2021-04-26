Virtual keyboards
=================

If some of your languages use non-ASCII characters, it might be a good idea to add a virtual keyboard. The user can enable or disable virtual keyboards for main language-dependent text boxes by clikcing on a keyboard sign. The virtual keyboard is based on the `KioskBoard <https://furcan.github.io/KioskBoard/>`_ plugin.

This is how you can add virtual keyboards for all or some of your languages:

1. Add ``keyboards`` dictionary in :doc:`corpus.json </configuration>`. Write language/tier names as keys and keyboard IDs as values.

2. For each keyboard ID, you have to create a keyboard file in ``/search/web_app/static/keyboards``. The files describe keyboards in JSON format. The file should be named ``keyboard-%KEYBOARD_ID%.json``. The file should contain a list where each element describes one row of keys. Each row contains a list of strings, one per key. Here is a small example:

.. code-block:: javascript
  :linenos:

  [
    [
      "w",
      "e",
      "ə",
      "ɤ"
    ],
    [
      "a",
      "s",
      "š",
      "šʼ"
    ],
    [
      "z",
      "ž",
      "žʼ"
    ]
  ]

3. If you have different :doc:`input methods </input_methods>` for some language, you can create different keyboards for different input methods. Name your keyboard files ``keyboard-%KEYBOARD_ID%__%INPUT_METHOD_NAME%.json``. If Tsakorpus finds no file for a specific input method, it will look for a generic keyboard for that language.

The keyboards are assigned independently to text boxes in each query word, depending on the language/tier selected by the user for that particular word. The keyboard for the full-text search text box is assigned based on the language/tier of the first query word.
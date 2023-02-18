Input methods
=============

Input methods are functions that transform textual input before the search. They can be used e.g. if you want to be able to enter search terms in a transliteration or add ASCII shortcuts for fancy characters. If you have multiple input methods, you have to list their names in the ``input_methods`` list in :doc:`corpus.json </configuration>`. The user can choose input method in the settings dialog. Although the list of input methods is defined globally for the whole corpus, each input method can work differently depending on the language/tier chosen.

Adding input methods works much in the same way as :doc:`adding transliterations </transliteration>` does. For each language and each input method, you have to create a function in a python file located in ``/search/transliterators`` (feel free to add new files) with two arguments, ``field`` and ``text``. ``field`` argument contains the name of the search field the text comes from (e.g. ``wf`` for word form or ``lex`` for lemma), and ``text`` is the text to be transformed. The function must return a transformed string. It is allowed to turn the string into a regex in the process by adding special characters such as ``.*``. According to the convention used in Tsakorpus, such functions should be called ``%LANGUAGE_NAME%_input_%INPUT_METHOD%(field, text)``, but that's up to you.

This a simple example from ``/search/transliterators/tajik.py``:


.. code-block:: python
  :linenos:

  def tajik_input_normal(field, text):
      """
      Prepare a string from one of the query fields for subsequent
      processing: replace common shortcuts with valid Tajik characters.
      """
      if field not in ('wf', 'lex'):
          return text
      text = text.replace('и1', 'ӣ')
      text = text.replace('х1', 'ҳ')
      text = text.replace('к1', 'қ')
      text = text.replace('ч1', 'ҷ')
      text = text.replace('у1', 'ӯ')
      text = text.replace('г1', 'ғ')
      return text

When you are done, you have to import your functions in ``/search/web_app/transliteration.py`` and add function calls to ``input_method_%INPUT_METHOD%`` under a condition like ``if lang == '%LANGUAGE_NAME%'``. If there is no existing function for your input method name, you can add one.

If no function is found for some input method or some language, nothing bad will happen: the search will just be performed as is.

Also see :doc:`transliteration`.
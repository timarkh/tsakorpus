Transliterations
================

You can set up automatic transliterations in your corpus. Transliterations are functions that transform the text of words and sentences before they are sent to the user. If you use transliterations, you have to list their names in the ``transliterations`` list in :doc:`corpus.json </configuration>`. The user can choose a transliteration in the settings dialog. Although the list of transliterations is defined globally for the whole corpus, each transliteration can work differently depending on the language/tier chosen.

For each language and each transliteration, you have to create a function in a python file located in ``/search/transliterators`` (feel free to add new files) with one argument, which contains the text to be transliterated. The function must return a transliterated string. According to the convention used in Tsakorpus, such functions should be called ``%LANGUAGE_NAME%_translit_%TRANSLITERATION%(text)``, but that's up to you.

This a simple example from ``/search/transliterators/armenian.py``:

.. code-block:: python
  :linenos:

  dictArm2Lat = {'խ': 'x', 'ու': 'u', 'ւ': 'w',
                 'է': 'ē', 'ր': 'r', 'տ': 't',
                 'ե': 'e', 'ը': 'ə', 'ի': 'i',
                 'ո': 'o', 'պ': 'p', 'չ': 'č‘',
                 'ջ': 'ĵ', 'ա': 'a', 'ս': 's',
                 'դ': 'd', 'ֆ': 'f', 'ք': 'k‘',
                 'հ': 'h', 'ճ': 'č', 'կ': 'k',
                 'լ': 'l', 'թ': 't‘', 'փ': 'p‘',
                 'զ': 'z', 'ց': 'c‘', 'գ': 'g',
                 'վ': 'v', 'բ': 'b', 'ն': 'n',
                 'մ': 'm', 'շ': 'š', 'ղ': 'ġ',
                 'ծ': 'c', 'ձ': 'j', 'յ': 'y',
                 'օ': 'ō', 'ռ': 'ŕ', 'ժ': 'ž',
                 'և': 'ew', ':': '.'}
  
  def armenian_translit_meillet(text):
      text = text.replace('ու', 'u')
      text = text.replace('ու'.upper(), 'U')
      text = text.replace('Ու'.upper(), 'U')
      textTrans = ''
      for c in text:
          try:
              c = dictArm2Lat[c]
          except KeyError:
              try:
                  c = dictArm2Lat[c.lower()].upper()
              except KeyError:
                  pass
          textTrans += c
      return textTrans

When you are done, you have to import your functions in ``/search/web_app/transliteration.py`` and add function calls to ``trans_%TRANSLITERATION%_baseline`` under a condition like ``if lang == '%LANGUAGE_NAME%'``. If there is no existing function for your transliteration name, you can add one. The transliterations will be applied to the sentence text ("baseline") and certain fields, such as word form and lemma. Applying transliterations to some other fields, such as glosses, might require slightly different rules. Separate functions for such cases will probably be added in one of the later releases.

If no function is found for some transliteration or some language, nothing bad will happen.

Also see :doc:`input_methods`.
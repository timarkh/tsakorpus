Spans and styles
================

Spans
-----

It is possible to annotate spans, possibly including multiple words, in the :doc:`Tsakorpus JSON format </data_model>`. Span annotations cannot be searched directly, but they can be displayed in search results. Tsakorpus uses `CSS styles and HTML classes`_ for that. You can assign each span a certain style that will determine what it looks like.

.. _CSS styles and HTML classes: https://www.w3schools.com/html/html_classes.asp

This is what a span looks like in a JSON file:

.. code-block:: javascript
  :linenos:

  {
    "off_start": ...,
    "off_end": ...,
    "span_class": "...",
    "tooltip_text": "..."  // optional
  }

The ``off_start`` and ``off_end`` parameters are integers that define the offset of the relevant segment in the ``text`` value in characters.

``span_class`` is a string that defines the style. When displayed in a search hit, the relevant segment is put inside a ``<span>`` element with the ``class`` attribute set to ``style_%SPAN_CLASS%``. For example, if ``span_class`` equals ``i``, the actual span tag will look like ``<span class="style_i">``.

The classes should be defined in ``/search/web_app/static/css/span_styles.css``. There are several predefined classes:

- ``style_i`` (italics);
- ``style_b`` (bold);
- ``style_sup`` (superscript);
- ``style_sub`` (subscript);
- ``style_txt_hX`` for ``X`` = ``1``, ``2`` and ``3`` (headers).

If the ``tooltip_text`` parameter is set, it can be used to display a tooltip. However, this is not done automatically. Instead, its value is written to the ``data-tooltip-text`` attribute of the ``<span>`` element. You can make it visible by referencing it in the corresponding style definition. Here is an example of how this can be done:

.. code-block:: css
  :linenos:

  .style_%SPAN_CLASS%:hover:before {
    content: attr(data-tooltip-text);
    background-color: #000;
    color: #fff;
    top: 1em;
    padding: 10px;
    border-radius: 4px;
    position: absolute;
    white-space: nowrap;
  }

Languages/tiers
---------------

It is possible to display text in different languages/tiers differently. Each sentence is assigned an HTML class ``sent_lang_%LANGUAGE_NAME%``. If you want to define a style for some language, you can do it in ``/search/web_app/static/css/span_styles.css``. Two styles are defined by default:

- ``sent_lang_ref`` (for "reference tiers"): smaller font, gray color.
- ``sent_lang_english_note`` (for comments in English): light gray color.

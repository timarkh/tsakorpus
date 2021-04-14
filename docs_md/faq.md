## Very brief FAQ about the tsakorpus platform
Short answers for long questions (See ``faq_ru.md`` for Russian version.)

### From the developer's perspective

* Q: **Is the platform open source and free to use for any purpose?**
  A: Yes.

* Q: **Will it work if my corpus has <= 1 million words?**
  A: Yes.

* Q: **Will it work if my corpus has 10-20 million words?**
  A: Yes, but you'll want to use more memory (say, 3-4 Gb), otherwise complex multi-word queries may be slow.

* Q: **Will it work if my corpus has 100 million words?**
  A: The largest corpus people have tried tsakorpus on so far has about 250 million words, which seems to work ok with at least 8 Gb memory. But multi-word queries will be slow anyway.

* Q: **Can I have audio/video alignment so that the users can listen/watch whatever they find?**
  A: Yes.

* Q: **Can I have aligned translations in multiple languages?**
  A: Yes.

* Q: **Can I have arbitrary document-level metadata?**
  A: Yes.

* Q: **Can I have sentence-level metadata, such as age or sex of the speaker in dialogues?**
  A: Yes.

* Q: **Can I have words with multiple ambiguous analyses?**
  A: Yes.

* Q: **Can I have analyses/metadata attached to arbitrary spans of text longer than one word?**
  A: Not yet.

* Q: **Can I have syntactic annotation (dependencies/constituents)?**
  A: No.

* Q: **Is it possible to offer web interface in several languages?**
  A: Yes; English and Russian are in the box, but you may add other languages.

* Q: **Can I have several transliteration options?**
  A: Yes.

* Q: **Can I install the platform on my personal computer and use it alone?**
  A: Yes.

* Q: **I do not have access to a server. Can I use this platform to put my corpus online?**
  A: No, you have to find a server.

* Q: **What are the system requirements for the server?**
  A: Linux with apache configured for use with Python 3.x. The more memory, the better, but I guess at least 2 Gb should be available. Required disk space depends on corpus size and annotation, very roughly, you need 0.5-1 Gb per million tokens.

* Q: **I am a linguist who is not afraid of the word "SSH" and had some programming experience in the university, but has mostly forgotten it all by now. Will it be too difficult for me to use the platform without any help?**
  A: If your corpus is in one of the formats for which tsakorpus has source convertors, than probably it will be okay. You will have to fill in some lengthy configuration files and put it all to the server, but no actual programming is required.

* Q: **I am a linguist who has never dealt with servers or any kind of programming. How can I use the platform for my corpus?**
  A: The easiest way is to hire a computational linguistics / computer science student. An average undergraduate student in their pre-final or final year should be able to do this.



### From the user's perspective
* Q: **Can I search with regular expressions?**
  A: Yes.
  
* Q: **Can I simultaneously set several annotation fields when searching for a word, e.g. the lemma, grammatical tags and the translation?**
  A: Yes.

* Q: **When I find a sentence, can I look at its context (several neighboring sentences)?**
  A: Yes.

* Q: **When I find a sentence, can I read the whole text?**
  A: No.

* Q: **Can I download the results I found?**
  A: Yes, but only the pages you've looked at, not all the results at once.

* Q: **Can I choose a subcorpus, i.e. a subset of corpus texts, based on metadata, and search only inside it?**
  A: Yes.

* Q: **If the corpus has morphological annotation, can I search for e.g. nouns that are in the genitive or in the dative, but not in plural?**
  A: Yes.
  
* Q: **If the corpus is glossed, can I search for words that have, say, an iterative marker that starts with "a" followed immediately by any passive marker?**
  A: Yes.

* Q: **Can I search for expressions / multiple words inside one sentence?**
  A: Yes.

* Q: **Can I search for multiple words within any segments larger than sentence (like paragraph or text)?**
  A: No.

* Q: **Can I search for sentences that __do not__ contain some words?**
  A: Yes.

* Q: **Can I get frequency lists of words that conform to my query?**
  A: Yes.

* Q: **Can I get frequency lists of words that conform to a query and occupy a certain slot in a construction?**
  A: Yes, but if your construction is too complex and the corpus is large, you will only see the list based on a random sample of corpus sentences.

* Q: **Can I get lists of n-grams or learn something about their pointwise mutual information etc.?**
  A: No.

* Q: **Can I get charts comparing the usage of certain words/expressions between genres, years etc.?**
  A: Yes.

* Q: **Can I save a query for later use and get the results in the same order?**
  A: Yes, if the corpus is not re-indexed until then.
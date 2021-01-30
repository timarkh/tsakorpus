## Developer's checklist
What you should manually check in the web interface before releasing a new version.

### Basic sentence search
* Search for a single word works.

* Search for a word with asterisks works.

* Search for a word with regular expressions works.

* Search for a Boolean expression like ``N,(nom|gen),~pl`` in Grammar field works.

* Clicking on ``expand context`` expands context.

* Clicking on page numbers results in opening new hit pages.

* Hovering your mouse over a highlighted word shows you the analyses; the correct analysis is highlighted.

### Advanced sentence search

* Clicking on ``+`` and ``-`` adds/removes word search boxes.

* Searching for two words without distance constraints works.

* Searching for two words with a constraint (e.g. ``1 to 3 words from Word 1``) works.

* Number of sentences is displayed correctly.

* Combining positive and negative search terms works (e.g. find all words that start with an **a** in sentences with no verbs).

### Word search

* Simple word and lemma search works.

* Clicking on downward arrow in the hit table downloads more hits. New hits do not coincide with the existing ones. Check for both word and lemma search.

* Searching for two words with a distance constraint gets you a list of words found in the first slot.

### Subcorpus

* If you type something in the first subcorpus selection tab, the list and charts in the other tabs change.

* If you search in a subcorpus, you see a message above the hits, and the numbers are lower than when you search in the entire corpus.

* Word search in a subcorpus works, and the numbers are lower than when you search in the entire corpus.

* With subcropus selected, clicking on downward arrow in the hit table downloads more hits. New hits do not coincide with the existing ones. Check for both word and lemma search.

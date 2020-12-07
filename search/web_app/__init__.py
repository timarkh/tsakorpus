from flask import Flask
import os
import random

SETTINGS_DIR = '../conf'
MAX_PAGE_SIZE = 100     # maximum number of sentences per page
sessionData = {}        # session key -> dictionary with the data for current session
random.seed()

# Read settings before we import anything else. Many modules
# imported after this point reference the settings object,
# therefore it has to exist at import time.
from .corpus_settings import CorpusSettings
settings = CorpusSettings()
settings.load_settings(os.path.join(SETTINGS_DIR, 'corpus.json'),
                       os.path.join(SETTINGS_DIR, 'categories.json'))

# Continue with module imports. Beware that there are other
# circular import issues, so the order of imported modules
# should not change.
from search_engine.client import SearchClient
from .response_processors import SentenceViewer
localizations = {}
sc = SearchClient(SETTINGS_DIR, mode='test')
sentView = SentenceViewer(settings, sc)
sc.qp.rp = sentView
sc.qp.wr.rp = sentView

settings.corpus_size = sc.get_n_words()  # size of the corpus in words
for lang in settings.languages:
    # number of word types for each frequency rank
    settings.word_freq_by_rank.append(sentView.extract_cumulative_freq_by_rank(sc.get_word_freq_by_rank(lang)))
    # number of lemmata for each frequency rank
    settings.lemma_freq_by_rank.append(sentView.extract_cumulative_freq_by_rank(sc.get_lemma_freq_by_rank(lang)))


app = Flask(__name__)
app.secret_key = 'kkj6hd)^js7#dFQ'

app.config.update(dict(
    LANGUAGES=settings.interface_languages,
    BABEL_DEFAULT_LOCALE=settings.default_locale
))

from .views import *

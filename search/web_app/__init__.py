from flask import Flask
from elasticsearch.exceptions import ConnectionError, NotFoundError
import sys
import subprocess
import os
import re
import random


def load_csv_translations(fname, pfx=''):
    """
    Load translations from a tab-delimited file. Add prefix
    to the keys. Return a dictionary.
    """
    translations = {}
    with open(fname, 'r', encoding='utf-8-sig') as fIn:
        for line in fIn:
            line = line.strip('\r\n ')
            if len(line) <= 2 or line.count('\t') != 1:
                continue
            key, value = line.split('\t')
            key = pfx + key
            translations[key] = value
    return translations


def generate_po(lang):
    """
    Generate a messages.po translation file for pybabel based on
    the contents of translations/lang
    """
    srcDir = os.path.join('web_app/translations', lang)
    targetDir = os.path.join('web_app/translations_pybabel', lang, 'LC_MESSAGES')
    if not os.path.exists(srcDir):
        return
    if not os.path.exists(targetDir):
        os.makedirs(targetDir)
    with open(os.path.join(targetDir, 'messages.po'), 'w', encoding='utf-8') as fOut:
        try:
            with open(os.path.join(srcDir, 'header.txt'), 'r', encoding='utf-8') as fIn:
                fOut.write(fIn.read() + '\n')
            with open(os.path.join(srcDir, 'main.txt'), 'r', encoding='utf-8') as fIn:
                fOut.write(fIn.read() + '\n\n')
            dictMessages = {}
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'corpus-specific.txt'), ''))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'input_methods.txt'),
                                                      'inputmethod_'))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'languages.txt'),
                                                      'langname_'))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'metadata_fields.txt'),
                                                      'metafield_'))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'metadata_values.txt'),
                                                      'metavalue_'))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'tooltips.txt'),
                                                      'tooltip_'))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'transliterations.txt'),
                                                      'translitname_'))
            dictMessages.update(load_csv_translations(os.path.join(srcDir, 'word_fields.txt'),
                                                      'wordfield_'))
            for k in sorted(dictMessages):
                fOut.write('msgid "' + k.replace('\n', '\\n').replace('"', '&quot;').replace('%', '%%') + '"\n')
                fOut.write('msgstr "' + dictMessages[k].replace('\n', '\\n').replace('"', '&quot;').replace('%', '%%') + '"\n\n')
        except:
            print('Something went wrong when generating interface translations.')


def compile_translations():
    """
    Compile flask_babel translations.
    """
    pythonPath = ''
    for p in sys.path:
        if re.search('Python3[^/\\\\]*[/\\\\]?$', p) is not None:
            pythonPath = p
            break
    if len(pythonPath) <= 0:
        pyBabelPath = 'pybabel'
    else:
        pyBabelPath = os.path.join(pythonPath, 'Scripts', 'pybabel')
    try:
        subprocess.run([pyBabelPath, 'compile',  '-d', 'translations_pybabel'], cwd='web_app', check=True)
    except:
        print('Could not compile translations with ' + pyBabelPath + ' .')
    else:
        print('Interface translations compiled.')


SETTINGS_DIR = '../conf'
MAX_PAGE_SIZE = 100     # maximum number of sentences per page
MIN_TOTAL_FREQ_WORD_QUERY = 2000  # minimal number of processed tokens after which
                                  # the word/lemma search involving multiple words
                                  # may be stopped due to timeout
sessionData = {}        # session key -> dictionary with the data for current session
random.seed()

rxIndexAtEnd = re.compile('_[0-9]+$')


# Read settings before we import anything else. Many modules
# imported after this point reference the settings object,
# therefore it has to exist at import time.
from .corpus_settings import CorpusSettings
settings = CorpusSettings()
settings.load_settings(os.path.join(SETTINGS_DIR, 'corpus.json'),
                       os.path.join(SETTINGS_DIR, 'categories.json'))

# Prepare pybabel translations
for lang in settings.interface_languages:
    generate_po(lang)
compile_translations()

# Continue with module imports. Beware that there are other
# circular import issues, so the order of imported modules
# should not change.
from search_engine.client import SearchClient
from .response_processors import SentenceViewer
localizations = {}
sc = SearchClient(SETTINGS_DIR, settings)
sentView = SentenceViewer(settings, sc)
sc.qp.rp = sentView
sc.qp.wr.rp = sentView

try:
    settings.corpus_size = sc.get_n_words()  # size of the corpus in words
    for lang in settings.languages:
        # number of word types for each frequency rank
        settings.word_freq_by_rank.append(sentView.extract_cumulative_freq_by_rank(sc.get_word_freq_by_rank(lang)))
        # number of lemmata for each frequency rank
        settings.lemma_freq_by_rank.append(sentView.extract_cumulative_freq_by_rank(sc.get_lemma_freq_by_rank(lang)))
    settings.ready_for_work = True
except (ConnectionError, NotFoundError):
    # Elasticsearch is down
    settings.corpus_size = 0
    for lang in settings.languages:
        settings.word_freq_by_rank.append({})
        settings.lemma_freq_by_rank.append({})
sc.qp.maxFreqRank = max(max(len(settings.word_freq_by_rank[i]), len(settings.lemma_freq_by_rank[i]))
                        for i in range(len(settings.languages))) + 1


app = Flask(__name__)
app.secret_key = 'kkj6hd)^js7#dFQ'

app.config.update(dict(
    LANGUAGES=settings.interface_languages,
    BABEL_DEFAULT_LOCALE=settings.default_locale,
    BABEL_TRANSLATION_DIRECTORIES='translations_pybabel',
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='tsakorpus_session'
))

if settings.session_cookie_domain is not None and len(settings.session_cookie_domain) > 0:
    app.config['SESSION_COOKIE_DOMAIN'] = settings.session_cookie_domain

from .views import *

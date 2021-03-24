import os
import sys
import json
import re
from json_doc_reader import JSONDocReader

sys.path.insert(0, '../search/web_app')
from corpus_settings import CorpusSettings
from response_processors import SentenceViewer

class JSON2HTML:
    """
    Contains methods for translating annotated JSON files into
    HTML files, provided that the corpus settings allow full-text view.
    """
    SETTINGS_DIR = '../conf'

    def __init__(self):
        self.settings = CorpusSettings()
        self.settings.load_settings(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                               os.path.join(self.SETTINGS_DIR, 'categories.json'))
        self.sentView = SentenceViewer(self.settings, None)
        self.iterSent = None
        if self.settings.input_format in ['json', 'json-gzip']:
            self.iterSent = JSONDocReader(format=self.settings.input_format)
        self.lastSentNum = 0  # for the IDs in the HTML

    def process_file(self, fnameIn, fnameOut):
        """
        Read one JSON file (fnameIn). Generate an HTML representation for it
        and store it in fnameOut.
        """
        htmlByLangView = {'lang0': ''}
        nLangView = 0
        for s, bLast in self.iterSent.get_sentences(fnameIn):
            if 'lang' in s:
                langID = s['lang']
            else:
                langID = 0
                s['lang'] = langID
            s['doc_id'] = '0'
            s = {
                '_source': s
            }
            self.lastSentNum += 1
            lang = self.settings.languages[langID]
            sentProcessed = self.sentView.process_sentence(s,
                                                           numSent=self.lastSentNum,
                                                           lang=lang,
                                                           langView='lang' + str(nLangView))
            if len(sentProcessed['languages']['lang' + str(nLangView)]['text']) > 0:
                htmlByLangView['lang' + str(nLangView)] += sentProcessed['languages']['lang' + str(nLangView)]['text'] + ' \n'
            if bLast or ('last' in s['_source'] and s['_source']['last']):
                nLangView += 1
                htmlByLangView['lang' + str(nLangView)] = ''

        htmlByLangView = {langView: htmlByLangView[langView]
                          for langView in htmlByLangView
                          if len(htmlByLangView[langView].strip()) > 0}
        colClass = 8
        if len(htmlByLangView) > 1:
            colClass = 10 // len(htmlByLangView)
        for langView in htmlByLangView:
            htmlByLangView[langView] = htmlByLangView[langView].replace('<span class="newline"></span>', '<br>')
            htmlByLangView[langView] = re.sub('^[\n ]*<br> *', '', htmlByLangView[langView], flags=re.DOTALL)
            htmlByLangView[langView] = re.sub('\n\n+', '\n', htmlByLangView[langView], flags=re.DOTALL)
            htmlByLangView[langView] = re.sub('  +', ' ', htmlByLangView[langView])
            htmlByLangView[langView] = '<div class="col-sm-' + str(colClass) \
                                       + '"><span class="sent_lang sent_lang_' + langView \
                                       + '" id="res1_' + langView + '">' \
                                       + htmlByLangView[langView] + '</span></div>'

        with open(fnameOut, 'w', encoding='utf-8') as fOut:
            fOut.write('\n'.join(htmlByLangView[langView]
                                 for langView in sorted(htmlByLangView)))


if __name__ == '__main__':
    j2h = JSON2HTML()
    j2h.process_file('../corpus/beserman_eaf/2014.08.09_LV_cow-1.json', '1.html')

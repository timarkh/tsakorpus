import os
import sys
import json
import re
from werkzeug.utils import secure_filename
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

    def __init__(self, settings):
        self.settings = CorpusSettings()
        self.settings.load_settings(os.path.join(self.SETTINGS_DIR, 'corpus.json'),
                               os.path.join(self.SETTINGS_DIR, 'categories.json'))
        self.sentView = SentenceViewer(self.settings, None, fullText=True)
        self.iterSent = None
        if self.settings.input_format in ['json', 'json-gzip']:
            self.iterSent = JSONDocReader(format=self.settings.input_format,
                                          settings=settings)
        self.lastSentNum = 0  # for the IDs in the HTML

    def finalize_html_sentence(self, sent):
        """
        Add span tags etc. to a sentence in HTML and clean it.
        """
        # sent = sent.replace('<span class="newline"></span>', '<br>')
        sent = re.sub('^[\n ]*<br> *', '', sent, flags=re.DOTALL)
        sent = re.sub('\n\n+', '\n', sent, flags=re.DOTALL)
        sent = re.sub('  +', ' ', sent)
        return sent

    def finalize_html_paragraph(self, sentByTier, colClass, paraNum):
        """
        Make one HTML paragraph with parallel sentences.
        """
        remainingCol = max(2, 12 - colClass * len(sentByTier))
        paragraph = '<div class="d-none d-sm-block col-md-' + str(remainingCol // 2) + '"></div>'
        paragraph += '<div class="paragraph_num">'
        if paraNum % 10 == 0:
            paragraph += '<div>' + str(paraNum) + '</div>'
        paragraph += '</div>\n'
        for iTier in range(len(sentByTier)):
            sent = sentByTier[iTier]
            sent = re.sub('(?<=class="word)(.*)',
                          lambda m: m.group(1).replace('<span class="newline"></span>', '<br>'),
                          sent,
                          flags=re.DOTALL)
            sent = '<div class="col-sm-' + str(colClass) \
                   + '"><span class="sent_lang sent_lang_lang' + str(iTier) \
                   + '" id="res1_lang' + str(iTier) + '">' \
                   + sent + '</span></div>\n'
            paragraph += sent
        return paragraph

    def process_file(self, fnameIn, fnameOut):
        """
        Read one JSON file (fnameIn). Generate an HTML representation for it
        and store it in fnameOut.
        """
        htmlByTier = [[]]
        nTier = 0
        paraIDsByTier = [set()]
        for s, bLast in self.iterSent.get_sentences(fnameIn):
            if 'lang' in s:
                langID = s['lang']
            else:
                langID = 0
                s['lang'] = langID
            curParaIDs = []
            if 'para_alignment' in s:
                for para in s['para_alignment']:
                    if 'para_id' in para:
                        curParaIDs.append(para['para_id'])
            s['doc_id'] = '0'
            s = {
                '_source': s
            }
            self.lastSentNum += 1
            lang = self.settings.languages[langID]
            sentProcessed = self.sentView.process_sentence(s,
                                                           numSent=self.lastSentNum,
                                                           lang=lang,
                                                           langView='lang' + str(nTier))
            if len(sentProcessed['languages']['lang' + str(nTier)]['text']) > 0:
                curSentData = {
                    'html': sentProcessed['languages']['lang' + str(nTier)]['text'] + ' \n',
                    'para_ids': curParaIDs
                }
                htmlByTier[nTier].append(curSentData)
                paraIDsByTier[nTier] |= set(curSentData['para_ids'])
            if bLast or ('last' in s['_source'] and s['_source']['last']):
                nTier += 1
                htmlByTier.append([])
                paraIDsByTier.append(set())
        
        # Remove empty tiers
        for iTier in range(len(htmlByTier) - 1, -1, -1):
            if (len(htmlByTier[iTier]) <= 0
                    or all(len(sent['html'].strip()) <= 0
                           for sent in htmlByTier[iTier])):
                del htmlByTier[iTier]
                del paraIDsByTier[iTier]
        nTiers = len(htmlByTier)

        colClass = 8
        if nTiers > 1:
            colClass = max(2, 10 // nTiers)

        curPointers = [0] * nTiers
        usedParaIDsByTier = [set() for _ in range(nTiers)]
        dataFinal = {
            'rows': [],
            'meta': self.iterSent.get_metadata(fnameIn)
        }

        fname = ''
        if 'fulltext_id' in dataFinal['meta']:
            fname = secure_filename(dataFinal['meta']['fulltext_id'])
        if len(fname) <= 0:
            return
        if nTiers <= 0 or len(curPointers) <= 0 or len (htmlByTier) <= 0:
            print('No HTML generated for ' + fnameIn)
            return

        while curPointers[0] < len(htmlByTier[0]):
            curParagraph = [''] * nTiers
            curParagraph[0] = self.finalize_html_sentence(htmlByTier[0][curPointers[0]]['html'])
            curParaIDs = set(htmlByTier[0][curPointers[0]]['para_ids'])
            for iTier in range(1, nTiers):
                remainingParaIDs = (paraIDsByTier[iTier] & curParaIDs) - usedParaIDsByTier[iTier]
                while len(remainingParaIDs) > 0 and curPointers[iTier] < len(htmlByTier[iTier]):
                    curParagraph[iTier] += self.finalize_html_sentence(htmlByTier[iTier][curPointers[iTier]]['html'])
                    usedParaIDsByTier[iTier] |= set(htmlByTier[iTier][curPointers[iTier]]['para_ids'])
                    remainingParaIDs -= set(htmlByTier[iTier][curPointers[iTier]]['para_ids'])
                    curPointers[iTier] += 1
            dataFinal['rows'].append(self.finalize_html_paragraph(curParagraph, colClass, curPointers[0] + 1))
            curPointers[0] += 1

        if not os.path.exists(os.path.dirname(fnameOut)):
            os.makedirs(os.path.dirname(fnameOut))
        with open(fnameOut, 'w', encoding='utf-8') as fOut:
            json.dump(dataFinal, fOut, indent=1, ensure_ascii=False)


if __name__ == '__main__':
    j2h = JSON2HTML()
    j2h.process_file('../corpus/beserman_multimedia/json_disamb/2014/LV_AS-2014.08.09-TA_MU-cow_1.json',
                     '../search/corpus_html/beserman_multimedia/1.json')
    j2h.process_file('../corpus/beserman_multimedia/json_disamb/2018/AL_RA-2018.05.01-MU_NF-quest_repeat.json',
                     '../search/corpus_html/beserman_multimedia/2.json')

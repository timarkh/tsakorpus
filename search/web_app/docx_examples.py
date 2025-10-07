import re
import math
from docx import Document
from docx.shared import Inches, Cm, Pt
from docx.oxml.shared import OxmlElement, qn
from docx.enum.style import WD_STYLE_TYPE


class DocxExampleProcessor:
    """
    Contains methods for rendering search hit(s) as table(s) in a Word document.
    """
    rxStemGloss = re.compile('[ ,;:()]+')
    rxPuncR = re.compile('^[.,?!:;)"/\\-\\]”]+$')
    rxPuncL = re.compile('^(?:[/?!. ]*\\[|[#*(\\[“]+)$')
    rxLetters = re.compile('\\w')
    rxGlossesNonGlosses = re.compile('([^$]+)')

    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def set_cell_margins(table, left=0, right=0):
        tc = table._element
        tblPr = tc.tblPr
        tblCellMar = OxmlElement('w:tblCellMar')
        kwargs = {"left": left, "right": right}
        for m in ["left", "right"]:
            node = OxmlElement("w:{}".format(m))
            node.set(qn('w:w'), str(kwargs.get(m)))
            node.set(qn('w:type'), 'dxa')
            tblCellMar.append(node)

        tblPr.append(tblCellMar)

    @staticmethod
    def p_no_margins(wordDoc, p, style='Normal'):
        p.style = wordDoc.styles[style]
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Cm(0)
        p.paragraph_format.space_after = Cm(0)

    def smallcaps_glosses(self, p, text, langProps):
        if 'gloss_regex' not in langProps:
            p.text = text.strip()
            return
        text = langProps['gloss_regex'].sub(lambda m: '$' + m.group(1) + '$', text)
        for run in self.rxGlossesNonGlosses.findall(text):
            if langProps['gloss_regex'].search(run) is not None:
                p.add_run(run.lower()).font.small_caps = True
            else:
                p.add_run(run)
        else:
            p.text = text

    def process_example(self, wordDoc, langProps, s, translit, translations, additionalInfo,
                        tabular=True, gloss=True, tags=False):
        """
        Add one example to the docx file object.
        """
        if 'words' not in s:
            return
        text = s['text']
        words = []
        glosses = []
        hangingPuncL = ''
        for iToken in range(len(s['words'])):
            w = s['words'][iToken]
            wf = w['wf']
            if w['wtype'] != 'word':
                if self.rxLetters.search(wf) is not None:
                    words.append(hangingPuncL + wf)
                    glosses.append('')
                    hangingPuncL = ''
                else:
                    if w['off_start'] > 0 and text[w['off_start'] - 1] not in (' ', '\t', '\n'):
                        if len(hangingPuncL) > 0 or len(words) <= 0:
                            hangingPuncL += wf
                        else:
                            words[-1] += wf
                    else:
                        hangingPuncL += wf
                continue

            wf = hangingPuncL + wf

            gloss = 'STEM'
            curGlosses = set()
            curParts = set()
            curTrans = set()
            if 'ana' in w:
                for ana in w['ana']:
                    if 'parts' in ana:
                        curParts.add(ana['parts'])
                    if 'gloss' in ana:
                        curGlosses.add(ana['gloss'])
                    if 'trans_en' in ana:
                        curTrans.add(ana['trans_en'])
                    elif 'trans_ru' in ana:
                        curTrans.add(ana['trans_ru'])
            curGlosses = [g for g in sorted(curGlosses, key=lambda x: (x.count('-'), len(x), x))
                          if len(g) > 0]
            curParts = [p for p in sorted(curParts, key=lambda x: (x.count('-'), max(len(p) for p in x.split('-')), x))
                        if len(p) > 0]
            curTrans = [t for t in sorted(curTrans, key=lambda x: (-len(x), x))]
            if len(curGlosses) > 0 and len(curParts) > 0:
                wf = hangingPuncL + curParts[0]
                gloss = curGlosses[0]
                if len(curTrans) > 0:
                    gloss = gloss.replace('STEM', self.rxStemGloss.sub('.', curTrans[0]))
            hangingPuncL = ''

            if ('enclitics_regex' in langProps
                    and langProps['enclitics_regex'].search(wf) is not None
                    and len(words) > 0
                    and len(words[-1]) > 0
                    and self.rxPuncR.search(words[-1][-1]) is None):
                words[-1] += '=' + wf
                glosses[-1] += '=' + gloss
            else:
                words.append(wf)
                glosses.append(gloss)

        nCharsWords = len(''.join(w.strip() for w in words))
        # If a gloss is overly long, something is probably wrong with it,
        # so the user will want to shorten it anyway. Therefore, it would
        # be ok for it to be wrapped
        nCharsGloss = len(''.join(re.sub('^.{30,}',
                                         'X' * 30, g.strip()) for g in glosses))
        nRows = math.ceil(max(nCharsWords // (450 / self.settings.docx_example_font_size),
                              nCharsGloss // (600 / self.settings.docx_gloss_font_size)) + 1)
        nCols = 1 + math.ceil(len(words) / nRows)
        nRows *= 2

        table = wordDoc.add_table(rows=nRows + len(translations) + len(additionalInfo), cols=nCols)
        p = table.cell(0, 0).paragraphs[0]
        p.text = '(xx)'
        DocxExampleProcessor.p_no_margins(wordDoc, p)
        for iRow in range(nRows):
            p = table.cell(iRow, 0).paragraphs[0]
            DocxExampleProcessor.p_no_margins(wordDoc, p)
            # p = table.cell(iRow + 2, 0).paragraphs[0]
            # DocxExampleProcessor.p_no_margins(wordDoc, p)
        for iCell in range(len(words)):
            if iCell >= len(glosses):
                break
            words[iCell] = translit(words[iCell])
            iDoubleRow = iCell // (nCols - 1)
            iCol = iCell - iDoubleRow * (nCols - 1) + 1
            if iCell >= 1:
                for iMergedRow in range(len(translations) + len(additionalInfo)):
                    table.cell(nRows + iMergedRow, 1).merge(table.cell(nRows + iMergedRow, iCol))
            p = table.cell(iDoubleRow * 2, iCol).paragraphs[0]
            p.add_run(words[iCell].strip()).italic = True
            DocxExampleProcessor.p_no_margins(wordDoc, p)
            p = table.cell(iDoubleRow * 2 + 1, iCol).paragraphs[0]
            p.style = wordDoc.styles['Gloss']
            DocxExampleProcessor.p_no_margins(wordDoc, p, 'Gloss')
            if re.search('^(?:[ /*?!.,()_«»-]*|\\[S[0-9]+\\]:?)$', words[iCell].strip()) is not None:
                continue
            self.smallcaps_glosses(p, glosses[iCell].strip(), langProps)
        for iTrans in range(len(translations)):
            p = table.cell(nRows + iTrans, 1).paragraphs[0]
            p.text = translations[iTrans]
            DocxExampleProcessor.p_no_margins(wordDoc, p)
        for iAddInfo in range(len(additionalInfo)):
            p = table.cell(nRows + iAddInfo, 1).paragraphs[0]
            p.text = additionalInfo[iAddInfo]
            DocxExampleProcessor.p_no_margins(wordDoc, p)
        # self.set_cell_margins(table, 0, 0)
        table.autofit = True

    def get_docx(self, lang, sentences, tabular=True, gloss=True, tags=False,
                 translations=None, additionalInfo=None, translit=None):
        """
        Create a docx with the sentences, either as tables or as paragraphs.
        """
        if lang not in self.settings.lang_props:
            return None
        if translations is None:
            translations = []
        for i in range(len(translations)):
            if 'text' in translations[i]:
                translations[i] = translations[i]['text']
            else:
                translations[i] = ''
            translations[i] = translations[i].strip().replace('\n', ' ')
            if not translations[i].startswith('‘'):
                translations[i] = '‘' + translations[i]
            if not translations[i].endswith('’'):
                translations[i] += '’'
        if additionalInfo is None:
            additionalInfo = []
        for i in range(len(additionalInfo)):
            if 'text' in additionalInfo[i]:
                additionalInfo[i] = additionalInfo[i]['text']
            else:
                additionalInfo[i] = ''
        if translit is None:
            translit = lambda x: x
        langProps = self.settings.lang_props[lang]

        wordDoc = Document()
        exampleStyle = wordDoc.styles.add_style('LanguageExample', WD_STYLE_TYPE.PARAGRAPH)
        glossStyle = wordDoc.styles.add_style('Gloss', WD_STYLE_TYPE.PARAGRAPH)
        normalStyle = wordDoc.styles['Normal']
        normalStyle.font.name = self.settings.docx_normal_font_face
        normalStyle.font.size = Pt(self.settings.docx_normal_font_size)
        normalStyle.paragraph_format.space_after = Cm(0)
        exampleStyle.font.name = self.settings.docx_example_font_face
        exampleStyle.font.size = Pt(self.settings.docx_example_font_size)
        glossStyle.font.name = self.settings.docx_gloss_font_face
        glossStyle.font.size = Pt(self.settings.docx_gloss_font_size)
        for s in sentences:
            self.process_example(wordDoc, langProps, s, translit, translations, additionalInfo, tabular, gloss, tags)
            p = wordDoc.add_paragraph('')
            DocxExampleProcessor.p_no_margins(wordDoc, p)
        return wordDoc


if __name__ == '__main__':
    pass


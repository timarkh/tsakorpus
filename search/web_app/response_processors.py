import json
import html
import copy
import math
import re
import jinja2
from flask import render_template
try:
    from .transliteration import *
except ImportError:
    # This happens when response_processors.py is imported
    # from outside this package, but we do not need the
    # transliterations in that case
    pass


class SentenceViewer:
    """
    Contains methods for turning the JSON response of ES into
    viewable html.
    """

    rxWordNo = re.compile('^w[0-9]+_([0-9]+)$')
    rxHitWordNo = re.compile('(?<=^w)[0-9]+')
    rxTextSpans = re.compile('</?span.*?>|[^<>]+', flags=re.DOTALL)
    rxTabs = re.compile('^\t*$')
    rxKW = re.compile('_kw$')
    invisibleAnaFields = {'gloss_index'}

    def __init__(self, settings, search_client, fullText=False):
        """
        Set fullText = True if this instance is to be used for
        generating full-text HTML files. This will switch off
        source alignment spans and maybe some other things.
        """
        self.settings = settings
        self.name = self.settings.corpus_name
        self.sentence_props = ['text']
        self.dictionary_categories = {lang: set() for lang in self.settings.languages}
        for lang in self.settings.lang_props:
            if 'dictionary_categories' in self.settings.lang_props[lang]:
                self.dictionary_categories[lang] = set(self.settings.lang_props[lang]['dictionary_categories'])
        self.authorMeta = 'author'
        if self.settings.author_metafield is not None and len(self.settings.author_metafield) > 0:
            self.authorMeta = self.settings.author_metafield
        self.sc = search_client
        self.w1_labels = set(['w1'] + ['w1_' + str(i) for i in range(self.settings.max_words_in_sentence)])
        self.templates = {}     # Jinja2 template cache for standalone use
        self.fullText = fullText

    def render_jinja_html(self, templateDir, templateFilename, **context):
        """
        Render a flask template without flask context (needed if
        this file is imported from outside the package).
        """
        try:
            template = self.templates[(templateDir, templateFilename)]
        except KeyError:
            template = jinja2.Environment(
                loader=jinja2.FileSystemLoader(templateDir + '/')
            ).get_template(templateFilename)
            self.templates[(templateDir, templateFilename)] = template
        return template.render(context)

    def differing_ana_field(self, ana1, ana2):
        """
        Determine if two analyses with equal number of fields only differ
        in one field, with the possible exception of the gloss field.
        If they do, return the name of the field. If they do not differ
        at all, return empty string. If they have more than one
        differing fields, return None.
        """
        differingField = ''
        for key in ana1:
            if key not in ana2:
                return None
            if key in ('gloss', 'gloss_index'):
                continue
            if ana2[key] != ana1[key]:
                if len(differingField) > 0:
                    return None
                differingField = key
        return differingField

    def join_ana_gloss_variants(self, ana1, ana2):
        """
        Check if the gloss field values in the analyses differ only
        in one gloss. If so, return a string with joined glossing, e.g.
        (STEM-PL-GEN) + (STEM-SG-GEN) would give (STEM-PL/SG-GEN). If not,
        return None.
        """
        if 'gloss' not in ana1 or 'gloss' not in ana2:
            return None
        if ana1['gloss'] == ana2['gloss']:
            return ana1['gloss']
        glossParts1 = ana1['gloss'].split('-')
        glossParts2 = ana2['gloss'].split('-')
        if len(glossParts1) != len(glossParts2):
            return None
        nDifferences = 0
        joinedGloss = ''
        for iGloss in range(len(glossParts1)):
            if iGloss != 0:
                joinedGloss += '-'
            if glossParts1[iGloss] == glossParts2[iGloss]:
                joinedGloss += glossParts1[iGloss]
            else:
                if nDifferences >= 1:
                    return None
                nDifferences += 1
                newGlossPart = list(set(glossParts1[iGloss].split('/') + glossParts2[iGloss].split('/')))
                newGlossPart.sort()
                joinedGloss += '/'.join(newGlossPart)
        return joinedGloss

    def simplify_ana(self, analyses, matchingAnalyses):
        """
        Collate JSON analyses that only have differences in one field,
        e.g. [(N,sg,gen), (N,pl,gen)] -> (N,sg/pl,gen). Analyses that
        match the query (their indices are stored in matchingAnalyses)
        cannot be collated with those that do not.
        Return a list with simplified analyses and the matching analyses
        indices in the new list. The source list is changed in the process.
        """
        nAnalyses = len(analyses)
        simpleAnalyses = []
        simpleMatchingAnalyses = []
        usedAnalyses = []
        for i in range(nAnalyses):
            if i in usedAnalyses:
                continue
            for j in range(i + 1, nAnalyses):
                if j in usedAnalyses:
                    continue
                if i in matchingAnalyses and j not in matchingAnalyses:
                    continue
                if j in matchingAnalyses and i not in matchingAnalyses:
                    continue
                if len(analyses[i]) != len(analyses[j]):
                    continue
                differingField = self.differing_ana_field(analyses[i], analyses[j])
                if (differingField is not None
                        and len(differingField) > 0
                        and differingField.startswith(('gr.', 'trans_'))
                        and type(analyses[i][differingField]) == str
                        and type(analyses[j][differingField]) == str):
                    if 'gloss' in analyses[i] or 'gloss' in analyses[j]:
                        joinedGloss = self.join_ana_gloss_variants(analyses[i], analyses[j])
                        if joinedGloss is None:
                            continue
                        analyses[i]['gloss'] = joinedGloss
                    if differingField.startswith('gr.'):
                        separator = '/'
                    else:
                        separator = ' || '
                    values = list(set(analyses[i][differingField].split(separator) + analyses[j][differingField].split(separator)))
                    values.sort()
                    analyses[i][differingField] = separator.join(values)
                    usedAnalyses.append(j)
            simpleAnalyses.append(analyses[i])
            if i in matchingAnalyses:
                simpleMatchingAnalyses.append(len(simpleAnalyses) - 1)
        if len(simpleAnalyses) < len(analyses):
            # The procedure may require several recursive steps
            simpleAnalyses, simpleMatchingAnalyses = self.simplify_ana(simpleAnalyses, simpleMatchingAnalyses)
        return simpleAnalyses, simpleMatchingAnalyses

    def build_gr_ana_part_text(self, grValues, lang):
        """
        Build a string with gramtags ordered according to the settings
        for the language specified by lang.
        """
        def key_comp(p):
            if 'gr_fields_order' not in self.settings.lang_props[lang]:
                return -1
            if p[0] not in self.settings.lang_props[lang]['gr_fields_order']:
                return len(self.settings.lang_props[lang]['gr_fields_order'])
            return self.settings.lang_props[lang]['gr_fields_order'].index(p[0])

        grAnaPart = ''
        for fv in sorted(grValues, key=key_comp):
            if len(grAnaPart) > 0:
                grAnaPart += ', '
            grAnaPart += fv[1]
        return grAnaPart

    def build_gr_ana_part(self, grValues, lang, gramdic=False):
        """
        Build an HTML div with gramtags ordered according to the settings
        for the language specified by lang.
        gramdic == True iff dictionary values (such as gender) are processed. 
        """
        grAnaPart = self.build_gr_ana_part_text(grValues, lang)
        if not gramdic:
            try:
                return render_template('search_results/grammar_popup.html', grAnaPart=grAnaPart).strip()
            except (AttributeError, RuntimeError):
                return self.render_jinja_html('../search/web_app/templates/search_results',
                                              'grammar_popup.html', grAnaPart=grAnaPart).strip()
        try:
            return render_template('search_results/gramdic_popup.html', grAnaPart=grAnaPart).strip()
        except (AttributeError, RuntimeError):
            return self.render_jinja_html('../search/web_app/templates/search_results',
                                          'gramdic_popup.html', grAnaPart=grAnaPart).strip()

    def build_ana_div(self, ana, lang, translit=None):
        """
        Build the contents of a div with one particular analysis.
        """
        def field_sorting_key(x):
            if x['key'] in self.settings.lang_props[lang]['other_fields_order']:
                return (self.settings.lang_props[lang]['other_fields_order'].index(x['key']),
                        x['key'])
            return (len(self.settings.lang_props[lang]['other_fields_order']),
                    x['key'])

        ana4template = {'lex': '', 'pos': '', 'grdic': '', 'lex_fields': [], 'gr': '', 'other_fields': []}
        if 'lex' in ana:
            ana4template['lex'] = self.transliterate_baseline(ana['lex'], lang=lang, translit=translit)
        if 'gr.pos' in ana:
            ana4template['pos'] = ana['gr.pos']
        grValues = []     # inflectional categories
        grdicValues = []  # dictionary categories such as nominal gender
        for field in sorted(ana):
            if field not in ['lex', 'gr.pos'] and field not in self.invisibleAnaFields:
                value = ana[field]
                if type(value) == list:
                    value = ', '.join(value)
                if field.startswith('gr.'):
                    if lang in self.dictionary_categories and field[3:] in self.dictionary_categories[lang]:
                        grdicValues.append((field[3:], value))
                    else:
                        grValues.append((field[3:], value))
                elif ('exclude_fields' in self.settings.lang_props[lang]
                      and field in self.settings.lang_props[lang]['exclude_fields']):
                    continue
                elif ('lexical_fields' in self.settings.lang_props[lang]
                      and field in self.settings.lang_props[lang]['lexical_fields']):
                    # Lexical fields are displayed between the lemma+pos and the gr lines
                    ana4template['lex_fields'].append({'key': field, 'value': value})
                else:
                    # Other fields are displayed below the gr line
                    ana4template['other_fields'].append({'key': field, 'value': value})
        ana4template['grdic'] = self.build_gr_ana_part(grdicValues, lang, gramdic=True)
        ana4template['gr'] = self.build_gr_ana_part(grValues, lang, gramdic=False)
        if 'other_fields_order' in self.settings.lang_props[lang]:
            ana4template['lex_fields'].sort(key=field_sorting_key)
            ana4template['other_fields'].sort(key=field_sorting_key)
        else:
            # Order analysis fields alphabetically
            ana4template['lex_fields'].sort(key=lambda x: x['key'])
            ana4template['other_fields'].sort(key=lambda x: x['key'])
        try:
            return render_template('search_results/analysis_div.html', ana=ana4template).strip()
        except (AttributeError, RuntimeError):
            return self.render_jinja_html('../search/web_app/templates/search_results',
                                          'analysis_div.html', ana=ana4template).strip()

    def build_ana_popup(self, word, lang, matchingAnalyses=None, translit=None):
        """
        Build a string for a popup with the word and its analyses. 
        """
        if matchingAnalyses is None:
            matchingAnalyses = []
        data4template = {'wf': '', 'analyses': []}
        if 'wf_display' in word:
            data4template['wf_display'] = self.transliterate_baseline(word['wf_display'], lang=lang, translit=translit)
        elif 'wf' in word:
            data4template['wf'] = html.escape(self.transliterate_baseline(word['wf'], lang=lang, translit=translit))
        if 'ana' in word:
            simplifiedAnas, simpleMatchingAnalyses = self.simplify_ana(word['ana'], matchingAnalyses)
            for iAna in range(len(simplifiedAnas)):
                ana4template = {'match': iAna in simpleMatchingAnalyses,
                                'ana_div': self.build_ana_div(simplifiedAnas[iAna], lang, translit=translit)}
                data4template['analyses'].append(ana4template)
        try:
            return render_template('search_results/analyses_popup.html', data=data4template)
        except (AttributeError, RuntimeError):
            return self.render_jinja_html('../search/web_app/templates/search_results',
                                          'analyses_popup.html', data=data4template)

    def prepare_analyses(self, words, indexes, lang, matchWordOffsets=None, translit=None):
        """
        Generate viewable analyses for the words with given indexes.
        """
        result = ''
        for iStr in indexes:
            mWordNo = self.rxWordNo.search(iStr)
            if mWordNo is None:
                continue
            i = int(mWordNo.group(1))
            if i < 0 or i >= len(words):
                continue
            word = words[i]
            if word['wtype'] != 'word':
                continue
            matchingAnalyses = []
            if matchWordOffsets is not None and iStr in matchWordOffsets:
                matchingAnalyses = [offAna[1] for offAna in matchWordOffsets[iStr]]
            result += self.build_ana_popup(word, lang, matchingAnalyses=matchingAnalyses, translit=translit)
        # result = result.replace('"', "&quot;").replace('<', '&lt;').replace('>', '&gt;')
        return result

    def build_span(self, sentSrc, curWords, curStyles, lang, matchWordOffsets, translit=None):
        """
        Build a string with a starting span for a word in the baseline.
        """
        curClass = ''
        if any(wn.startswith('w') for wn in curWords):
            curClass += ' word '
        if any(wn.startswith('p') for wn in curWords):
            curClass += ' para '
        if not self.fullText and any(wn.startswith('src') for wn in curWords):
            curClass += ' src '
        curClass = curClass.lstrip()

        if 'word' in curClass:
            dataAna = self.prepare_analyses(sentSrc['words'], curWords,
                                            lang, matchWordOffsets,
                                            translit=translit)
        else:
            dataAna = ''
        dataAna = html.escape(dataAna)

        def highlightClass(nWord):
            if nWord in matchWordOffsets:
                return ' wmatch' + ''.join(' wmatch_' + str(n)
                                           for n in set(anaOff[0]
                                                        for anaOff in matchWordOffsets[nWord]))
            return ''

        spanStart = '<span class="' + curClass + \
                    ' '.join(wn + highlightClass(wn)
                             for wn in curWords) + '" data-ana="' + dataAna + '">'
        for styleTag in curStyles:
            spanStart += styleTag
        return spanStart

    def add_highlighted_offsets(self, offStarts, offEnds, text):
        """
        Find highlighted fragments in source text of the sentence
        and store their offsets in the respective lists.
        """
        indexSubtr = 0  # <em>s that appeared due to highlighting should be subtracted
        for i in range(len(text) - 4):
            if text[i] != '<':
                continue
            if text[i:i+4] == '<em>':
                try:
                    offStarts[i - indexSubtr].add('smatch')
                except KeyError:
                    offStarts[i - indexSubtr] = {'smatch'}
                indexSubtr += 4
            elif text[i:i+5] == '</em>':
                try:
                    offEnds[i - indexSubtr].add('smatch')
                except KeyError:
                    offEnds[i - indexSubtr] = {'smatch'}
                indexSubtr += 5

    def process_sentence_header(self, sentSource, format='html'):
        """
        Retrieve the metadata of the document the sentence
        belongs to. Return a string with this data that can
        serve as a header for the context on the output page
        (format=='html') or as a set of tab-delimited metadata
        fields that accompany the sentence in a CSV file (format='csv').
        In the latter case, the first element should contain
        a short description string, including things such as
        authour or title.
        """
        docID = sentSource['doc_id']
        meta = self.sc.get_doc_by_id(docID)
        if (meta is None
                or 'hits' not in meta
                or 'hits' not in meta['hits']
                or len(meta['hits']['hits']) <= 0
                or '_source' not in meta['hits']['hits'][0]):
            if format == 'csv':
                return ['']
            else:
                return render_template('search_results/sentence_header.html',
                                       fulltext_view_enabled=False)
        meta = meta['hits']['hits'][0]['_source']
        for k in meta:
            if type(meta[k]) == list:
                meta[k] = '; '.join(meta[k])
            elif type(meta[k]) == int:
                meta[k] = str(meta[k])
        dateDisplay = ''
        if 'year' in meta:
            dateDisplay = str(meta['year'])
        elif 'year_from' in meta and 'year_to' in meta:
            dateDisplay = str(meta['year_from'])
            if meta['year_to'] != meta['year_from']:
                dateDisplay += '–' + str(meta['year_to'])
        metaHtml = render_template('modals/metadata_table.html',
                                   data={'meta': meta},
                                   viewable_meta=self.settings.viewable_meta)
        metaHtml = html.escape(metaHtml)

        if format == 'csv':
            result = ['']
            if 'title' in meta:
                result[0] += '"' + meta['title'] + '" '
            else:
                result[0] += '"???" '
            if self.authorMeta in meta and len(meta[self.authorMeta]) > 0:
                result[0] += '(' + meta[self.authorMeta] + ') '
            if 'issue' in meta and len(meta['issue']) > 0:
                result[0] += meta['issue'] + ' '
            if len(dateDisplay) > 0:
                result[0] += '[' + dateDisplay + ']'
            meta = {self.rxKW.sub('', k): v
                    for k, v in meta.items()
                    if self.rxKW.sub('', k) in self.settings.viewable_meta
                    and k not in ['filename', 'filename_kw']}
            sortedMetaFields = []
            for f in self.settings.viewable_meta:
                # Sort in the same order as listed in conf/corpus.json
                if f not in ['filename', 'filename_kw'] and f not in self.settings.sentence_meta:
                    sortedMetaFields.append(f)
            for f in sortedMetaFields:
                v = ''
                if f in meta:
                    v = str(meta[f]).replace('\t', ' ')
                newField = '[' + f + ': ' + v + ']'
                if newField not in result:
                    result.append(newField)
        else:
            result = render_template('search_results/sentence_header.html',
                                     fulltext_view_enabled=self.settings.fulltext_view_enabled,
                                     author_meta=self.authorMeta,
                                     date_display=dateDisplay,
                                     metaHtml=metaHtml,
                                     meta=meta)
        return result

    def get_word_offsets(self, sSource, numSent, matchOffsets=None):
        """
        Find at which offsets which word start and end. If macthOffsets
        is not None, find only offsets of the matching words.
        Return two dicts, one with start offsets and the other with end offsets.
        The keys are offsets and the values are the string IDs of the words.
        """
        offStarts, offEnds = {}, {}
        for iWord in range(len(sSource['words'])):
            try:
                if sSource['words'][iWord]['wtype'] != 'word':
                    continue
                offStart, offEnd = sSource['words'][iWord]['off_start'], sSource['words'][iWord]['off_end']
            except KeyError:
                continue
            wn = 'w' + str(numSent) + '_' + str(iWord)
            if matchOffsets is not None and wn not in matchOffsets:
                continue
            try:
                offStarts[offStart].add(wn)
            except KeyError:
                offStarts[offStart] = {wn}
            try:
                offEnds[offEnd].add(wn)
            except KeyError:
                offEnds[offEnd] = {wn}
        return offStarts, offEnds

    def get_para_offsets(self, sSource):
        """
        Find at which offsets which parallel fragments start and end.
        Return two dicts, one with start offsets and the other with end offsets.
        The keys are offsets and the values are the string IDs of the fragments.
        """
        offStarts, offEnds = {}, {}
        if 'para_alignment' not in sSource or 'doc_id' not in sSource:
            return offStarts, offEnds
        docID = sSource['doc_id']
        for iPA in range(len(sSource['para_alignment'])):
            pa = sSource['para_alignment'][iPA]
            try:
                offStart, offEnd = pa['off_start'], pa['off_end']
            except KeyError:
                continue
            pID = 'p' + str(pa['para_id']) + str(docID)
            try:
                offStarts[offStart].add(pID)
            except KeyError:
                offStarts[offStart] = {pID}
            try:
                offEnds[offEnd].add(pID)
            except KeyError:
                offEnds[offEnd] = {pID}
        return offStarts, offEnds

    def get_src_offsets(self, sSource):
        """
        Find at which offsets which sound/video-alignment fragments start and end.
        Return three dicts, one with start offsets, the other with end offsets,
        and the third with the descriptions of the fragments.
        The keys in the first two are offsets and the values are the string IDs 
        of the fragments.
        """
        offStarts, offEnds, fragmentInfo = {}, {}, {}
        if self.fullText or 'src_alignment' not in sSource or 'doc_id' not in sSource:
            return offStarts, offEnds, fragmentInfo
        docID = sSource['doc_id']
        for iSA in range(len(sSource['src_alignment'])):
            sa = sSource['src_alignment'][iSA]
            try:
                offStart, offEnd = sa['off_start_sent'], sa['off_end_sent']
            except KeyError:
                continue
            srcID = 'src' + sa['src_id'] + str(docID)
            fragmentInfo[srcID] = {'start': sa['off_start_src'],
                                   'end': sa['off_end_src'],
                                   'src': sa['src'],
                                   'mtype': sa['mtype']}
            try:
                offStarts[offStart].add(srcID)
            except KeyError:
                offStarts[offStart] = {srcID}
            try:
                offEnds[offEnd].add(srcID)
            except KeyError:
                offEnds[offEnd] = {srcID}
        return offStarts, offEnds, fragmentInfo

    def get_style_offsets(self, sSource):
        """
        Find spans of text that should be displayed in a non-default style,
        e.g. in italics or in superscript.
        Return two dicts, one with start offsets and the other with end offsets.
        The keys are offsets. The values are sets with HTML tags that contain
        the class and other attributes, such as tooltip text.
        """
        offStarts, offEnds = {}, {}
        if 'style_spans' not in sSource:
            return offStarts, offEnds
        for iSpan in range(len(sSource['style_spans'])):
            try:
                offStart, offEnd = sSource['style_spans'][iSpan]['off_start'], sSource['style_spans'][iSpan]['off_end']
            except KeyError:
                continue
            styleClass = 'style_' + sSource['style_spans'][iSpan]['span_class']
            tooltipText = ''
            if 'tooltip_text' in sSource['style_spans'][iSpan]:
                tooltipText = sSource['style_spans'][iSpan]['tooltip_text']
            styleSpan = '<span class="style_span ' + styleClass \
                        + '" data-tooltip-text="' + tooltipText + '">'
            try:
                offStarts[offStart].add(styleSpan)
            except KeyError:
                offStarts[offStart] = {styleSpan}
            try:
                offEnds[offEnd].add(styleSpan)
            except KeyError:
                offEnds[offEnd] = {styleSpan}
        return offStarts, offEnds

    def relativize_src_alignment(self, expandedContext, srcFiles):
        """
        If the sentences in the expanded context are aligned with the
        neighboring media file fragments rather than with the same fragment,
        re-align them with the same one and recalculate offsets.
        """
        srcFiles = set(srcFiles)
        if len(srcFiles) > 1 or len(srcFiles) <= 0 or 'src_alignment' not in expandedContext:
            return
        srcFile = list(srcFiles)[0]
        rxSrcFragmentName = re.compile('^(.*?)-(\\d+)-(\\d+)\\.[^.]*$')
        mSrc = rxSrcFragmentName.search(srcFile)
        if mSrc is None:
            return
        for k in expandedContext['src_alignment']:
            alignment = expandedContext['src_alignment'][k]
            if srcFile == alignment['src']:
                continue
            mExp = rxSrcFragmentName.search(alignment['src'])
            if mExp is None or mExp.group(1) != mSrc.group(1):
                continue
            offsetSrc = (int(mSrc.group(3)) * self.settings.media_length
                         + int(mSrc.group(2)) * self.settings.media_length / 3)
            offsetExp = (int(mExp.group(3)) * self.settings.media_length
                         + int(mExp.group(2)) * self.settings.media_length / 3)
            difference = offsetExp - offsetSrc
            alignment['src'] = srcFile
            alignment['start'] = str(float(alignment['start']) + difference)
            alignment['end'] = str(float(alignment['end']) + difference)

    def process_sentence_csv(self, sJSON, lang='', translit=None):
        """
        Process one sentence taken from response['hits']['hits'].
        Return a CSV string for this sentence.
        """
        sDict = self.process_sentence(sJSON, numSent=0, getHeader=False, format='csv',
                                      lang=lang, translit=translit)
        if ('languages' not in sDict
                or lang not in sDict['languages']
                or 'text' not in sDict['languages'][lang]
                or len(sDict['languages'][lang]['text']) <= 0):
            return ''
        return sDict['languages'][lang]['text']

    def transliterate_baseline(self, text, lang, translit=None):
        if translit is None or lang not in self.settings.languages:
            return text
        spans = self.rxTextSpans.findall(text)
        translitFuncName = 'trans_' + translit + '_baseline'
        localNames = globals()
        if translitFuncName not in localNames:
            return text
        translit_func = localNames[translitFuncName]
        textTranslit = ''
        for span in spans:
            if span.startswith('<'):
                textTranslit += span
            else:
                textTranslit += translit_func(span, lang)
        return textTranslit

    def view_sentence_meta(self, sSource, format):
        """
        If there is a metadata dictionary in the sentence, transform it
        to an HTML span or text for CSV.
        """
        if 'meta' not in sSource:
            return ''
        meta2show = {self.rxKW.sub('', k): sSource['meta'][k]
                     for k in sSource['meta'] if k not in ['sent_analyses', 'sent_analyses_kw']}
        if len(meta2show) <= 0:
            return ''
        metaSpan = '<span class="sentence_meta">'
        if format == 'csv':
            metaSpan = ''
        sortedMetaFields = []
        for f in self.settings.sentence_meta:
            if f not in ['filename', 'filename_kw', 'sent_analyses', 'sent_analyses_kw']:
                sortedMetaFields.append(f)
        for f in sortedMetaFields:
            v = ''
            if f in meta2show:
                v = str(meta2show[f]).replace('\t', ' ')
            if format == 'csv':
                metaSpan += '[' + f + ': ' + v + ']\t'
            elif len(v) > 0:
                metaSpan += html.escape(f + ': ' + v)
                metaSpan += '<br>'
        if format == 'csv':
            metaSpan = metaSpan.strip(' ')
        else:
            if metaSpan.endswith('<br>'):
                metaSpan = metaSpan[:-4]
            metaSpan += '</span>'
        return metaSpan

    def process_sentence(self, s, numSent=1, getHeader=False, lang='', langView='', translit=None, format='html'):
        """
        Process one sentence taken from response['hits']['hits'].
        If getHeader is True, retrieve the metadata from the database.
        Return dictionary {'header': document header HTML,
                           {'languages': {'<language_name>': {'text': sentence HTML[,
                               'img': related image name,
                               'rtl': True if right-to-left script is used]}}}}.
        """
        if len(langView) <= 0 and len(lang) > 0:
            langView = lang
        if '_source' not in s:
            return {'languages': {langView: {'text': '', 'highlighted_text': ''}}}
        matchWordOffsets = self.retrieve_highlighted_words(s, numSent)
        sSource = s['_source']
        if 'text' not in sSource or len(sSource['text']) <= 0:
            return {'languages': {langView: {'text': '', 'highlighted_text': ''}}}

        header = {}
        if getHeader:
            header = self.process_sentence_header(sSource, format)
        if 'highlight' in s and 'text' in s['highlight']:
            highlightedText = s['highlight']['text']
            if type(highlightedText) == list:
                if len(highlightedText) > 0:
                    highlightedText = highlightedText[0]
                else:
                    highlightedText = sSource['text']
        else:
            highlightedText = sSource['text']
        if 'words' not in sSource:
            return {'languages': {langView: {'text': highlightedText,
                                             'highlighted_text': highlightedText}}}
        chars = list(sSource['text'])
        if format == 'csv':
            offParaStarts, offParaEnds = {}, {}
            offSrcStarts, offSrcEnds, fragmentInfo = {}, {}, {}
            offStyleStarts, offStyleEnds = {}, {}
            offStarts, offEnds = self.get_word_offsets(sSource, numSent,
                                                       matchOffsets=matchWordOffsets)
        else:
            offParaStarts, offParaEnds = self.get_para_offsets(sSource)
            offSrcStarts, offSrcEnds, fragmentInfo = self.get_src_offsets(sSource)
            offStyleStarts, offStyleEnds = self.get_style_offsets(sSource)
            offStarts, offEnds = self.get_word_offsets(sSource, numSent)
            self.add_highlighted_offsets(offStarts, offEnds, highlightedText)

        curWords = set()
        curStyles = set()
        for i in range(len(chars)):
            if chars[i] == '\n':
                if format == 'csv':
                    chars[i] = '\\n '
                elif (i == 0 or i == len(chars) - 1
                        or all(chars[j] == '\n'
                               for j in range(i+1, len(chars)))):
                    chars[i] = '<span class="newline"></span>'
                else:
                    chars[i] = '<br>'
            elif chars[i] == '<' and format != 'csv':
                chars[i] = '&lt;'
            elif chars[i] == '>' and format != 'csv':
                chars[i] = '&gt;'

            # Add style tags (italics, superscript, etc.)
            styleSpanEndAddition = ''
            if len(curStyles) > 0 and i in offStyleEnds:
                styleSpanEndAddition = '</span>' * len(offStyleEnds[i])
                curStyles -= offStyleEnds[i]
            if (i not in offStarts and i not in offEnds
                    and i not in offParaStarts and i not in offParaEnds
                    and i not in offSrcStarts and i not in offSrcEnds):
                if i in offStyleStarts:
                    for styleSpan in offStyleStarts[i]:
                        if styleSpan not in curStyles:
                            curStyles.add(styleSpan)
                            chars[i] = styleSpan + chars[i]
                chars[i] = styleSpanEndAddition + chars[i]
                continue

            # Add word and alignment tags
            addition = ''
            if len(curWords) > 0:
                if format == 'csv':
                    addition = '}}'
                else:
                    addition = '</span>'
                    if len(curStyles) > 0:
                        addition += '</span>' * len(curStyles)
                if i in offEnds:
                    curWords -= offEnds[i]
                if i in offStyleEnds:
                    curWords -= offStyleEnds[i]
                if i in offParaEnds:
                    curWords -= offParaEnds[i]
                if i in offSrcEnds:
                    curWords -= offSrcEnds[i]
            if i in offStyleStarts:
                for styleSpan in offStyleStarts[i]:
                    if styleSpan not in curStyles:
                        curStyles.add(styleSpan)
            newWord = False
            if i in offStarts:
                curWords |= offStarts[i]
                newWord = True
            if i in offParaStarts:
                curWords |= offParaStarts[i]
                newWord = True
            if i in offSrcStarts:
                curWords |= offSrcStarts[i]
                newWord = True
            if len(curWords) > 0 and (len(addition) > 0 or newWord):
                if format == 'csv':
                    addition = '{{'
                else:
                    addition += self.build_span(sSource, curWords, curStyles, lang, matchWordOffsets, translit=translit)
            chars[i] = styleSpanEndAddition + addition + chars[i]
        if len(curWords) > 0:
            if format == 'csv':
                chars[-1] += '}}'
            else:
                chars[-1] += '</span>'
        chars[-1] += '</span>' * len(curStyles)
        relationsSatisfied = True
        if 'toggled_on' in s and not s['toggled_on']:
            relationsSatisfied = False
        text = self.view_sentence_meta(sSource, format) +\
               self.transliterate_baseline(''.join(chars), lang=lang, translit=translit)
        langViewContents = {'text': text, 'highlighted_text': highlightedText}
        if self.settings.images and 'img' in sSource['meta']:
            langViewContents['img'] = sSource['meta']['img']
        if langView in self.settings.rtl_languages:
            langViewContents['rtl'] = True
        return {'header': header, 'languages': {langView: langViewContents},
                'toggled_on': relationsSatisfied,
                'src_alignment': fragmentInfo}

    def get_glossed_sentence(self, s, getHeader=True, lang='', glossOnly=False, translit=None):
        """
        Process one sentence taken from response['hits']['hits'].
        If getHeader is True, retrieve the metadata from the database.
        Return tab-delimited text version of the sentence that could be inserted
        either as a simple text example or as a glossed example in a
        linguistic paper.
        """
        def key_comp(p):
            if 'gr_fields_order' not in self.settings.lang_props[lang]:
                return -1
            if p[0] not in self.settings.lang_props[lang]['gr_fields_order']:
                return len(self.settings.lang_props[lang]['gr_fields_order'])
            return self.settings.lang_props[lang]['gr_fields_order'].index(p[0])

        def get_ana_gramm(ana):
            grAnaPart = ''
            grValues = [(k[3:], v) for k, v in ana.items() if k.startswith('gr.')]
            for fv in sorted(grValues, key=key_comp):
                if len(grAnaPart) > 0:
                    grAnaPart += ', '
                if type(fv[1]) == str:
                    grAnaPart += fv[1]
                else:
                    grAnaPart += ', '.join(grTag for grTag in sorted(fv[1]))
            return grAnaPart

        if 'text' not in s or len(s['text']) <= 0:
            return {''}

        header = ''
        if getHeader:
            header = ' [' + self.process_sentence_header(s, 'csv')[0] + ']'
        if 'words' not in s:
            return {s['text'] + header}
        text = self.transliterate_baseline(s['text'].strip(' \t\n').replace('\n', '\\n '),
                                           lang=lang, translit=translit) + header + '\n'
        tokens = ''
        parts = ''
        gloss = ''
        gramm = ''
        lemmata = ''
        wordsStarted = False
        for iWord in range(len(s['words'])):
            w = s['words'][iWord]
            if wordsStarted and w['wtype'] == 'word':
                tokens += '\t'
                parts += '\t'
                gloss += '\t'
                gramm += '\t'
                lemmata += '\t'
            tokens += w['wf']
            if w['wtype'] == 'word':
                wordsStarted = True
                analyses = []
                if 'ana' in w:
                    analyses = self.simplify_ana(w['ana'], [])[0]
                setParts = set(str(ana['parts']) for ana in analyses
                               if 'parts' in ana and type(ana['parts']) in (str, list))
                setGloss = set(str(ana['gloss']) for ana in analyses
                               if 'gloss' in ana and type(ana['gloss']) in (str, list))
                setLemmata = set(str(ana['lex']) for ana in analyses
                                 if 'lex' in ana and type(ana['lex']) in (str, list))
                if len(setParts) > 1:
                    parts += ' || '.join(str(ana['parts']) for ana in analyses
                                         if 'parts' in ana and type(ana['parts']) in (str, list))
                elif len(setParts) == 1:
                    parts += setParts.pop()
                else:
                    parts += w['wf']
                if len(setGloss) != 1:
                    gloss += ' || '.join(str(ana['gloss']) for ana in analyses
                                         if 'gloss' in ana and type(ana['gloss']) in (str, list))
                else:
                    gloss += setGloss.pop()
                gramm += ' || '.join(get_ana_gramm(ana) for ana in analyses)
                if len(setLemmata) != 1:
                    lemmata += ' || '.join(str(ana['lex']) for ana in analyses
                                           if 'lex' in ana and type(ana['lex']) in (str, list))
                else:
                    lemmata += setLemmata.pop()
        if self.rxTabs.search(parts) is not None:
            parts = ''
        if self.rxTabs.search(gloss) is not None:
            gloss = ''
        if self.rxTabs.search(gramm) is not None:
            gramm = ''
        if self.rxTabs.search(lemmata) is not None:
            lemmata = ''
        if not glossOnly:
            if len(parts) > 0:
                return text + parts + '\n' + gloss + '\n' + lemmata + '\n' + gramm + '\n'
            return text + tokens + '\n' + parts + '\n' + gloss + '\n' + lemmata + '\n' + gramm + '\n'
        # glossOnly == True means that we don't need anything other than the glossed example
        return parts.replace('\t', ' ') + '\t' + gloss.replace('\t', ' ')

    def count_word_subcorpus_stats(self, w, docIDs):
        """
        Return statistics about the given word in the subcorpus
        specified by the list of document IDs.
        This function is currently unused and will probably be deleted.
        """
        query = {'bool':
                 {'must':
                  [{'term': {'w_id': w['_id']}},
                   {'terms': {'d_id': docIDs}}]
                  }
                 }
        aggFreq = {'agg_freq': {'stats': {'field': 'freq'}}}
        esQuery = {'query': query, 'aggs': aggFreq, 'size': 1}
        response = self.sc.get_word_freqs(esQuery)
        nSents, rank = '', ''   # for now
        if 'hits' not in response or 'total' not in response['hits']:
            return '?', '?', '?', '?'
        nDocs = str(response['hits']['total']['value'])
        if 'aggregations' in response and 'agg_freq' in response['aggregations']:
            freq = str(int(response['aggregations']['agg_freq']['sum']))
        else:
            freq = '0'
        return freq, rank, nSents, nDocs

    def process_word(self, w, lang, searchType='word', translit=None):
        """
        Process one word taken from response['hits']['hits'].
        """
        if '_source' not in w:
            return ''
        wSource = w['_source']
        freq = str(wSource['freq'])
        rank = str(wSource['rank'])
        nDocs = str(wSource['n_docs'])
        nForms = 1
        otherFields = []
        if searchType == 'word':
            nSents = str(wSource['n_sents'])
            wf = self.transliterate_baseline(wSource['wf'], lang=lang, translit=translit)
            wfDisplay = ''
            if 'wf_display' in wSource:
                wfDisplay = self.transliterate_baseline(wSource['wf_display'], lang=lang, translit=translit)
            lemma = self.get_lemma(wSource)
            gr = self.get_gramm(wSource, lang)
            otherFields = self.get_word_table_fields(wSource)
        else:
            nSents = 0
            if 'n_sents' in wSource:
                nSents = str(wSource['n_sents'])
            wf = wfDisplay = ''
            otherFields = []
            lemma = self.transliterate_baseline(wSource['wf'], lang=lang, translit=translit)
            gr = ''
            nForms = str(wSource['n_forms'])
        if 'w_id' in w:
            wID = w['w_id']  # word or lemma found in the sentences index
        else:
            wID = w['_id']  # word or lemma found in the words index
        if searchType == 'word':
            return render_template('search_results/word_table_row.html',
                                   ana_popup=html.escape(self.build_ana_popup(wSource, lang, translit=translit)),
                                   wf=wf,
                                   wf_display=wfDisplay,
                                   lemma=lemma,
                                   gr=gr,
                                   word_search_display_gr=self.settings.word_search_display_gr,
                                   other_fields=otherFields,
                                   freq=freq,
                                   display_freq_rank=self.settings.display_freq_rank,
                                   rank=rank,
                                   nSents=nSents,
                                   nDocs=nDocs,
                                   wID=wID,
                                   wfSearch=wSource['wf'])
        return render_template('search_results/lemma_table_row.html',
                               ana_popup=html.escape(self.build_ana_popup(wSource, lang, translit=translit)),
                               wf=wf,
                               wf_display=wfDisplay,
                               lemma=lemma,
                               gr=gr,
                               word_search_display_gr=self.settings.word_search_display_gr,
                               other_fields=otherFields,
                               freq=freq,
                               display_freq_rank=self.settings.display_freq_rank,
                               rank=rank,
                               nSents=nSents,
                               nDocs=nDocs,
                               nForms=nForms,
                               lID=wID,
                               wfSearch=wSource['wf'])

    def process_word_buckets(self, w, nDocuments, nForms, freq, lang, searchType='word', translit=None):
        """
        Process one word taken from response['hits']['hits'] for subcorpus or lemma
        queries (where frequency data comes separately from the aggregations).
        """
        if '_source' not in w:
            return ''
        wSource = w['_source']
        if freq is None:
            # This means total frequency was not present in a subaggregation,
            # which in turn means no subcorpus was selected. If this is the case,
            # take the frequency from the word/lemma object itself.
            if 'freq' in wSource:
                freq = wSource['freq']
            else:
                freq = 0
        freq = str(int(round(freq, 0)))
        rank = ''
        nSents = ''
        if 'n_docs' in wSource and nDocuments < 0:
            nDocs = str(wSource['n_docs'])
        else:
            nDocs = str(nDocuments)
        if 'n_sents' in wSource:
            nSents = str(wSource['n_sents'])

        if searchType == 'word':
            return render_template('search_results/word_table_row.html',
                                   ana_popup=html.escape(self.build_ana_popup(wSource, lang, translit=translit)),
                                   wf=self.transliterate_baseline(wSource['wf'], lang=lang, translit=translit),
                                   lemma=self.get_lemma(wSource),
                                   gr=self.get_gramm(wSource, lang),
                                   word_search_display_gr=self.settings.word_search_display_gr,
                                   freq=freq,
                                   display_freq_rank=self.settings.display_freq_rank,
                                   rank=rank,
                                   nSents=nSents,
                                   nDocs=nDocs,
                                   wID=w['_id'],
                                   wfSearch=wSource['wf'])
        return render_template('search_results/lemma_table_row.html',
                               ana_popup=html.escape(self.build_ana_popup(wSource, lang, translit=translit)),
                               lemma=self.transliterate_baseline(wSource['wf'], lang=lang, translit=translit),
                               gr=self.get_gramm(wSource, lang),
                               word_search_display_gr=self.settings.word_search_display_gr,
                               freq=freq,
                               display_freq_rank=self.settings.display_freq_rank,
                               rank=rank,
                               nSents=nSents,
                               nDocs=nDocs,
                               nForms=nForms,
                               lID=w['_id'],
                               wfSearch=wSource['wf'])

    def filter_multi_word_highlight_iter(self, hit, nWords=1, negWords=None, keepOnlyFirst=False):
        """
        Remove those of the highlights that are empty or which do
        not constitute a full set of search terms. If keepOnlyFirst
        is True, remove highlights for all non-first query words.
        negWords is a list of words whose query was negative: they will be
        absent from the highlighting.
        Iterate over filtered inner hits.
        """
        if 'inner_hits' not in hit:
            return
        if negWords is None:
            negWords = []
        if keepOnlyFirst:
            for key, ih in hit['inner_hits'].items():
                if (key in self.w1_labels
                    and all(hit['inner_hits']['w' + str(iWord + 1) + '_' + key[3:]]['hits']['total']['value'] > 0
                            for iWord in range(1, nWords)
                            if iWord + 1 not in negWords)):
                    yield key, ih
        else:
            for key, ih in hit['inner_hits'].items():
                if (all(hit['inner_hits'][self.rxHitWordNo.sub(str(iWord + 1), key, 1)]['hits']['total']['value'] > 0
                        for iWord in range(nWords) if iWord + 1 not in negWords)
                        or '_' not in key):
                    yield key, ih

    def filter_multi_word_highlight(self, hit, nWords=1, negWords=None, keepOnlyFirst=False):
        """
        Non-iterative version of filter_multi_word_highlight_iter which
        replaces hits['inner_hits'] dictionary.
        """
        if 'inner_hits' not in hit or nWords <= 1:
            return
        hit['inner_hits'] = {key: ih for key, ih in self.filter_multi_word_highlight_iter(hit, nWords=nWords,
                                                                                          negWords=negWords,
                                                                                          keepOnlyFirst=keepOnlyFirst)}

    def add_word_from_sentence(self, hitsProcessed, hit, nWords=1, negWords=None, searchType='word'):
        """
        Extract word data from the highlighted w1 in the sentence and
        add it to the dictionary hitsProcessed.
        negWords is a list that contains numbers of words in the query
        whose query was negative.
        searchType can equal 'word' or 'lemma'.
        """
        if '_source' not in hit or 'inner_hits' not in hit:
            return
        langID, lang = self.get_lang_from_hit(hit)
        bRelevantWordExists = False
        # self.filter_multi_word_highlight(hit, nWords=nWords, keepOnlyFirst=True)

        for innerHitKey, innerHit in self.filter_multi_word_highlight_iter(hit, nWords=nWords,
                                                                           keepOnlyFirst=True, negWords=negWords):
            # if innerHitKey not in self.w1_labels:
            #     continue
            bRelevantWordExists = True
            for word in innerHit['hits']['hits']:
                hitsProcessed['total_freq'] += 1
                word['_source']['lang'] = lang
                if searchType == 'word':
                    wID = word['_source']['w_id']
                    wf = word['_source']['wf'].lower()
                elif searchType == 'lemma':
                    wID = word['_source']['l_id']
                    wf = self.get_lemma(word['_source'])
                else:
                    wID = 'w0'
                    wf = ''
                try:
                    hitsProcessed['word_ids'][wID]['n_occurrences'] += 1
                    hitsProcessed['word_ids'][wID]['sents'].add(hit['_id'])
                    hitsProcessed['word_ids'][wID]['docs'].add(hit['_source']['doc_id'])
                    if searchType == 'lemma':
                        hitsProcessed['word_ids'][wID]['forms'].add(word['_source']['w_id'])
                except KeyError:
                    hitsProcessed['n_occurrences'] += 1
                    hitsProcessed['word_ids'][wID] = {
                        'n_occurrences': 1,
                        'sents': {hit['_id']},
                        'docs': {hit['_source']['doc_id']},
                        'wf': wf
                    }
                    if searchType == 'lemma':
                        hitsProcessed['word_ids'][wID]['forms'] = {word['_source']['w_id']}
                    elif searchType == 'word':
                        hitsProcessed['word_ids'][wID]['lemma'] = self.get_lemma(word['_source'])
        if bRelevantWordExists:
            hitsProcessed['n_sentences'] += 1
            hitsProcessed['doc_ids'].add(hit['_source']['doc_id'])

    def get_lemma(self, word):
        """
        Join all lemmata in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        if not self.settings.keep_lemma_order:
            curLemmata = set()
            for ana in word['ana']:
                if 'lex' in ana:
                    if type(ana['lex']) == list:
                        for l in ana['lex']:
                            curLemmata.add(l.lower())
                    else:
                        curLemmata.add(ana['lex'].lower())
            return '/'.join(l for l in sorted(curLemmata))
        curLemmata = []
        for ana in word['ana']:
            if 'lex' in ana:
                if type(ana['lex']) == list:
                    for l in ana['lex']:
                        curLemmata.append(l.lower())
                else:
                    curLemmata.append(ana['lex'].lower())
        return '/'.join(curLemmata)

    def get_gramm(self, word, lang):
        """
        Join all grammar tags strings in the JSON representation of a word with
        an analysis and return them as a string.
        """
        if 'ana' not in word:
            return ''
        if not self.settings.keep_lemma_order:
            curGramm = set()
            simplifiedAnas, simpleMatchingAnalyses = self.simplify_ana(word['ana'], [])
            for ana in simplifiedAnas:
                grTagsList = []
                for field in sorted(ana):
                    value = ana[field]
                    if type(value) == list:
                        value = ', '.join(value)
                    if field.startswith('gr.'):
                        grTagsList.append((field[3:], value))
                grTags = self.build_gr_ana_part_text(grTagsList, lang)
                if len(grTags) > 0:
                    curGramm.add(grTags)
            return ' | '.join(gt for gt in sorted(curGramm))
        curGramm = []
        for ana in word['ana']:
            grTagsList = []
            for field in sorted(ana):
                value = ana[field]
                if type(value) == list:
                    value = ', '.join(value)
                if field.startswith('gr.'):
                    grTagsList.append((field[3:], value))
            grTags = self.build_gr_ana_part_text(grTagsList, lang)
            if len(grTags) > 0:
                curGramm.append(grTags)
        return ' | '.join(curGramm)

    def get_word_table_fields(self, word):
        """
        Return a list with values of fields that have to be displayed
        in a word search hits table, along with wordform and lemma.
        """
        wordTableValues = []
        for field in self.settings.word_table_fields:
            if field in ['lex', 'wf']:
                continue
            curValues = set()
            for k, v in word.items():
                if k == field:
                    if type(v) == list:
                        for value in v:
                            curValues.add(value)
                    elif type(v) == str:
                        curValues.add(v)
            if 'ana' in word:
                for ana in word['ana']:
                    for k, v in ana.items():
                        if k == field:
                            if type(v) == list:
                                for value in v:
                                    curValues.add(value)
                            elif type(v) == str:
                                curValues.add(v)
            wordTableValues.append('/'.join(v for v in sorted(curValues)))
        return wordTableValues

    def process_words_collected_from_sentences(self, hitsProcessedAll,
                                               sortOrder='freq', searchType='word',
                                               startFrom=0, pageSize=10):
        """
        Process all words collected from the sentences with a multi-word query. Modify
        hitsProcessedAll so that hitsProcessedAll['words'] stores data about all
        words found in the sentences index. Leave only those currently requested
        in hitsProcessed and return it.
        searchType can equal 'word' or 'lemma'.
        """
        if len(hitsProcessedAll['words']) <= 0:
            # If this is the first time we process these hits, fill
            # hitsProcessed['words'] based on hitsProcessed['word_ids']
            for wID, freqData in hitsProcessedAll['word_ids'].items():
                word = {'w_id': wID, '_source': {'wf': freqData['wf']}}
                word['_source']['freq'] = freqData['n_occurrences']
                word['_source']['rank'] = ''
                word['_source']['n_sents'] = len(freqData['sents'])
                word['_source']['n_docs'] = len(freqData['docs'])
                if searchType == 'lemma':
                    word['_source']['n_forms'] = len(freqData['forms'])
                elif searchType == 'word':
                    word['_source']['lemma'] = freqData['lemma']
                hitsProcessedAll['words'].append(word)
            del hitsProcessedAll['word_ids']
            self.calculate_ranks(hitsProcessedAll)
            if sortOrder == 'freq':
                hitsProcessedAll['words'].sort(key=lambda w: (-w['_source']['freq'], w['_source']['wf']))
            elif sortOrder == 'wf' or (searchType == 'lemma' and sortOrder in ('wf', 'lemma')):
                hitsProcessedAll['words'].sort(key=lambda w: w['_source']['wf'])
            elif sortOrder == 'lemma' and searchType == 'word':
                hitsProcessedAll['words'].sort(key=lambda w: w['_source']['lemma'])
        processedWords = []
        for i in range(startFrom, min(len(hitsProcessedAll['words']), startFrom + pageSize)):
            word = hitsProcessedAll['words'][i]
            wordSource = self.sc.get_word_by_id(word['w_id'])['hits']['hits'][0]['_source']
            wordSource.update(word['_source'])
            word['_source'] = wordSource
            processedWords.append(self.process_word(word, lang=self.settings.languages[word['_source']['lang']],
                                                    searchType=searchType))
        hitsProcessed = copy.deepcopy(hitsProcessedAll)
        hitsProcessed['words'] = processedWords
        return hitsProcessed

    def calculate_ranks(self, hitsProcessed):
        """
        Calculate frequency ranks of the words collected from sentences based
        on their frequency in the hitsProcessed list.
        For each word, store results in word['_source']['rank']. Return nothing.
        """
        freqsSorted = [w['_source']['freq'] for w in hitsProcessed['words']]
        freqsSorted.sort(reverse=True)
        quantiles = {}
        for q in [0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.25, 0.5]:
            qIndex = math.ceil(q * len(freqsSorted))
            if qIndex >= len(freqsSorted):
                qIndex = len(freqsSorted) - 1
            quantiles[q] = freqsSorted[qIndex]
        for w in hitsProcessed['words']:
            if w['_source']['freq'] > 1:
                if w['_source']['freq'] > quantiles[0.03]:
                    w['_source']['rank'] = '#' + str(freqsSorted.index(w['_source']['freq']) + 1)
                elif w['_source']['freq'] >= quantiles[0.5]:
                    w['_source']['rank'] = '&gt; ' + str(min(math.ceil(q * 100) for q in quantiles
                                                             if w['_source']['freq'] >= quantiles[q])) + '%'

    def process_doc(self, d, exclude=None):
        """
        Process one document taken from response['hits']['hits'].
        """
        if '_source' not in d:
            return ''
        dSource = d['_source']
        dID = d['_id']
        doc = {'fields': [], 'excluded': (exclude is not None and int(dID) in exclude),
               'id': dID}
        dateDisplayed = '-'
        if 'year_from' in dSource:
            dateDisplayed = str(dSource['year_from'])
            if 'year_to' in dSource and dSource['year_to'] != dSource['year_from']:
                dateDisplayed += '&ndash;' + str(dSource['year_to'])
        doc['date_displayed'] = dateDisplayed
        for field in self.sc.qp.docMetaFields:
            if field.endswith('_kw'):
                continue
            if field in dSource:
                doc['fields'].append(dSource[field])
            else:
                doc['fields'].append('')
        return doc

    def retrieve_highlighted_words(self, sentence, numSent, queryWordID=''):
        """
        Explore the inner_hits part of the response to find the
        offsets of the words that matched the word-level query
        and offsets of the respective analyses, if any.
        Search for word offsets recursively, so that the procedure
        does not depend exactly on the response structure.
        Return a dictionary where keys are offsets of highlighted words
        and values are sets of the pairs (ID of the words, ID of its ana)
        that were found by the search query .
        """
        if 'inner_hits' in sentence:
            return self.retrieve_highlighted_words(sentence['inner_hits'],
                                                   numSent,
                                                   queryWordID)

        offsets = {}    # query term ID -> highlights for this query term
        if type(sentence) == list:
            for el in sentence:
                if type(el) not in [dict, list]:
                    continue
                newOffsets = self.retrieve_highlighted_words(el, numSent, queryWordID)
                for newK, newV in newOffsets.items():
                    if newK not in offsets:
                        offsets[newK] = newV
                    else:
                        offsets[newK] |= newV
            return offsets
        elif type(sentence) == dict:
            if 'field' in sentence and sentence['field'] == 'words':
                if 'offset' in sentence:
                    wordOffset = 'w' + str(numSent) + '_' + str(sentence['offset'])
                    if wordOffset not in offsets:
                        offsets[wordOffset] = set()
                    if queryWordID == '':
                        queryWordID = 'w0'
                    anaOffset = -1
                    if ('_nested' in sentence
                            and 'field' in sentence['_nested']
                            and sentence['_nested']['field'] == 'ana'):
                        anaOffset = sentence['_nested']['offset']
                    offsets[wordOffset].add((queryWordID, anaOffset))
                return offsets
            for k, v in sentence.items():
                curQueryWordID = queryWordID
                mQueryWordID = re.search('^(w[0-9]+)(_[0-9]+)?$', k)
                if mQueryWordID is not None:
                    if len(queryWordID) > 0 and queryWordID != mQueryWordID.group(1):
                        continue
                    elif len(queryWordID) <= 0:
                        curQueryWordID = mQueryWordID.group(1)
                if type(v) in [dict, list]:
                    newOffsets = self.retrieve_highlighted_words(v, numSent, curQueryWordID)
                    for newK, newV in newOffsets.items():
                        if newK not in offsets:
                            offsets[newK] = newV
                        else:
                            offsets[newK] |= newV
        return offsets

    def get_lang_from_hit(self, hit):
        """
        Return the ID and the name of the language of the current hit
        taken from ES response.
        """
        if 'lang' in hit['_source']:
            langID = hit['_source']['lang']
        else:
            langID = 0
        lang = self.settings.languages[langID]
        return langID, lang

    def process_sent_json(self, response, translit=None):
        result = {
            'n_occurrences': 0,
            'n_sentences': 0,
            'n_docs': 0,
            'page': 1,
            'message': 'Nothing found.',
            'contexts': [],
            'languages': [],
            'too_many_hits': False
        }
        result['context_header_rtl'] = self.settings.context_header_rtl
        if ('hits' not in response or 'total' not in response['hits']
                or response['hits']['total']['value'] <= 0):
            return result
        result['message'] = ''
        result['n_sentences'] = response['hits']['total']['value']
        # response['hits']['total']['value'] is limited by 10,000 now, so we'll try to take this value from elsewhere
        resultLanguages = set()
        srcAlignmentInfo = {}
        if 'aggregations' in response:
            if 'agg_ndocs' in response['aggregations']:
                result['n_docs'] = int(response['aggregations']['agg_ndocs']['value'])
            if result['n_docs'] > 0 and 'agg_nwords' in response['aggregations']:
                result['n_occurrences'] = int(math.floor(response['aggregations']['agg_nwords']['sum']))
                result['n_sentences'] = int(math.floor(response['aggregations']['agg_nwords']['count']))
        for iHit in range(len(response['hits']['hits'])):
            langID, lang = self.get_lang_from_hit(response['hits']['hits'][iHit])
            langView = lang
            if ('_source' in response['hits']['hits'][iHit]
                    and 'transVar' in response['hits']['hits'][iHit]['_source']):
                langView += '_' + str(response['hits']['hits'][iHit]['_source']['transVar'])
            resultLanguages.add(langView)
            curContext = self.process_sentence(response['hits']['hits'][iHit],
                                               numSent=iHit,
                                               getHeader=True,
                                               lang=lang,
                                               langView=langView,
                                               translit=translit)
            if 'src_alignment' in curContext:
                srcAlignmentInfo.update(curContext['src_alignment'])
            result['contexts'].append(curContext)
        if len(srcAlignmentInfo) > 0:
            result['src_alignment'] = json.dumps(srcAlignmentInfo)
        result['languages'] += [l for l in sorted(resultLanguages)]
        if self.settings.max_hits_retrieve < result['n_sentences']:
            result['too_many_hits'] = True
        return result

    def process_word_json(self, response, searchType='word', subcorpus=False, translit=None):
        """
        Process hits from the words index.
        """
        if searchType == 'lemma' or subcorpus:
            return self.process_word_buckets_json(response, searchType=searchType,
                                                  translit=translit, subcorpus=subcorpus)

        result = {'n_occurrences': 0, 'n_sentences': 0, 'n_docs': 0, 'message': 'Nothing found.'}
        if ('hits' not in response
                or 'total' not in response['hits']
                or response['hits']['total']['value'] <= 0):
            result['total_freq'] = 0
            return result
        result['message'] = ''
        # result['n_occurrences'] = response['hits']['total']['value']
        # response['hits']['total']['value'] is limited by 10,000
        result['n_occurrences'] = response['aggregations']['agg_noccurrences']['value']
        result['n_docs'] = response['aggregations']['agg_ndocs']['value']
        result['total_freq'] = int(round(response['aggregations']['agg_freq']['value']))
        result['words'] = []
        for iHit in range(len(response['hits']['hits'])):
            langID, lang = self.get_lang_from_hit(response['hits']['hits'][iHit])
            result['words'].append(self.process_word(response['hits']['hits'][iHit],
                                                     searchType=searchType,
                                                     lang=lang, translit=translit))
        return result

    def process_word_buckets_json(self, response, searchType='word', translit=None, subcorpus=True):
        """
        Process hits from the words index by retrieving an object for
        each bucket in the agg_group_by_word aggregation. This works for
        lemmata, as well as for any objects searched in a subcorpus.
        """
        result = {'n_occurrences': 0, 'n_sentences': 0, 'n_docs': 0, 'message': 'Nothing found.'}
        if ('aggregations' not in response
                or 'agg_freq' not in response['aggregations']
                or 'value' not in response['aggregations']['agg_freq']
                or 'hits' not in response
                or 'total' not in response['hits']
                or response['hits']['total']['value'] <= 0):
            result['total_freq'] = 0
            return result
        result['message'] = ''
        # result['n_occurrences'] = response['hits']['total']['value']
        result['n_occurrences'] = response['aggregations']['agg_noccurrences']['value']
        result['n_docs'] = response['aggregations']['agg_ndocs']['value']
        result['total_freq'] = response['aggregations']['agg_freq']['value']
        result['words'] = []
        # print(response['aggregations']['agg_group_by_word']['buckets'])
        for iHit in range(len(response['aggregations']['agg_group_by_word']['buckets'])):
            if subcorpus:
                wordID = response['aggregations']['agg_group_by_word']['buckets'][iHit]['key']
                nForms = response['aggregations']['agg_group_by_word']['buckets'][iHit]['subagg_nforms']['value']
                docCount = response['aggregations']['agg_group_by_word']['buckets'][iHit]['doc_count']
            else:
                wordID = response['aggregations']['agg_group_by_word']['buckets'][iHit]['key']['l_id']
                nForms = response['aggregations']['agg_group_by_word']['buckets'][iHit]['doc_count']
                docCount = -1
            try:
                # If this was a subcorpus search, then total frequency of
                # found items comes from word[wtype=word_freq] objects and
                # therefore is stored in a subaggregation.
                # If not, it will be taken from the item itself by process_word_buckets.
                # print(response['aggregations']['agg_group_by_word'])
                wordFreq = response['aggregations']['agg_group_by_word']['buckets'][iHit]['subagg_freq']['value']
            except KeyError:
                wordFreq = None
            hit = self.sc.get_word_by_id(wordID)
            langID, lang = self.get_lang_from_hit(hit['hits']['hits'][0])
            result['words'].append(self.process_word_buckets(hit['hits']['hits'][0],
                                                             nDocuments=docCount,
                                                             nForms=nForms,
                                                             freq=wordFreq,
                                                             lang=lang,
                                                             searchType=searchType,
                                                             translit=translit))
        return result

    def process_docs_json(self, response, exclude=None, corpusSize=1):
        result = {'n_words': 0, 'n_sentences': 0, 'n_docs': 0,
                  'size_percent': 0.0,
                  'message': 'Nothing found.',
                  'metafields': [field for field in self.sc.qp.docMetaFields if not field.endswith('_kw')]}
        if ('hits' not in response
                or 'total' not in response['hits']
                or response['hits']['total']['value'] <= 0):
            return result
        if corpusSize <= 0:
            corpusSize = 1
        result['message'] = ''
        result['n_docs'] = response['hits']['total']['value']
        result['n_words'] = int(round(response['aggregations']['agg_nwords']['value'], 0))
        result['docs'] = []
        for iHit in range(len(response['hits']['hits'])):
            if exclude is not None and int(response['hits']['hits'][iHit]['_id']) in exclude:
                result['n_docs'] -= 1
                result['n_words'] -= response['hits']['hits'][iHit]['_source']['n_words']
            result['docs'].append(self.process_doc(response['hits']['hits'][iHit], exclude))
        result['size_percent'] = round(result['n_words'] * 100 / corpusSize, 3)
        return result

    def extract_cumulative_freq_by_rank(self, hits):
        """
        Process search results that contain buckets with word frequency rank. Each
        bucket contains the total frequency of a word of a given frequency rank.
        Buckets should be ordered by frequency rank.
        Return a dictionary of the kind {frequency rank: total frequency of the words
        whose rank is less or equal to this rank}.
        """
        if ('aggregations' not in hits
                or 'agg_rank' not in hits['aggregations']
                or 'buckets' not in hits['aggregations']['agg_rank']):
            return {}
        cumulFreq = 0
        freqByRank = {}
        for bucket in hits['aggregations']['agg_rank']['buckets']:
            if 'subagg_nlemmata' in bucket:
                # Subaggregation for word-based lemma frequency search
                cumulFreq += bucket['subagg_nlemmata']['value']
            else:
                cumulFreq += bucket['doc_count']
            freqByRank[bucket['key']] = cumulFreq
        return freqByRank

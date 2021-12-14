"""
Contains Flask view functions associated with certain URLs.
"""


from flask import request, render_template, jsonify, send_from_directory
import json
import copy
import re
import time
import os
import shutil
import uuid
import xlsxwriter
from werkzeug.utils import secure_filename
from . import app, settings, sc, sentView, MAX_PAGE_SIZE
from .session_management import get_locale, get_session_data, change_display_options, set_session_data
from .auxiliary_functions import jsonp, gzipped, nocache, lang_sorting_key, copy_request_args,\
    distance_constraints_too_complex, remove_sensitive_data, log_query
from .search_pipelines import *


@app.route('/search')
@app.route('/search_minimalistic')
def search_page():
    """
    Return HTML of the search page (the main page of the corpus).
    """
    queryString = ''
    if request.query_string is not None:
        queryString = request.query_string.decode('utf-8')
    ready4work = settings.ready_for_work
    if settings.ready_for_work:
        ready4work = sc.is_alive()
    bMinimalistic = ('minimalistic' in request.url_rule.rule)
    locales = settings.interface_languages
    if type(locales) == list:
        locales = {x: x for x in locales}

    return render_template('index.html',
                           minimalistic=bMinimalistic,
                           ready_for_work=ready4work,
                           locale=get_locale(),
                           corpus_name=settings.corpus_name,
                           languages=settings.languages,
                           all_lang_search=settings.all_language_search_enabled,
                           transliterations=settings.transliterations,
                           input_methods=settings.input_methods,
                           keyboards_by_tier=json.dumps(settings.keyboards,
                                                        ensure_ascii=False, indent=-1),
                           media=settings.media,
                           video=settings.video,
                           images=settings.images,
                           youtube=settings.media_youtube,
                           gloss_search_enabled=settings.gloss_search_enabled,
                           negative_search_enabled=settings.negative_search_enabled,
                           fulltext_search_enabled=settings.fulltext_search_enabled,
                           year_sort_enabled=settings.year_sort_enabled,
                           debug=settings.debug,
                           subcorpus_selection=settings.search_meta,
                           sentence_meta=settings.sentence_meta,
                           word_fields_by_tier=json.dumps(settings.word_fields_by_tier,
                                                          ensure_ascii=False, indent=-1),
                           auto_switch_tiers=json.dumps(settings.auto_switch_tiers,
                                                        ensure_ascii=False, indent=-1),
                           generate_dictionary=settings.generate_dictionary,
                           citation=settings.citation,
                           start_page_url=settings.start_page_url,
                           default_view=settings.default_view,
                           max_request_time=settings.query_timeout + 1,
                           max_page_size=MAX_PAGE_SIZE,
                           locales=locales,
                           random_seed=get_session_data('seed'),
                           query_string=queryString)


@app.route('/search_sent_query/<int:page>')
@app.route('/search_sent_query')
@jsonp
def search_sent_query(page=-1):
    """
    Return list of all ES queries made when searching for sentences.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_query_logging()
    search_sent(page=page)
    queryLog = sc.stop_logging()
    return jsonify(queryLog)


@app.route('/search_lemma_query/<int:page>')
@app.route('/search_lemma_query')
@jsonp
def search_lemma_query(page=-1):
    """
    Return list of all ES queries made when searching for lemmata.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_query_logging()
    search_lemma(page=page)
    queryLog = sc.stop_logging()
    return jsonify(queryLog)


@app.route('/search_word_query/<int:page>')
@app.route('/search_word_query')
@jsonp
def search_word_query(page=-1):
    """
    Return list of all ES queries made when searching for words.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_query_logging()
    search_word(page=page)
    queryLog = sc.stop_logging()
    return jsonify(queryLog)


@app.route('/search_doc_query')
@jsonp
def search_doc_query():
    """
    Return list of all ES queries made when searching for subcorpus documents.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_query_logging()
    search_doc()
    queryLog = sc.stop_logging()
    return jsonify(queryLog)


@app.route('/search_sent_json/<int:page>')
@app.route('/search_sent_json')
@jsonp
def search_sent_json(page=-1):
    """
    Return list of all ES responses made when searching for sentences, except for iterators.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_hits_logging()
    search_sent(page=page)
    hitsLog = sc.stop_logging()
    return jsonify(hitsLog)


@app.route('/search_lemma_json/<int:page>')
@app.route('/search_lemma_json')
@jsonp
def search_lemma_json(page=-1):
    """
    Return list of all ES responses made when searching for lemmata, except for iterators.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_hits_logging()
    search_lemma(page=page)
    hitsLog = sc.stop_logging()
    return jsonify(hitsLog)


@app.route('/search_word_json/<int:page>')
@app.route('/search_word_json')
@jsonp
def search_word_json(page=-1):
    """
    Return list of all ES responses made when searching for words, except for iterators.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_hits_logging()
    search_word(page=page)
    hitsLog = sc.stop_logging()
    return jsonify(hitsLog)


@app.route('/search_doc_json')
@jsonp
def search_doc_json():
    """
    Return list of all ES responses made when searching for subcorpus documents, except for iterators.
    """
    if not settings.debug:
        return jsonify({})
    sc.start_hits_logging()
    search_doc()
    hitsLog = sc.stop_logging()
    return jsonify(hitsLog)


@app.route('/doc_stats/<metaField>/<lang>')
@app.route('/doc_stats/<metaField>')
def get_doc_stats(metaField, lang='all'):
    """
    Return JSON with basic statistics concerning the distribution
    of corpus documents by values of one metafield. This function
    can be used to visualise (sub)corpus composition.
    """
    if metaField not in settings.search_meta['stat_options']:
        return jsonify({})
    query = copy_request_args()
    change_display_options(query)
    docIDs = subcorpus_ids(query)
    langID = -1
    if lang != 'all' and lang in settings.languages:
        langID = settings.languages.index(lang)
    buckets = get_buckets_for_doc_metafield(metaField, langID=langID, docIDs=docIDs)
    return jsonify(buckets)


@app.route('/word_freq_stats/<searchType>')
def get_word_freq_stats(searchType='word'):
    """
    Return JSON with the distribution of a particular kind of words
    or lemmata by frequency rank. This function is used for visualisation.
    Currently, it can only return statistics for a context-insensitive
    query for the whole corpus (the subcorpus constraints are
    discarded from the query). Return a list which contains results
    for each of the query words (the corresponding lines are plotted
    in different colors). Maximum number of simultaneously queried words
    is 10. All words should be in the same language; the language of the
    first word is used.
    """
    htmlQuery = copy_request_args()
    change_display_options(htmlQuery)
    log_query('word_freq_stats/' + searchType, htmlQuery)
    langID = 0
    nWords = 1
    if 'n_words' in htmlQuery and int(htmlQuery['n_words']) > 1:
        nWords = int(htmlQuery['n_words'])
        if nWords > 10:
            nWords = 10
    if searchType not in ('word', 'lemma'):
        searchType = 'word'
    if 'lang1' in htmlQuery and htmlQuery['lang1'] in settings.languages:
        langID = settings.languages.index(htmlQuery['lang1'])
    else:
        return jsonify([])
    results = []
    for iWord in range(1, nWords + 1):
        htmlQuery['lang' + str(iWord)] = htmlQuery['lang1']
        partHtmlQuery = sc.qp.swap_query_words(1, iWord, copy.deepcopy(htmlQuery))
        esQuery = sc.qp.word_freqs_query(partHtmlQuery, searchType=searchType)
        # print(esQuery)
        hits = sc.get_words(esQuery)
        # return jsonify(hits)
        curFreqByRank = sentView.extract_cumulative_freq_by_rank(hits)
        buckets = []
        prevFreq = 0
        if searchType == 'lemma':
            freq_by_rank = settings.lemma_freq_by_rank
        else:
            freq_by_rank = settings.word_freq_by_rank
        for freqRank in sorted(freq_by_rank[langID]):
            bucket = {
                'name': freqRank,
                'n_words': 0
            }
            if freqRank in curFreqByRank:
                bucket['n_words'] = curFreqByRank[freqRank] / freq_by_rank[langID][freqRank]
                prevFreq = curFreqByRank[freqRank]
            else:
                bucket['n_words'] = prevFreq / freq_by_rank[langID][freqRank]
            buckets.append(bucket)
        results.append(buckets)
    return jsonify(results)


@app.route('/word_stats/<searchType>/<metaField>')
def get_word_stats(searchType, metaField):
    """
    Return JSON with basic statistics concerning the distribution
    of a particular word form by values of one metafield. This function
    can be used to visualise word distributions across genres etc.
    If searchType == 'context', take into account the whole query.
    If searchType == 'compare', treat the query as several separate
    one-word queries. If, in this case, the data is to be displayed
    on a bar plot, process only the first word of the query.
    Otherwise, return a list which contains results for each
    of the query words (the corresponding lines are plotted
    in different colors). Maximum number of simultaneously queried words
    is 10. All words should be in the same language; the language of the
    first word is used.
    If the metaField is a document-level field, first split
    the documents into buckets according to its values and then search
    inside each bucket. If it is a sentence-level field, do a single
    search in the sentence index with bucketing.
    """
    if metaField not in settings.search_meta['stat_options']:
        return jsonify([])
    if searchType not in ('compare', 'context'):
        return jsonify([])

    htmlQuery = copy_request_args()
    if (('l_id1' not in htmlQuery or len(htmlQuery['l_id1']) <= 0)
             and ('w_id1' not in htmlQuery or len(htmlQuery['w_id1']) <= 0)):
        # If this URL was called from a word/lemma table, then we
        # have to be able to continue serving words/lemmata further down the list
        change_display_options(htmlQuery)
    log_query('word_stats/' + searchType + '/' + metaField, htmlQuery)
    langID = -1
    if 'lang1' in htmlQuery and htmlQuery['lang1'] in settings.languages:
        langID = settings.languages.index(htmlQuery['lang1'])
    nWords = 1
    if 'n_words' in htmlQuery and int(htmlQuery['n_words']) > 1:
        nWords = int(htmlQuery['n_words'])
        if searchType == 'compare':
            if nWords > 10:
                nWords = 10
            # if metaField not in settings.line_plot_meta:
            #     nWords = 1

    searchIndex = 'words'
    queryWordConstraints = None
    if ((searchType == 'context' and nWords > 1)
            or metaField in settings.sentence_meta
            or sc.qp.check_html_parameters(htmlQuery, searchOutput='words')[3] == 'sentences'):
        searchIndex = 'sentences'
        wordConstraints = sc.qp.wr.get_constraints(htmlQuery)
        set_session_data('word_constraints', wordConstraints)
        if (len(wordConstraints) > 0
                and get_session_data('distance_strict')):
            queryWordConstraints = wordConstraints
    elif searchType == 'context' and 'sentence_index1' in htmlQuery and len(htmlQuery['sentence_index1']) > 0:
        searchIndex = 'sentences'

    results = get_word_buckets(searchType, metaField, nWords, htmlQuery,
                               queryWordConstraints, langID, searchIndex)
    return jsonify(results)


@app.route('/search_sent/<int:page>')
@app.route('/search_sent')
@gzipped
def search_sent(page=-1):
    if page < 0:
        cur_search_context().flush()
        page = 0
    # try:
    hits = find_sentences_json(page=page)
    # except:
    #     return render_template('search_results/result_sentences.html', message='Request timeout.')
    cur_search_context().add_sent_to_session(hits)
    hitsProcessed = sentView.process_sent_json(hits,
                                               translit=cur_search_context().translit)
    # hitsProcessed['languages'] = settings.languages
    if len(settings.languages) > 1 and 'hits' in hits and 'hits' in hits['hits']:
        add_parallel(hits['hits']['hits'], hitsProcessed)
    hitsProcessed['languages'].sort(key=lang_sorting_key)
    hitsProcessed['page'] = get_session_data('page')
    hitsProcessed['page_size'] = get_session_data('page_size')
    hitsProcessed['media'] = settings.media
    hitsProcessed['images'] = settings.images
    hitsProcessed['subcorpus_enabled'] = False
    if 'subcorpus_enabled' in hits:
        hitsProcessed['subcorpus_enabled'] = True
    cur_search_context().sync_page_data(hitsProcessed['page'], hitsProcessed)
    maxPageNumber = (min(hitsProcessed['n_sentences'], settings.max_hits_retrieve) - 1) \
                    // hitsProcessed['page_size'] + 1
    hitsProcessed['too_many_hits'] = (settings.max_hits_retrieve < hitsProcessed['n_sentences'])

    return render_template('search_results/result_sentences.html',
                           data=hitsProcessed,
                           max_page_number=maxPageNumber)


@app.route('/get_sent_context/<int:n>')
@jsonp
def get_sent_context(n):
    """
    Retrieve the neighboring sentences for the currently
    viewed sentence number n. Take into account how many
    times this particular context has been expanded and
    whether expanding it further is allowed.
    """
    if n < 0:
        return jsonify({})
    sentData = cur_search_context().sentence_data
    if sentData is None or n >= len(sentData) or 'languages' not in sentData[n]:
        return jsonify({})
    curSentData = sentData[n]
    if curSentData['times_expanded'] >= settings.max_context_expand >= 0:
        return jsonify({})
    context, adjacentIDs = find_sent_context(curSentData, n)
    cur_search_context().update_expanded_contexts(context, adjacentIDs)
    return jsonify(context)


@app.route('/search_lemma/<int:page>')
@app.route('/search_lemma')
def search_lemma(page=-1):
    return search_word(searchType='lemma', page=page)


@app.route('/search_word/<int:page>')
@app.route('/search_word')
def search_word(searchType='word', page=-1):
    if page < 0:
        cur_search_context().flush()
        page = 0
    hitsProcessed = find_words_json(searchType=searchType, page=page)
    bShowNextButton = True
    if 'words' not in hitsProcessed or len(hitsProcessed['words']) != get_session_data('page_size'):
        bShowNextButton = False
    return render_template('search_results/result_words.html',
                           data=hitsProcessed,
                           word_table_fields=settings.word_table_fields,
                           word_search_display_gr=settings.word_search_display_gr,
                           display_freq_rank=settings.display_freq_rank,
                           search_type=searchType,
                           page=get_session_data('page'),
                           show_next=bShowNextButton)


@app.route('/search_doc')
@jsonp
def search_doc():
    query = copy_request_args()
    log_query('doc', query)
    change_display_options(query)
    query = sc.qp.subcorpus_query(query,
                                  sortOrder=get_session_data('sort'),
                                  query_size=settings.max_docs_retrieve)
    hits = sc.get_docs(query)
    hitsProcessed = sentView.process_docs_json(hits,
                                               exclude=get_session_data('excluded_doc_ids'),
                                               corpusSize=settings.corpus_size)
    hitsProcessed['media'] = settings.media
    hitsProcessed['images'] = settings.images
    return render_template('search_results/result_docs.html', data=hitsProcessed,
                           sentence_meta=settings.sentence_meta)


@app.route('/autocomplete_meta/<metafield>')
@jsonp
def autocomplete_meta(metafield):
    if 'query' not in request.args:
        return jsonify({'query': '', 'suggestions': []})
    query = request.args['query']
    if metafield not in settings.viewable_meta:
        return jsonify({'query': query, 'suggestions': []})
    suggests = suggest_metafield(metafield, query)
    return jsonify({'query': query,
                    'suggestions': suggests})


@app.route('/autocomplete_word/<lang>/<field>')
@jsonp
def autocomplete_word(lang, field):
    if ('query' not in request.args
            or lang not in settings.languages
            or field not in ('wf', 'lex')):
        return jsonify({'query': '', 'suggestions': []})
    query = request.args['query']
    suggests = suggest_word(lang, field, query)
    return jsonify({'query': query,
                    'suggestions': suggests})


@app.route('/get_word_fields')
def get_word_fields():
    """
    Return HTML with form inputs representing all additional
    word-level annotation fields.
    """
    return render_template('index/common_additional_search_fields.html',
                           word_fields=settings.word_fields,
                           sentence_meta=settings.sentence_meta,
                           multiple_choice_fields=settings.multiple_choice_fields,
                           int_meta_fields=settings.integer_meta_fields,
                           sentence_meta_values=settings.sentence_meta_values,
                           default_values=settings.default_values,
                           ambiguous_analyses=settings.ambiguous_analyses)


@app.route('/media/<path:path>')
def send_media(path):
    """
    Return the requested media file.
    """
    return send_from_directory(os.path.join('../media', settings.corpus_name), path)


@app.route('/img/<path:path>')
def send_image(path):
    """
    Return the requested image file.
    """
    return send_from_directory(os.path.join('../img', settings.corpus_name), path)


@app.route('/docs/<doc_fname>')
@gzipped
def send_text_html(doc_fname):
    """
    Return the requested document, if full-text view is enabled.
    """
    if not settings.fulltext_view_enabled:
        return ''
    doc_fname = secure_filename(re.sub('\\.html?$', '', doc_fname))
    if not doc_fname.endswith('.json'):
        doc_fname += '.json'
    try:
        with open(os.path.join('corpus_html',
                               settings.corpus_name,
                               doc_fname),
                  'r', encoding='utf-8') as fText:
            data = json.load(fText)
    except FileNotFoundError:
        data = {
            'meta': {},
            'rows': [],
            'page': 1
        }
    data['meta'] = {k: data['meta'][k]
                    for k in data['meta'] if k in settings.viewable_meta}
    page = request.args.get('page', 1)
    try:
        page = int(page) - 1
    except:
        page = 0
    if page < 0:
        page = 0
    maxPage = len(data['rows']) // settings.fulltext_page_size
    if page > maxPage:
        page = maxPage
    data['rows'] = data['rows'][page * settings.fulltext_page_size:
                                (page + 1) * settings.fulltext_page_size]
    data['page'] = page + 1
    return render_template('fulltext.html',
                           locale=get_locale(),
                           corpus_name=settings.corpus_name,
                           languages=settings.languages,
                           generate_dictionary=settings.generate_dictionary,
                           citation=settings.citation,
                           start_page_url=settings.start_page_url,
                           locales=settings.interface_languages,
                           viewable_meta=settings.viewable_meta,
                           data=data,
                           max_page_number=maxPage + 1)


@app.route('/download_cur_results_csv')
@nocache
def download_cur_results_csv():
    """
    Write all sentences the user has already seen, except the
    toggled off ones, to a CSV file. Return the contents of the file.
    """
    pageData = cur_search_context().page_data
    if pageData is None or len(pageData) <= 0:
        return ''
    result = cur_search_context().prepare_results_for_download()
    return '\n'.join(['\t'.join(s) for s in result if len(s) > 0])


@app.route('/download_cur_results_xlsx')
@nocache
def download_cur_results_xlsx():
    """
    Write all sentences the user has already seen, except the
    toggled off ones, to an XSLX file. Return the file.
    """
    pageData = cur_search_context().page_data
    if pageData is None or len(pageData) <= 0:
        return ''
    results = cur_search_context().prepare_results_for_download()
    XLSXFilename = 'results-' + str(uuid.uuid4()) + '.xlsx'
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    workbook = xlsxwriter.Workbook('tmp/' + XLSXFilename)
    worksheet = workbook.add_worksheet('Search results')
    for i in range(len(results)):
        for j in range(len(results[i])):
            worksheet.write(i, j, results[i][j])
    workbook.close()
    return send_from_directory('../tmp', XLSXFilename)


@app.route('/toggle_sentence/<int:sentNum>')
def toggle_sentence(sentNum):
    """
    Togle currently viewed sentence with the given number on or off.
    The sentences that have been switched off are not written to the
    CSV/XLSX when the user wants to download the search results.
    """
    pageData = cur_search_context().page_data
    page = get_session_data('page')
    if page is None or page == '':
        page = 0
    if pageData is None or page is None or page not in pageData:
        return json.dumps(pageData)
    if sentNum < 0 or sentNum >= len(pageData[page]):
        return ''
    pageData[page][sentNum]['toggled_off'] = not pageData[page][sentNum]['toggled_off']
    return ''


@app.route('/toggle_doc/<int:docID>')
def toggle_document(docID):
    """
    Togle given docID on or off. The documents that have been switched off
    are not included in the search.
    """
    excludedDocIDs = get_session_data('excluded_doc_ids')
    nWords = sc.get_n_words_in_document(docId=docID)
    sizePercent = round(nWords * 100 / settings.corpus_size, 3)
    if docID in excludedDocIDs:
        excludedDocIDs.remove(docID)
        nDocs = 1
    else:
        excludedDocIDs.add(docID)
        nWords = -1 * nWords
        sizePercent = -1 * sizePercent
        nDocs = -1
    return jsonify({'n_words': nWords, 'n_docs': nDocs, 'size_percent': sizePercent})


@app.route('/clear_subcorpus')
def clear_subcorpus():
    """
    Flush the list of excluded document IDs.
    """
    set_session_data('excluded_doc_ids', set())
    return ''


@app.route('/get_gramm_selector/<lang>')
def get_gramm_selector(lang=''):
    """
    Return HTML of the grammatical tags selection dialogue for the given language.
    """
    if lang not in settings.lang_props or 'gramm_selection' not in settings.lang_props[lang]:
        return ''
    grammSelection = settings.lang_props[lang]['gramm_selection']
    return render_template('modals/select_gramm.html', tag_table=grammSelection)


@app.route('/get_add_field_selector/<field>')
def get_add_field_selector(field=''):
    """
    Return HTML of the tags selection dialogue for an additional word-level field.
    """
    if field not in settings.multiple_choice_fields:
        return ''
    tagSelection = settings.multiple_choice_fields[field]
    return render_template('modals/select_gramm.html', tag_table=tagSelection)


@app.route('/get_gloss_selector/<lang>')
def get_gloss_selector(lang=''):
    """
    Return HTML of the gloss selection dialogue for the given language.
    """
    if lang not in settings.lang_props or 'gloss_selection' not in settings.lang_props[lang]:
        return ''
    glossSelection = settings.lang_props[lang]['gloss_selection']
    return render_template('modals/select_gloss.html', glosses=glossSelection)


@app.route('/get_glossed_sentence/<int:n>')
def get_glossed_sentence(n):
    """
    Return a tab-delimited glossed sentence ready for insertion into
    a linguistic paper.
    """
    if n < 0:
        return ''
    sentData = cur_search_context().sentence_data
    if sentData is None or n >= len(sentData) or 'languages' not in sentData[n]:
        return ''
    curSentData = sentData[n]
    for langView in curSentData['languages']:
        lang = langView
        try:
            langID = settings.languages.index(langView)
        except:
            # Language + number of the translation version: chop off the number
            langID = settings.languages.index(re.sub('_[0-9]+$', '', langView))
            lang = settings.languages[langID]
        if langID != 0:
            continue  # for now
        result = sentView.get_glossed_sentence(curSentData['languages'][langView]['source'], lang=lang)
        if type(result) == str:
            return result
        return ''
    return ''


@app.route('/set_locale/<lang>')
@app.route('/docs/set_locale/<lang>')
def set_locale(lang=''):
    if type(settings.interface_languages) == dict and lang not in settings.interface_languages:
        for il in settings.interface_languages:
            if settings.interface_languages[il] == lang:
                lang = il
                break
    if lang not in settings.interface_languages:
        return
    set_session_data('locale', lang)
    return ''


@app.route('/help_dialogue')
@app.route('/docs/help_dialogue')
def help_dialogue():
    l = get_locale()
    return render_template('modals/help_dialogue_' + l + '.html',
                           media=settings.media,
                           video=settings.video,
                           gloss_search_enabled=settings.gloss_search_enabled)


@app.route('/docs/dictionary/<lang>')
@app.route('/dictionary/<lang>')
@gzipped
def get_dictionary(lang):
    if not settings.generate_dictionary:
        return 'No dictionary available for this language.'
    dictFilename = 'dictionaries/dictionary_' + settings.corpus_name + '_' + lang + '.html'
    try:
        return render_template(dictFilename)
    except:
        return ''


@app.route('/config')
def setup_corpus():
    if not request.host.strip('/').endswith(('0.0.0.0:7342', '127.0.0.1:7342')):
        return 'This page can only be accessed from localhost.', 403
    return render_template('admin/corpus_setup.html',
                           filename=os.path.abspath('../USER_CONFIG/corpus.json'),
                           settings=settings.as_dict())


@app.route('/config_update', methods=['POST'])
def setup_corpus_save_changes():
    if not request.host.strip('/').endswith(('0.0.0.0:7342', '127.0.0.1:7342')):
        return 'This page can only be accessed from localhost.', 403
    data = request.form.to_dict()
    if os.path.exists('../USER_CONFIG'):
        shutil.rmtree('../USER_CONFIG')
    time.sleep(0.5)
    os.makedirs('../USER_CONFIG/translations')
    settings.save_settings(os.path.abspath('../USER_CONFIG/corpus.json'), data=data)
    settings.prepare_translations(os.path.abspath('../USER_CONFIG/translations'), data=data)
    return jsonify(result='OK')

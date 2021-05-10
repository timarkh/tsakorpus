var curClickedObj = null;
var searchType = 'none';
var excludeDocs = [];

function print_json(results) {
    hide_query_panel();
	$('.progress').css('display', 'none');
	$('#analysis').css('display', 'none');
	$('#w_id1').val('');
	$('#l_id1').val('');
	$("#search_results").html('<pre><code id="debug_code">' + JSON.stringify(results, null, 2) + '</code></pre>');
	//alert("success" + JSON.stringify(results));
}

function print_html(results) {
	//alert("success" + JSON.stringify(results));
	$('.progress').css('display', 'none');
	$('#analysis').css('display', 'none');
	$('#w_id1').val('');
	$('#l_id1').val('');
	$("#search_results").html(results);
	$('#video_prompt').show();
	toggle_interlinear();
}

function update_wordlist(results) {
	$('.progress').css('display', 'none');
	$('#analysis').css('display', 'none');
	$('#w_id1').val('');
	$('#l_id1').val('');
	$("#td_load_more_words").replaceWith(results);
	toggle_interlinear();
}

function show_player() {
	$('#media_div').css('display', 'inline-block');
}

function hide_player() {
	$('#media_div').css('display', 'none');
}

function show_img() {
	$('#image_div').css('display', 'inline-block');
	$('#image_src').click(toggle_full_image);
}

function hide_img() {
	$('#image_div').css('display', 'none');
}

function assign_word_events() {
	$("span.word").unbind('click');
	//$("span.style_span").unbind('click');
	$("span.expand").unbind('click');
	$("span.get_glossed_copy").unbind('click');
	$("span.context_header").unbind('click');
	$(".search_w").unbind('click');
	$(".search_l").unbind('click');
	$(".stat_w").unbind('click');
	$(".stat_l").unbind('click');
	$(".page_link").unbind('click');
	$(".cx_toggle_chk").unbind('change');
	$(".sent_lang").unbind('change');
	$("#td_load_more_words").unbind('click');
	$('span.word').click(highlight_cur_word);
	//$('span.style_span').click(highlight_cur_word);
	$('span.expand').click(expand_context);
	$('span.get_glossed_copy').click(copy_glossed_sentence);
	$('span.context_header').click(show_doc_meta);
	$('.search_w').click(search_word_from_list);
	$('.search_l').click(search_lemma_from_list);
	$('.stat_w').click(show_word_stats);
	$('.stat_l').click(show_lemma_stats);
	$(".page_link").click(page_click);
	$(".cx_toggle_chk").change(context_toggle);
	$('.sent_lang').click(show_sentence_img);
	$("#td_load_more_words").click(load_more_words);
	assign_para_highlight();
	assign_src_alignment();
	assign_gram_popup();
	assign_sent_meta_popup();
}

function expand_context(e) {
	let n_sent = $(e.currentTarget).attr('data-nsent');
	load_expanded_context(n_sent);
}

function copy_glossed_sentence(e) {
	let n_sent = $(e.currentTarget).attr('data-nsent');
	let hiddenTextArea = document.createElement("textarea");
	hiddenTextArea.id = "glossed_copy_textarea";
	hiddenTextArea.style.boxShadow = 'none';
	document.body.appendChild(hiddenTextArea);
	load_glossed_sentence(n_sent);
	$('#glossed_copy_textarea').focus();
	$('#glossed_copy_textarea').select();
	let successful = document.execCommand('copy');
	if (successful) {
		let pos = $(e.currentTarget).position();
		let width = $("#glossed_copy_successful").width();
		let height = $("#glossed_copy_successful").height();
		$("#glossed_copy_successful").css({left: pos.left - width - $(e.currentTarget).width() - 20, top: pos.top + $(e.currentTarget).height() / 2 - height / 2});
		$('#glossed_copy_successful').fadeIn(200);
		setTimeout(function(){
			$('#glossed_copy_successful').fadeOut(600, function() {$(this).hide();});
		}, 1200);
	}
	document.body.removeChild(hiddenTextArea);
}

function context_toggle(e) {
	let contextDiv = $(e.currentTarget).parent().parent().parent();
	contextDiv.toggleClass('context_off');
	contextID = contextDiv.attr('id').substring(7);
	$.ajax({url: "toggle_sentence/" + contextID});
}

function show_doc_meta(e) {
	var e_obj = $(e.currentTarget);
	while (e_obj.attr('class') != 'context_header') {
		e_obj = e_obj.parent();
	}
	var docMeta = e_obj.attr('data-meta');
	$("#metadata_dialogue_body").html(html_decode(docMeta.replace(/\\n/g, "\n")));
	$("#metadata_dialogue").modal('show');
}

function clear_search_form() {
	$('input.search_input').each(function (index) {
		var grandparent = $(this).parent().parent();
		if (grandparent.attr('id') && grandparent.attr('id') == 'display_options_tab') {
			return;
		}
		if ($(this).attr('id') && $(this).attr('id').search(/[^0-9]1$/) < 0) {
			return;
		}
		$(this).val('');
	});
}

function search_word_from_list(e) {
	var wID = $(e.currentTarget).attr('data-wid');
	if (wID == "") return;
	clear_search_form();
	$('#w_id1').val(wID);
	$("#search_sent").click();
}

function search_lemma_from_list(e) {
	var lID = $(e.currentTarget).attr('data-lid');
	if (lID == "") return;
	clear_search_form();
	$('#l_id1').val(lID);
	$("#search_sent").click();
}

function page_click(e) {
	var page = $(e.currentTarget).attr("data-page");
	get_sentences_page(page);
}

function make_player_markers(objContext, curFragment) {
	var markers = [];
	children = objContext.children('.src');
	usedIntervals = [];
	children.each(function () {
		var targetClasses = $(this).attr('class').split(' ');
		for (var iClass = 0; iClass < targetClasses.length; iClass++) {
			var item = targetClasses[iClass];
			if (!item.startsWith("src") || item == "src" || item.includes('highlighted')) continue;
			if (usedIntervals.indexOf(item) > -1) { continue; }
			usedIntervals.push(item);
			var alignmentInfo = srcAlignments[item];
			if (item == curFragment) {
				markers.push({'time': parseFloat(alignmentInfo.start) + 0.1,
							  'text': $(this).text() + '...',
							  'class': 'timespan_highlighted',
							  'id': item});
			}
			else {
				markers.push({'time': parseFloat(alignmentInfo.start) + 0.1,
							  'text': $(this).text() + '...',
							  'id': item});
			}
			markers.push({'time': parseFloat(alignmentInfo.end) - 0.1, 'text': '[end]',
						  'id': '[end]_' + item});
		}
	});
	return markers;
}

function src_align_span(item, i) {
	if (!item.startsWith("src") || item == "src" || item.includes('highlighted')) return;
	$('#video_prompt').hide();
	var alignmentInfo = srcAlignments[item];
	var srcPlayer = videojs('src_player');
	var realSrc = alignmentInfo.src;
	if (!realSrc.startsWith('http:') && !realSrc.startsWith('https:')) {
		realSrc = "media/" + realSrc;
	}
	if (srcPlayer.src() != realSrc) {
		if (alignmentInfo.mtype == 'audio') {
			srcPlayer.currentType('audio/wav');
		}
		srcPlayer.src(realSrc);
	}
	objContext = curClickedObj.parent();
	srcPlayer.currentTime(parseFloat(alignmentInfo.start));
	srcPlayer.play();
	var markers = make_player_markers(objContext, item);
	try
	{
		srcPlayer.markers.removeAll();
	}
	catch(err) {
		srcPlayer.markers({'markers': markers, "markerStyle": {
			'width': '2px',
			'border-radius': '30%',
			'background-color': 'green'
		},
		'onMarkerReached': markerReached});
	}
	
	srcPlayer.markers.reset(markers);
	$('.src_highlighted').removeClass('src_highlighted');
	$('.' + item).addClass('src_highlighted');
}

function markerReached(marker) {
	var srcPlayer = videojs('src_player');
	//$('.src_highlighted').removeClass('src_highlighted');
	if (marker.text == "[end]") {
		$('.' + marker.id.replace('[end]_', '')).removeClass('src_highlighted');
	}
	else {
		$('.' + marker.id).addClass('src_highlighted');
	}
	var n_markers_to_the_right = 0;
	var markers = srcPlayer.markers.getMarkers();
	for (i = 0; i < markers.length; i++) {
		//alert(markers[i].time.toString() + ' : ' + marker.time.toString());
		if (markers[i].time > marker.time) {
			n_markers_to_the_right += 1;
		}
		else if (markers[i].text == '[end]') {
			$('.' + markers[i].id.replace('[end]_', '')).removeClass('src_highlighted');
		}
	}
	if (n_markers_to_the_right == 0) {
		srcPlayer.pause();
	}
}

function show_expanded_context(results) {
	var n = results.n;
	if (n == null) {
		return;
	}
	for (lang in results.languages) {
		var resID = '#res' + n + '_' + lang;
		$(resID).html(results.languages[lang].prev + ' ' + $(resID).html() + ' ' + results.languages[lang].next);
/*
		wordSpans = $(resID).find('span');
		for (i = 1; i < wordSpans.length; i++) {
			$(wordSpans[i]).html($(wordSpans[i]).html().replace(/<span class="newline"><\/span>/g, "<br>"));
		}
*/
		newlineSpans = $(resID).find('span[class=\'newline\']');
		for (i = 0; i < newlineSpans.length; i++) {
			$(newlineSpans[i]).html('<br>');
		}
		// $(resID).html($(resID).html().replace(/<span class="newline"><\/span>/g, "<br>"));
	}
	for (var srcKey in results.src_alignment) {
        srcAlignments[srcKey] = results.src_alignment[srcKey];
    }
	var srcPlayer = null;
	try {
		srcPlayer = videojs('src_player');
		srcPlayer.pause();
	}
	catch (err) { }
	assign_word_events();
	toggle_interlinear();
}

function assign_src_alignment() {
	// $("span.src").unbind('click');
	$('span.src').click(function (e) {
		curClickedObj = $(e.target);
		var targetClasses = $(e.target).attr('class').split(' ');
		targetClasses.forEach(src_align_span);
	});
}

function show_sentence_img(e) {
	var e_obj = $(e.currentTarget);
	while (!e_obj.hasClass('sent_lang')) {
		e_obj = e_obj.parent();
	}
	var imgSrc = $(e_obj).attr('data-img');
	if (typeof imgSrc !== typeof undefined && imgSrc !== false) {
		$('#image_div').html('<img id="image_src" src="img/' + imgSrc + '">');
		$('#img_fullres').attr('src', 'img/' + imgSrc);
		show_img();
	}
	else {
		hide_img();
	}
}

function show_word_stats(e) {
	var wID = $(e.currentTarget).attr('data-wid');
	var wf = $(e.currentTarget).attr('data-wf');
	if (wID != null && wID != "" && wf != null && wf != "") {
		clear_search_form();
		$('#word_stats_wf').html(wf);
		$('#w_id1').val(wID);
	}
	else {
		$('#word_stats_wf').html(forTheQueryCaption);
	}
	$('#word_stats').modal('show');
	if ($('#word_stats_by_meta').hasClass('active')) {
		$('#select_meta_word_stat').trigger('change');
	} else if ($('#word_stats_by_freq').hasClass('active')) {
		$('#select_freq_stat_type').trigger('change');
	}
}

function show_lemma_stats(e) {
	var lID = $(e.currentTarget).attr('data-lid');
	var lemma = $(e.currentTarget).attr('data-lemma');
	if (lID != null && lID != "" && lemma != null && lemma != "") {
		clear_search_form();
		$('#word_stats_wf').html(lemma);
		$('#l_id1').val(lID);
	}
	else {
		$('#word_stats_wf').html(forTheQueryCaption);
	}
	$('#word_stats').modal('show');
	if ($('#word_stats_by_meta').hasClass('active')) {
		$('#select_meta_word_stat').trigger('change');
	} else if ($('#word_stats_by_freq').hasClass('active')) {
		$('#select_freq_stat_type').trigger('change');
	}
}

function make_sortable() {
	$('th').click(function(){
		var table = $(this).parents('table').eq(0);
		var rows = table.find('tr:gt(0)').toArray().sort(row_comparer($(this).index()));
		this.asc = !this.asc;
		if (!this.asc) {
			rows = rows.reverse()
		}
		lastRow = null;
		for (var i = 0; i < rows.length; i++) {
			if (rows[i].id != "td_load_more_words") {
				table.append(rows[i]);
			}
			else {
				lastRow = rows[i];
			}
		}
		if (lastRow != null) {
			table.append(lastRow);
		}
	})
}

function row_comparer(index) {
    return function(a, b) {
        var valA = getCellValue(a, index), valB = getCellValue(b, index);
        if (valA == undefined) {
            return 1;
        }
        if (valB == undefined) {
            return -1;
        }
        return $.isNumeric(valA) && $.isNumeric(valB) ? valA - valB : valA.localeCompare(valB);
    }
}

function getCellValue(row, index){ return $(row).children('td').eq(index).html(); }

function change_tier(e) {
	var newTier = $(e.target).val();
	var curNum = $(e.target).attr('id').replace(/^.*[^0-9]/g, '');
	var allowedFields = [];
	var allowedLabels = [];
	if (newTier in wordFieldsByTier) {
		allowedFields = wordFieldsByTier[newTier].slice();
		allowedFields.push("wf");
		allowedFields.push("lang");
		allowedFields.push("sentence_index");
		allowedFields.push("n_ana");
	}
	for (var iField = 0; iField < allowedFields.length; iField++) {
		allowedFields[iField] += curNum;
		allowedLabels.push('_label_' + allowedFields[iField]);
	}
	$('.search_input').each(function (index) {
		wordNum = $(this).attr('id').replace(/^.*[^0-9]/g, '');
		if (wordNum != curNum || $(this).attr('id').startsWith('sent_meta')) {
			return;
		}
		if (allowedFields.length <= 0 || allowedFields.includes($(this).attr('id'))) {
			$(this).removeClass('disabled_search_input');
		}
		else {
			$(this).addClass('disabled_search_input');
		}
	});
	$('.search_label').each(function (index) {
		wordNum = $(this).attr('id').replace(/^.*[^0-9]/g, '');
		if (wordNum != curNum || $(this).attr('id').startsWith('_label_sent_meta')) {
			return;
		}
		if (allowedLabels.length <= 0 || allowedLabels.includes($(this).attr('id'))) {
			$(this).removeClass('disabled_search_input');
		}
		else {
			$(this).addClass('disabled_search_input');
		}
	});
	initialize_keyboards();
}

function toggle_full_image() {
	$('#full_image').modal('show');
}

function load_more_words(e) {
	var page = $(this).attr('data-page');
	var searchType = $(this).attr('data-searchtype');
	url = "search_" + searchType + "/" + page;
	$.ajax({
		url: url,
		type: "GET",
		//beforeSend: start_progress_bar,
		//complete: stop_progress_bar,
		success: update_wordlist,
		error: function(errorThrown) {
			$('.progress').css('display', 'none');
			alert( JSON.stringify(errorThrown) );
		}
	});
}
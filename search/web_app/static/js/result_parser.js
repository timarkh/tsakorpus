var curClickedObj = null;
var searchType = 'none';
var excludeDocs = [];

function print_json(results) {
	//alert("success" + JSON.stringify(results));
	$('.progress').css('visibility', 'hidden');
	$('#analysis').css('display', 'none');
	$('#w_id1').val('');
	$("#res_p").html( "<p style=\"font-family: 'Courier New', Courier, 'Lucida Sans Typewriter', 'Lucida Typewriter', monospace;\">Success!<hr>" + JSON.stringify(results, null, 2).replace(/\n/g, "<br>").replace(/ /g, "&nbsp;") ) + "</p>";
}

function print_html(results) {
	//alert("success" + JSON.stringify(results));
	$('.progress').css('visibility', 'hidden');
	$('#analysis').css('display', 'none');
	$('#w_id1').val('');
	$("#res_p").html(results);
	toggle_interlinear();
}

function show_player() {
	$('#media_div').css('display', 'inline-block');
}

function hide_player() {
	$('#media_div').css('display', 'none');
}

function assign_word_events() {
	$("span.word").unbind('click');
	$("span.expand").unbind('click');
	$("span.get_glossed_copy").unbind('click');
	$("span.context_header").unbind('click');
	$("span.search_w").unbind('click');
	$("span.stat_w").unbind('click');
	$("span.page_link").unbind('click');
	$(".cx_toggle_chk").unbind('change');
	$('span.word').click(highlight_cur_word);
	$('span.expand').click(expand_context);
	$('span.get_glossed_copy').click(copy_glossed_sentence);
	$('span.context_header').click(show_doc_meta);
	$('span.search_w').click(search_word_from_list);
	$('span.stat_w').click(show_word_stats);
	$("span.page_link").click(page_click);
	$(".cx_toggle_chk").change(context_toggle);
	assign_para_highlight();
	assign_src_alignment();
	assign_gram_popup();
	assign_sent_meta_popup();
}

function highlight_cur_word(e) {
	targetClasses = $(this).attr('class').split(' ');
	$('.w_highlighted').removeClass('w_highlighted');
	targetClasses.forEach(highlight_word_spans);
}

function expand_context(e) {
	var n_sent = $(e.currentTarget).attr('data-nsent');
	load_expanded_context(n_sent);
}

function copy_glossed_sentence(e) {
	var n_sent = $(e.currentTarget).attr('data-nsent');
	var hiddenTextArea = document.createElement("textarea");
	hiddenTextArea.id = "glossed_copy_textarea";
	hiddenTextArea.style.boxShadow = 'none';
	document.body.appendChild(hiddenTextArea);
	load_glossed_sentence(n_sent);
	$('#glossed_copy_textarea').focus();
	$('#glossed_copy_textarea').select();
	var successful = document.execCommand('copy');
	document.body.removeChild(hiddenTextArea);
}

function context_toggle(e) {
	var contextDiv = $(e.currentTarget).parent().parent().parent();
	contextDiv.toggleClass('context_off');
	contextID = contextDiv.attr('id').substring(7);
	$.ajax({url: "toggle_sentence/" + contextID});
}

function show_doc_meta(e) {
	var e_obj = $(e.currentTarget);
	while (e_obj.attr('class') != 'context_header') {
		e_obj = e_obj.parent();
	}
	var doc_meta = e_obj.attr('data-meta');
	alert(doc_meta.replace(/\\n/g, "\n"));
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

function page_click(e) {
	var page = $(e.currentTarget).attr("data-page");
	get_sentences_page(page);
}

function highlight_word_spans(item, i) {
	if (item == "word" || item.includes('match') || !item.startsWith("w")) return;
	$('.' + item).addClass('w_highlighted');
}

function highlight_para_spans(item, i) {
	if (item == "para" || item.includes('match') || !item.startsWith("p")) return;
	$('.' + item).addClass('p_highlighted');
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

function assign_para_highlight() {
	$("span.para").unbind('hover');
	$("span.para").unbind('mousemove');
	$('span.para').hover(function (e) {
		$('.p_highlighted').removeClass('p_highlighted');
		var targetClasses = $(this).attr('class').split(' ');
		targetClasses.forEach(highlight_para_spans);
	}, function () {
		$('.p_highlighted').removeClass('p_highlighted');
	});
}

function assign_src_alignment() {
	// $("span.src").unbind('click');
	$('span.src').click(function (e) {
		curClickedObj = $(e.target);
		var targetClasses = $(e.target).attr('class').split(' ');
		targetClasses.forEach(src_align_span);
	});
}

function assign_sent_meta_popup() {
    $("span.sent_lang").unbind('hover');
	$("span.sent_lang").unbind('mousemove');
    $('span.sent_lang').hover(function (e) {
/*
        var sentMeta = $(this).find('.sentence_meta');
        if (sentMeta.html() != '') {
			sentMeta.show();
        }
*/
	}, function () {
		$('.sentence_meta').hide();
	});
}

function assign_gram_popup() {
	var moveLeft = 20;
	var moveDown = 10;
	$("span.word, span.word_in_table").unbind('hover');
	$("span.word, span.word_in_table").unbind('mousemove');
	$('.word, .word_in_table').hover(function (e) {
		$('#analysis').replaceWith('<div id="analysis">' + $("<textarea/>").html(($(this).attr("data-ana"))).text() + '</div>');
		anaWidth = $('#analysis').width();
		anaHeight = $('#analysis').height();
		$('#analysis').css('left', $(document).innerWidth() - anaWidth - 30);
		$('#analysis').css('top', $(document).innerHeight() - anaHeight - 30);
		$('#analysis').show();
        if ($('.sentence_meta').length > 0) {
			var prevEl = $(this).prev();
			while (true) {
				if (prevEl.hasClass('sentence_meta')) {
					break;
				}
				prevEl = prevEl.prev();
			}
			if (prevEl.hasClass('sentence_meta')) {
				$('.sentence_meta').hide();
				prevEl.show();
			}
        }
	}, function () {
		$('#analysis').hide();
        $('.sentence_meta').hide();
	});
	$('.word, .word_in_table').mousemove(function (e) {
		anaWidth = $('#analysis').width();
		anaHeight = $('#analysis').height();
		if (e.pageX + moveLeft + anaWidth + 30 < $(document).innerWidth()) {
			$('#analysis').css('left', e.pageX + moveLeft);
			$('#analysis').width(anaWidth);
		}
		else {
			$('#analysis').css('left', $(document).innerWidth() - anaWidth - 30);
			$('#analysis').width(anaWidth);
		}
		if (e.pageY + moveDown + anaHeight + 30 < $(document).innerHeight()) {
			$('#analysis').css('top', e.pageY + moveDown);
			$('#analysis').height(anaHeight);
		}
		else {
			$('#analysis').css('top', $(document).innerHeight() - anaHeight - 30);
			$('#analysis').height(anaHeight);
		}
	});
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

function toggle_interlinear() {
	if (searchType != 'sentences') {
		return;
	}
	if ($('#viewing_mode option:selected').attr('value') == 'glossed')
	{
		$('span.word, span.word_in_table').each(function (index) {
			if ($(this).find('.ana_interlinear').length > 0) {
				return;
			}
			$(this).css("display", "inline-table");
			var data_ana = $(this).attr('data-ana');
			if (data_ana == null || data_ana.length <= 0) {
				return;
			}
			data_ana = data_ana.replace('class="popup_word"', 'class="popup_word ana_interlinear"');
			data_ana = data_ana.replace(/<span class="popup_(key|wf)">.*?<\/span>/g, '');
			data_ana = data_ana.replace('class="popup_value"', 'class="popup_value_small"');
			data_ana = data_ana.replace(/(class="popup_value">[^<>]{38,100}?)[ ,;][^<>]{3,}/g, '$1...');
			if (/<div class="popup_word[^<>]*>\s*<\/div>\s*/.test(data_ana)) {
				return;
			}
			$(this).html($(this).html() + '<br>' + data_ana);
		});
	}
	else {
		$('span.word, span.word_in_table').each(function (index) {
			$(this).css("display", "inline-block");
			$(this).html($(this).html().replace(/<br>/, ''));
		});
		$('.ana_interlinear').remove();
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
		for (var i = 0; i < rows.length; i++) {
			table.append(rows[i])
		}
	})
}

function row_comparer(index) {
    return function(a, b) {
        var valA = getCellValue(a, index), valB = getCellValue(b, index);
        return $.isNumeric(valA) && $.isNumeric(valB) ? valA - valB : valA.localeCompare(valB);
    }
}

function getCellValue(row, index){ return $(row).children('td').eq(index).html(); }
var curClickedObj = null;

function print_json(results) {
	//alert("success" + JSON.stringify(results));
	$("#res_p").html( "<p style=\"font-family: 'Courier New', Courier, 'Lucida Sans Typewriter', 'Lucida Typewriter', monospace;\">Success!<hr>" + JSON.stringify(results, null, 2).replace(/\n/g, "<br>").replace(/ /g, "&nbsp;") ) + "</p>";
}

function print_html(results) {
	//alert("success" + JSON.stringify(results));
	$("#res_p").html( results );
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
	$("span.context_header").unbind('click');
	$("span.search_w").unbind('click');
	$("span.page_link").unbind('click');
	$(".cx_toggle_chk").unbind('change');
	$('span.word').click(highlight_cur_word);
	$('span.expand').click(expand_context);
	$('span.context_header').click(show_doc_meta);
	$('span.search_w').click(search_word_from_list);
	$("span.page_link").click(page_click);
	$(".cx_toggle_chk").change(context_toggle);
	assign_para_highlight();
	assign_src_alignment();
	assign_gram_popup();
}

function highlight_cur_word(e) {
	//alert('Highlight called.');
	//alert($(e.target).attr('class'));
	targetClasses = $(e.target).attr('class').split(' ');
	$('.w_highlighted').css({'border-style': 'none'});
	$('.w_highlighted').removeClass('w_highlighted');
	targetClasses.forEach(highlight_word_spans);
	//alert($(e.target).attr('data-ana').replace(/\\n/g, "\n"));
}

function expand_context(e) {
	//alert($(e.currentTarget).attr('class'));
	var n_sent = $(e.currentTarget).attr('data-nsent');
	load_expanded_context(n_sent);
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

function search_word_from_list(e) {
	wf = $(e.currentTarget).attr('data-wf');
	if (wf == "") return;
	$('input.search_input').each(function (index) {
		if ($(this).parent().parent().attr('id') == 'display_options_tab') {
			return;
		}
		if ($(this).attr('id').search(/[^0-9]1$/) < 0) {
			return;
		}
		$(this).val('');
	});
	$('#wf1').val(wf);
	$("#search_sent").click();
}

function page_click(e) {
	var page = $(e.currentTarget).attr("data-page");
	get_sentences_page(page);
}

function highlight_word_spans(item, i) {
	if (item == "word" || item.includes('match') || !item.startsWith("w")) return;
	$('.' + item).css({'border-color': '#FF9000', 'border-radius': '5px',
					   'border-width': '2px', 'border-style': 'solid'});
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
	if (srcPlayer.src() != "media/" + alignmentInfo.src) {
		if (alignmentInfo.mtype == 'audio') {
			srcPlayer.currentType('audio/wav');
		}
		srcPlayer.src("media/" + alignmentInfo.src);
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
		wordSpans = $(resID).find('span');
		for (i = 1; i < wordSpans.length; i++) {
			$(wordSpans[i]).html($(wordSpans[i]).html().replace(/<span class="newline"><\/span>/g, "<br>"));
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
}

function assign_para_highlight() {
	$("span.para").unbind('hover');
	$("span.para").unbind('mousemove');
	$('span.para').hover(function (e) {
		$('.p_highlighted').removeClass('p_highlighted');
		var targetClasses = $(e.target).attr('class').split(' ');
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

function assign_gram_popup() {
	var moveLeft = 20;
	var moveDown = 10;
	$("span.word").unbind('hover');
	$("span.word").unbind('mousemove');
	$('.word').hover(function (e) {
		$('#analysis').replaceWith('<div id="analysis">' + $("<textarea/>").html(($(e.target).attr("data-ana"))).text() + '</div>');
		anaWidth = $('#analysis').width();
		anaHeight = $('#analysis').height();
		$('#analysis').css('left', $(document).innerWidth() - anaWidth - 30);
		$('#analysis').css('top', $(document).innerHeight() - anaHeight - 30);
		$('#analysis').show();
	}, function () {
		$('#analysis').hide();
	});
	$('.word').mousemove(function (e) {
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
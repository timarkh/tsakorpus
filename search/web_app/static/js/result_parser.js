function print_json(results) {
	//alert("success" + JSON.stringify(results));
	$("#res_p").html( "<p style=\"font-family: 'Courier New', Courier, 'Lucida Sans Typewriter', 'Lucida Typewriter', monospace;\">Success!<hr>" + JSON.stringify(results, null, 2).replace(/\n/g, "<br>").replace(/ /g, "&nbsp;") ) + "</p>";
}

function print_html(results) {
	//alert("success" + JSON.stringify(results));
	$("#res_p").html( results );
}

function assign_word_events() {
	$("span.word").unbind('click');
	$("span.expand").unbind('click');
	$("span.context_header").unbind('click');
	$("span.search_w").unbind('click');
	$("span.page_link").unbind('click');
	$('span.word').click(highlight_cur_word);
	$('span.expand').click(expand_context);
	$('span.context_header').click(show_doc_meta);
	$('span.search_w').click(search_word_from_list);
	$("span.page_link").click(page_click);
	assign_para_highlight();
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
	var n_sent = $(e.target).attr('data-nsent');
	load_expanded_context(n_sent);
	$('#res' + n_sent).html($('#res' + n_sent).html().replace(/<span class="newline"><\/span>/g, "<br>"));
}

function show_doc_meta(e) {
	var e_obj = $(e.target);
	while (e_obj.attr('class') != 'context_header') {
		e_obj = e_obj.parent();
	}
	var doc_meta = e_obj.attr('data-meta');
	alert(doc_meta.replace(/\\n/g, "\n"));
}

function search_word_from_list(e) {
	wf = $(e.target).attr('data-wf');
	if (wf == "") return;
	$('.search_input').val("");
	$('#wf1').val(wf);
	$("#search_sent").click();
}

function page_click(e) {
	var page = $(e.target).attr("data-page");
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

function show_expanded_context(results) {
	var n = results.n;
	for (lang in results.languages) {
		var resID = '#res' + n + '_' + lang;
		$(resID).html(results.languages[lang].prev + ' ' + $(resID).html() + ' ' + results.languages[lang].next);
	}
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

function assign_gram_popup() {
	var moveLeft = 20;
	var moveDown = 10;
	$("span.word").unbind('hover');
	$("span.word").unbind('mousemove');
	$('.word').hover(function (e) {
		$('div#analysis').replaceWith('<div id="analysis">' + $(e.target).attr("data-ana") + '</div>');
		$('div#analysis').show();
	}, function () {
		$('div#analysis').hide();
	});
	$('.word').mousemove(function (e) {
		$('div#analysis').css('top', e.pageY + moveDown).css('left', e.pageX + moveLeft);
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
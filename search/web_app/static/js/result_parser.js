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
}

function highlight_cur_word(e) {
	//alert('Highlight called.');
	//alert($(e.target).attr('class'));
	targetClasses = $(e.target).attr('class').split(' ');
	$('.word').css({'border-style': 'none'});
	targetClasses.forEach(highlight_word_spans);
	alert($(e.target).attr('data-ana').replace(/\\n/g, "\n"));
}

function expand_context(e) {
	var n_sent = $(e.target).attr('data-nsent');
	load_expanded_context(n_sent);
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
	if (item == "word" || item.endsWith('match')) return;
	$('.' + item).css({'border-color': '#FF9000', 'border-radius': '5px',
					   'border-width': '2px', 'border-style': 'solid'});
}

function show_expanded_context(results) {
	var n = results.n;
	$('#res' + n).html(results.prev + ' ' + $('#res' + n).html() + ' ' + results.next);
	assign_word_events();
}
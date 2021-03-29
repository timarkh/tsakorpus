function assign_input_events() {
	$("#show_help").unbind('click');
	$("#show_dictionary").unbind('click');
	$("#cite_corpus").unbind('click');
	$("a.locale").unbind('click');
	$("#viewing_mode").unbind('change');
	$('.toggle_glossed_layer').unbind('click');
	$("#show_help").click(show_help);
	$("#show_dictionary").click(show_dictionary);
	$("#cite_corpus").click(show_citation);
	$("a.locale").click(change_locale);
	$("#viewing_mode").change(toggle_interlinear);
	$('.toggle_glossed_layer').click(toggle_glossed_layer);
	assign_tooltips();
}

function assign_word_events() {
	$("span.word").unbind('click');
	$('span.word').click(highlight_cur_word);
	$(".page_link").unbind('click');
	$(".page_link").click(page_click_fulltext);
	// assign_para_highlight();
	assign_gram_popup();
	assign_sent_meta_popup();
}

function page_click_fulltext(e) {
	var page = $(e.currentTarget).attr("data-page");
	var url = window.location.href.split('?')[0];    
	url += '?page=' + page;
	window.location.href = url;
}
function print_json(results) {
	//alert("success" + JSON.stringify(results));
	$("#res_p").html( "<p style=\"font-family: 'Courier New', Courier, 'Lucida Sans Typewriter', 'Lucida Typewriter', monospace;\">Success!<hr>" + JSON.stringify(results, null, 2).replace(/\n/g, "<br>").replace(/ /g, "&nbsp;") ) + "</p>";
}

function print_html(results) {
	//alert("success" + JSON.stringify(results));
	$("#res_p").html( results );
}

function assign_word_events() {
	$('span.word').click(highlight_cur_word);
}

function highlight_cur_word(e) {
	//alert('Highlight called.');
	//alert($(e.target).attr('class'));
	targetClasses = $(e.target).attr('class').split(' ');
	$('.word').css({'border-style': 'none'});
	targetClasses.forEach(highlight_word_spans);
	alert($(e.target).attr('data-ana').replace(/\\n/g, "\n"));
}

function highlight_word_spans(item, i) {
	if (item == "word") return;
	$('.' + item).css({'border-color': '#FF9000', 'border-radius': '5px',
					   'border-width': '2px', 'border-style': 'solid'});
}
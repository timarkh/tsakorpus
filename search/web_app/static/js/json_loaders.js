$(function() {
	$("#search_sent").click(get_sentences);
	
	$("#search_sent_json").click(function() {
		//$("#header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent_json",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: print_json,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_sent_query").click(function() {
		//$("#header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent_query",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: print_json,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_word").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_word",
			data: $("#search_main").serialize(),
			type: "GET",
			success: print_html,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_word_json").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_word_json",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: print_json,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_word_query").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_word_query",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: print_json,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	assign_input_events();
});

function load_expanded_context(n_sent) {
	$.ajax({
		url: "get_sent_context/" + n_sent,
		type: "GET",
		dataType : "json",
		success: show_expanded_context,
//		success: print_json,
		error: function(errorThrown) {
			alert( JSON.stringify(errorThrown) );
		}
	});
}

function get_sentences() {
	get_sentences_page(-1);
}

function get_sentences_page(page) {
	if (page < 0) {
		$.ajax({
			url: "search_sent",
			data: $("#search_main").serialize(),
			type: "GET",
			success: print_html,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	else {
		$.ajax({
			url: "search_sent/" + page,
			type: "GET",
			success: print_html,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
}

function assign_input_events() {
	$("span.word_plus").unbind('click');
	$("span.word_minus").unbind('click');
	$("span.word_plus").click(add_word_inputs);
}

function add_word_inputs(e) {
	var new_word_num = parseInt($("#n_words").attr('value'));
	if (new_word_num <= 0) { return; }
	new_word_num += 1;
	word_div_html = '<div class="word_search">\n' + $('#first_word').html() + '</div>';
	// word_div_html = word_div_html.replace(' id="first_word"', '');
	word_div_html = word_div_html.replace(/1/g, new_word_num)
	word_div = $.parseHTML(word_div_html);
	$("div.words_search").append(word_div);
	$("#n_words").attr('value', new_word_num);
	assign_input_events();
}
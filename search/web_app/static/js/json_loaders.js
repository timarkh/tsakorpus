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

	$("#search_doc").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_doc",
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
	
	$("#search_doc_json").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_doc_json",
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
	
	$("#search_doc_query").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_doc_query",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: print_json,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	load_additional_word_fields();
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

function load_additional_word_fields() {
	$.ajax({
		url: "get_word_fields",
		type: "GET",
		success: function(result) {
			$("div.add_word_fields").html(result);
		},
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
	$("span.add_rel").unbind('click');
	$("input.neg_query").unbind('change');
	$("span.word_plus").click(add_word_inputs);
	$("span.add_rel").click(add_word_relations);
	$("input.neg_query").change(negative_query);
}

function negative_query(e) {
	var word_div = $(this).parent();
	if (word_div.css("background-color") != "rgb(20, 20, 20)") {
		word_div.css({"background-color": "rgb(20, 20, 20)", "color": "#fff"});
	}
	else {
		word_div.css({"background-color": "#fff", "color": "black"});
	}
}

function add_word_inputs(e) {
	var new_word_num = parseInt($("#n_words").attr('value'));
	if (new_word_num <= 0) { return; }
	new_word_num += 1;
	word_div_html = '<div class="word_search" id="wsearch_' + new_word_num + '">\n' + $('#first_word').html();
	word_div_html = word_div_html.replace(/1/g, new_word_num)
	word_div_html += '<br><span class="add_rel" data-nword="' + new_word_num + '" data-nrels="0">add relation</span>';
	word_div_html += '</div>';
	word_div = $.parseHTML(word_div_html);
	$("div.words_search").append(word_div);
	$("#n_words").attr('value', new_word_num);
	assign_input_events();
}

function add_word_relations(e) {
	var word_num = parseInt($(e.target).attr('data-nword'));
	if (word_num <= 0) { return; }
	var nrels = parseInt($(e.target).attr('data-nrels'));
	$(e.target).attr('data-nrels', nrels + 1);
	word_rel_html = '<div class="word_rel"> Distance to word #<input type="number" class="search_input" name="word_rel_' + word_num + '_' + nrels + '"><br>';
	word_rel_html += 'from <input type="number" class="search_input" name="word_dist_from_' + word_num + '_' + nrels + '"><br>';
	word_rel_html += 'to <input type="number" class="search_input" name="word_dist_to_' + word_num + '_' + nrels + '"> ';
	word_rel_html += '</div>';
	word_rel_div = $.parseHTML(word_rel_html);
	$("#wsearch_" + word_num).append(word_rel_div);
}

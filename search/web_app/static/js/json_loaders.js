$(function() {
	$("#search_sent").click(function() {
		//$("#header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent",
			data: $("#search_main").serialize(),
			type: "GET",
			success: print_html,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
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
			dataType : "text/html",
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

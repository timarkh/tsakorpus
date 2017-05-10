$(function() {
	$("#search_sent").click(function() {
		//$("#header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: parse,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_sent_test").click(function() {
		//$("#header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent_test",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: parse,
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
			dataType : "json",
			success: parse,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_word_test").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_word_test",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: parse,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
});
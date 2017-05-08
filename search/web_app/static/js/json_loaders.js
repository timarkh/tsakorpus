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
				alert( "111" );
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
});
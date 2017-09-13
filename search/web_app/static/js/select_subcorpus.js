$(function() {
	function assign_subcorpus_events() {
		$('.switchable_subcorpus_option').unbind('click');
		$('.switchable_subcorpus_option').click(toggle_subcorpus_option);
		$('#load_documents_link').click(load_subcorpus_documents);
	}

	function toggle_subcorpus_option(e) {
		$(this).toggleClass('subcorpus_option_enabled');
		rebuild_subcorpus_queries();
	}

	function rebuild_subcorpus_queries() {
		var dict_fields = new Object();
		$('.switchable_subcorpus_option').each(function (index) {
			var field = $(this).attr('data-name');
			if (!(field in dict_fields)) {
				dict_fields[field] = [];
			}
			if ($(this).hasClass('subcorpus_option_enabled')) {
				var val = $(this).attr('data-value');
				dict_fields[field].push(val);
			}
		});
		for (var field in dict_fields) {
			var formula = '';
			for (i = 0; i < dict_fields[field].length; i++) {
				formula += dict_fields[field][i];
				if (i < dict_fields[field].length - 1) {
					formula += '|';
				}
			}
			$('#' + field).val(formula);
		}
	}
	
	function load_subcorpus_documents(e) {
		$.ajax({
			url: "search_doc_json",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			success: print_document_list,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function print_document_list(results) {
		$('#subcorpus_documents').html(JSON.stringify(results, null, 2).replace(/\n/g, "<br>").replace(/ /g, "&nbsp;") );
	}

	assign_subcorpus_events();
});

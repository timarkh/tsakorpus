$(function() {
	function assign_subcorpus_events() {
		$('.switchable_subcorpus_option').unbind('click');
		$('#subcorpus_selector_ok').unbind('click');
		$('#subcorpus_selector_clear').unbind('click');
		$('.switchable_subcorpus_option').click(toggle_subcorpus_option);
		$('#load_documents_link').click(load_subcorpus_documents);
		$('#subcorpus_selector_ok').click(close_subcorpus_selector);
		$('#subcorpus_selector_clear').click(clear_subcorpus);
	}
	
	function assign_document_list_events() {
		$(".doc_toggle_chk").unbind('change');
		$(".doc_toggle_chk").change(toggle_doc_exclusion);
	}

	function toggle_doc_exclusion(e) {
		var docTR = $(e.currentTarget).parent().parent();
		docTR.toggleClass('context_off');
		docID = docTR.attr('id').substring(3);
		$.ajax({url: "toggle_doc/" + docID});
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
			url: "search_doc",
			data: $("#search_main").serialize(),
			type: "GET",
			success: print_document_list,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function print_document_list(results) {
		$('#subcorpus_documents').html(results);
		assign_word_events();
		assign_document_list_events();
		make_sortable();
	}
	
	function close_subcorpus_selector() {
		$('.nav-tabs a[href="#select_subcorpus_parameters"]').tab('show');
		$('#subcorpus_selector').modal('toggle');
	}
	
	function clear_subcorpus() {
		$('.switchable_subcorpus_option').each(function (index) {
			$(this).removeClass('subcorpus_option_enabled');
		});
		$('.subcorpus_input').each(function (index) {
			$(this).val('');
		});
		$.ajax({
			url: "clear_subcorpus",
			data: $("#search_main").serialize(),
			type: "GET",
			success: close_subcorpus_selector,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}

	assign_subcorpus_events();
});

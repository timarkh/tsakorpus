function share_query() {
	var query = $("#search_main").serialize().replace(/[^=?&]+=(&|$)/g, '');
	if (excludeDocs.length > 0) {
		query += 'exclude_docs=' + excludeDocs.join();
	}
	$('#query_to_share').html(query);
	$('#query_share_dialogue').modal('toggle');
}

function show_load_query() {
	$('#query_load_dialogue').modal('toggle');
	$('#query_to_load').val('');
}

function clear_all_search_fields() {
	$('input.search_input').val('');
	$('#distance_strict').prop('checked', false);
	$('#precise').prop('checked', false);
}

function load_query() {
	var query = $('#query_to_load').val().trim();
	$('#query_load_dialogue').modal('toggle');
	if (query.length <= 0) { return; }
	var pairs = query.split('&');
	var dictFields = {};
	var word_rels = [];
	var neg_queries = [];
	var docs2exclude = [];
	rxWordRel = /word_rel_([0-9]+)/g;
	rxNegQuery = /negq([0-9]+)/g;
	$.each(pairs, function(i, pair){
		if (pair.length <= 2) { return; }
        var kv = pair.split("=");
		var key = decodeURIComponent(kv[0]);
        var value = decodeURIComponent(kv[1]);
		var negQueryMatch = rxNegQuery.exec(key);
		if (negQueryMatch != null && negQueryMatch.length > 1 && value == 'on') {
			neg_queries.push(negQueryMatch[1]);
			return;
		}
		if (key == 'exclude_docs' && value.length > 0) {
			docs2exclude = value.split(',');
			return;
		}
		wordRelMatch = rxWordRel.exec(key);
		if (wordRelMatch != null && wordRelMatch.length > 1 && $('#' + key).length <= 0) {
			word_rels.push(wordRelMatch[1]);
		}
		dictFields[key] = value;
	});
	if (!('n_words' in dictFields)) {
		return;
	}
	clear_all_search_fields();
	clear_subcorpus();
	var curNWords = $('#n_words').val();
	if (curNWords < parseInt(dictFields['n_words'])) {
		for (var i = 0; i < parseInt(dictFields['n_words']) - curNWords; i++) {
			$('#first_word .word_plus').trigger('click');
		}
	}
	else if (curNWords > parseInt(dictFields['n_words'])) {
		for (var i = 0; i < curNWords - parseInt(dictFields['n_words']); i++) {
			$('#wsearch_' + (curNWords - i) + ' .word_minus').trigger('click');
		}
	}
	$.each(word_rels, function (i, wordNum) {
		$('#wsearch_' + wordNum + ' .add_rel').trigger('click');
	});
	$.each(neg_queries, function (i, wordNum) {
		$('#wsearch_' + wordNum + ' .neg_query').trigger('click');
	});
	$.each(dictFields, function (field, value) {
		if ($('#' + field).length > 0 && $('#' + field).attr('type') == 'checkbox') {
			if (value == 'on') {
				$('#' + field).prop('checked', true);
			}
			return;
		}
		$('#' + field).val(value);
	});
	$.each(docs2exclude, function (i, docID) {
		exclude_doc(docID);
	});
}
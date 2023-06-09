function share_query() {
	var query = share_query_str();
	$('#query_to_share').html(query);
	$('#query_share_dialogue').modal('toggle');
}

function share_query_str() {
	var query = $("#search_main").serialize().replace(/[^=?&]+=(&|$)/g, '');
	if (excludeDocs.length > 0) {
		query += 'exclude_docs=' + excludeDocs.join();
	}
	return query;
}

function show_load_query() {
	$('#query_load_dialogue').modal('toggle');
	$('#query_to_load').val('');
}

function clear_all_search_fields() {
	$('input.search_input').val('');
	$('.word_search').removeClass('negated');
	$('.word_search_r').removeClass('negated');
	$('.neg_query_checkbox').prop('checked', false);
	$('#distance_strict').prop('checked', true);
	$('#precise').prop('checked', true);
}

async function load_query() {
	var query = $('#query_to_load').val().trim();
	$('#query_load_dialogue').modal('hide');
	await load_query_str(query);
}

async function expand_all_words() {
	$('.word_search .bi-box-arrow-down').each(function(index) {
		var div_extra_fields = $(this).parent().parent().find('.add_word_fields');
		var oldTransitionDuration = div_extra_fields.css('transition');
		div_extra_fields.css('transition', '');  // Temporarily switch off visual effects
		$(this).trigger('click');
		
		div_extra_fields.css('transition', oldTransitionDuration);
	})
	await sleep(20);
}

async function load_query_str(query) {
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
	// Expand additional fields where not expanded, otherwise their values
	// will not be able to get there
	await expand_all_words();
	// Expand word distance sections where needed
	$.each(word_rels, function (i, wordNum) {
		$('#wsearch_' + wordNum + ' .add_rel').trigger('click');
	});
	// Toggle negative queries where needed
	$.each(neg_queries, function (i, wordNum) {
		if (wordNum > 1) {
			$('#wsearch_' + wordNum + ' .neg_query').trigger('click');
		}
		else {
			$('#first_word .neg_query').trigger('click');
		}
	});
	// Insert the values supplied in query
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

function get_param(query, key) {
    key = key.replace(/[\[\]]/g, '\\$&');
    var rx_key = new RegExp('[?&]' + key + '(=([^&#]*)|&|#|$)'),
        results = rx_key.exec(query);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function remember_query(query_type) {
	var query = share_query_str();
	var word = '';
	var lemma = '';
	var gramm = '';
	var subcorpus = '';
	for (i = 1; i <= 10; ++i) {
		cur_wf = get_param(query, 'wf' + i);
		if (cur_wf != null) {
			if (word.length > 0) {
				word += ' + ';
			}
			word += cur_wf;
		}
		cur_lemma = get_param(query, 'lex' + i);
		if (cur_lemma != null) {
			if (lemma.length > 0) {
				lemma += ' + ';
			}
			lemma += cur_lemma;
		}
		cur_gramm = get_param(query, 'gr' + i);
		if (cur_gramm != null) {
			if (gramm.length > 0) {
				gramm += ' + ';
			}
			gramm += cur_gramm;
		}
	}
	if (word.length <= 0) {
		word = '*';
	}
	if (lemma.length <= 0) {
		lemma = '*';
	}
	if (gramm.length <= 0) {
		gramm = '*';
	}

	if (get_param(query, 'exclude_docs') != null) {
		subcorpus = 'yes';
	}
	$('.subcorpus_input').each(function (index) {
		var attr_name = $(this).attr('name');
		if (attr_name == null || attr_name.length <= 0) {
			attr_name = $(this).attr('data-name');
		}
		if (attr_name != null && attr_name.length > 0 && get_param(query, attr_name) != null) {
			subcorpus = 'yes';
		}
	})
	if (subcorpus.length > 0) {
		subcorpus = '<i class="bi bi-check-circle-fill info_icon"></i>';
	}

	var curTime = new Date().toLocaleTimeString('en-US', { hour12: false, 
                                             hour: "numeric", 
                                             minute: "numeric"});
	var tr = '<tr>';
	tr += '<td>' + word + '</td>';
	tr += '<td>' + lemma + '</td>';
	tr += '<td>' + gramm + '</td>';
	tr += '<td>' + subcorpus + '</td>';
	tr += '<td>' + query_type + '</td>';
	tr += '<td>' + curTime + '</td>';
	tr += '<td><a class="repeat_query_link"><i class="bi bi-arrow-repeat info_icon" data-tooltip="tooltip" data-placement="top" title="' + $('#repeat_query_header').attr('title') + '" data-query="' + query + '" data-query-type="' + query_type +'"></i></a></td>';
	tr += '</tr>\n';
	$('#query_history_table_body').html(tr + $('#query_history_table_body').html());
	$('#no_queries_alert').hide();
	$(".repeat_query_link").unbind('click');
	$(".repeat_query_link").click(repeat_query);
}

function repeat_query(e) {
	var query = $(e.target).attr('data-query');
	var search_type = $(e.target).attr('data-query-type');
	load_query_str(query);
	$('#query_history').modal('toggle');
	if (search_type == 'sentence') {
		$('#search_sent').click();
	}
	else if (search_type == 'word') {
		$('#search_word').click();
	}
	else if (search_type == 'lemma') {
		$('#search_lemma').click();
	}
}
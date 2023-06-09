$(function() {
	$("#search_sent").click(get_sentences);
	
	$("#search_sent_json").click(function() {
		//$("#corpus_header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent_json",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_sent_query").click(function() {
		//$("#corpus_header").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_sent_query",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_word").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		remember_query('word');
		$.ajax({
			url: "search_word",
			data: $("#search_main").serialize(),
			type: "GET",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_html,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
		
	$("#search_lemma").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		remember_query('lemma');
		$.ajax({
			url: "search_lemma",
			data: $("#search_main").serialize(),
			type: "GET",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_html,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
/*
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
*/

	$("#search_word_json").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_word_json",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_lemma_json").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_lemma_json",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
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
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
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
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	$("#search_lemma_query").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_lemma_query",
			data: $("#search_main").serialize(),
			type: "GET",
			dataType : "json",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
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
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('display', 'none');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	load_additional_word_fields();
	assign_input_events();
	assign_show_hide();
	search_if_query();
});

function start_progress_bar() {
	// progressHtml = '<img src="static/img/search_in_progress.gif" style="visibility: hidden;" id="progress_gif" /><br>'
	// progressHtml += '<p id="seconds_elapsed" style="visibility: hidden;">0</p>'
	$('#search_results').html("");
	$('#search_results').addClass('in_progress');
	continue_progress_bar();
}

function continue_progress_bar() {
	setTimeout(function () {
		if ($('#search_results').hasClass('in_progress')) {
			secElapsed = parseInt($('#seconds_elapsed').html().replace(/[^0-9]/g, '')) + 1;
			if (secElapsed > 0) {
				$('#seconds_elapsed').html(secElapsed);
				$('.progress-bar').css('width', ((max_request_time - secElapsed) / max_request_time * 100) + '%');
				$('.progress-bar').attr('aria-valuenow', max_request_time - secElapsed);
				$('#progress_bar_seconds').html(max_request_time - secElapsed);
				if (secElapsed == 2) {
					hide_player();
					hide_img();
					hide_query_panel();
					$('.progress').css('display', 'block');
				}
				else if (secElapsed == 3) {
					$('#progress_gif').css('display', 'block');
				}
			}
			continue_progress_bar();
		}
    }, 1000)
}

function stop_progress_bar() {
	$('#progress_gif').css('display', 'none');
	$('#search_results').removeClass('in_progress');
	$('.progress-bar').attr('aria-valuenow', max_request_time);
	$('#seconds_elapsed').html("0");
}

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

function load_glossed_sentence(n_sent) {
	var glossedText = '';
	$.ajax({
		async: false,
		url: "get_glossed_sentence/" + n_sent,
		type: "GET",
		success: function(result) {
			$('#glossed_copy_textarea').val(result);
		},
//		success: print_json,
		error: function(errorThrown) {
			alert( JSON.stringify(errorThrown) );
		}
	});
	return glossedText;
}

function load_additional_word_fields() {
	$.ajax({
		url: "get_word_fields",
		type: "GET",
		success: function(result) {
			$("div.add_word_fields").html(result);
			change_tier({'target': $('#lang1')});
			assign_input_events();
		},
		error: function(errorThrown) {
			alert( JSON.stringify(errorThrown) );
		}
	});
}

function hide_query_panel() {
    $("#hide_query_button").show();
    $("#greeting").hide();
	if ($("#hide_query_icon").hasClass('bi-arrow-bar-up')) {
		$("#hide_query_button").click();
	}
	$('#search_div').removeClass('centered');
}

function show_query_panel() {
	if ($(".img-swap").hasClass('on')) {
		$(".img-swap").click();
	}
}

function get_sentences() {
	get_sentences_page(-1);
}

function get_sentences_page(page) {
	if (page < 0) {
		remember_query('sentence');
		$.ajax({
			url: "search_sent",
			data: $("#search_main").serialize(),
			type: "GET",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
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
	$(".word_plus").unbind('click');
	$(".word_minus").unbind('click');
	$(".word_expand").unbind('click');
	$(".add_rel").unbind('click');
	$(".gram_selector_link").unbind('click');
	$("#search_doc").unbind('click');
	//$("neg_query_checkbox").unbind('change');
	$(".neg_query").unbind('click');
	$("#show_help").unbind('click');
	$("#show_dictionary").unbind('click');
	$("#enable_virtual_keyboard").unbind('click');
	$("#show_settings").unbind('click');
	$("#show_history").unbind('click');
	$("#cite_corpus").unbind('click');
	$("#show_word_stat").unbind('click');
	$("a.locale").unbind('click');
	$(".search_input").unbind('keydown');
	$("#viewing_mode").unbind('change');
	$('#share_query').unbind('click');
	$('#load_query').unbind('click');
	$('#query_load_ok').unbind('click');
	$('#display_settings_ok').unbind('click');
	$('.toggle_glossed_layer').unbind('click');
	$(".tier_select").unbind('change');
	$(".word_plus").click(add_word_inputs);
	$(".word_minus").click(del_word_inputs);
	$(".word_expand").click(expand_word_input);
	$(".add_rel").click(add_word_relations);
	$(".gram_selector_link").click(choose_tags);
	$("#search_doc").click(select_subcorpus);
	//$("neg_query_checkbox").change(negative_query);
	$(".neg_query").click(negative_query_span);
	$("#show_help").click(show_help);
	$("#show_dictionary").click(show_dictionary);
	$("#enable_virtual_keyboard").click(toggle_keyboards);
	$("#show_settings").click(show_settings);
	$("#show_history").click(show_history);
	$("#cite_corpus").click(show_citation);
	$("#show_word_stat").click(show_word_stats);
	$("a.locale").click(change_locale);
	$(".search_input").on("keydown", search_if_enter);
	$("#viewing_mode").change(toggle_interlinear);
	$('#share_query').click(share_query);
	$('#load_query').click(show_load_query);
	$('#query_load_ok').click(load_query);
	$('#display_settings_ok').click(hide_settings);
	$('.toggle_glossed_layer').click(toggle_glossed_layer);
	$(".tier_select").change(change_tier);
	assign_tooltips();
	initialize_keyboards();
	assign_autocomplete();
}

function assign_autocomplete() {
	$(".word_autocomplete").each(function () {
		let wordNum = $(this).attr('id').replace(/^.*[^0-9]/g, '');
		let field = $(this).attr('id').replace(/[0-9]*$/g, '');
		let curTier = $('#lang' + wordNum.toString() + ' option:selected').val();
		$(this).autocomplete({
			serviceUrl: 'autocomplete_word/' + curTier + '/' + field,
			minChars: 2,
			width: 260,
			orientation: "auto",
			appendTo: $(this).parent()
		});
	});
}

function assign_show_hide() {
    $("#hide_query_button").unbind('click');
	$("#hide_query_button").click(function(e){
		e.preventDefault();
		var $this=$(this),
				rel=$this.attr("rel"),
				el=$(".query_slide"),
				wrapper=$("#search_div"),
				dur=700;
		switch(rel){
			case "toggle-query_slide":
				if(!el.is(":animated")){
					iconSwap = $('#hide_query_icon');
					iconSwap.toggleClass('bi-arrow-bar-down');
					iconSwap.toggleClass('bi-arrow-bar-up');
					$('#hide_query_caption').toggle();
					wrapper.removeClass("transitions");
					el.slideToggle(dur,function(){wrapper.addClass("transitions");});
				}
				break;
		}
	});
}

function negative_query(e, thisSpan) {
	var word_div = $(thisSpan).parent().parent();
	var word_r_div = $(thisSpan).parent();
	word_div.toggleClass('negated');
	word_r_div.toggleClass('negated');
}

function negative_query_span(e) {
	var cx_neg = $(this).parent().find('.neg_query_checkbox');
	cx_neg.prop('checked', !cx_neg.prop('checked'));
	negative_query(e, this);
}

function add_word_inputs(e) {
	hide_tooltips();
	var new_word_num = parseInt($("#n_words").attr('value'));
	if (new_word_num <= 0) { return; }
	new_word_num += 1;
	word_div_html = '<div class="word_search" id="wsearch_' + new_word_num + '">\n' + $('#first_word').html();
	word_div_html = word_div_html.replace(/1/g, new_word_num)
	word_div_html = word_div_html.replace('<a class="add_minus_stub">', '<a class="word_minus bi bi-dash-circle-fill" data-nword="' + new_word_num + '" data-tooltip="tooltip" data-placement="right" title="' + removeWordCaption + '"></a><br>');
	word_div_html = word_div_html.replace('<a class="add_distance_stub">', '<a class="add_rel bi bi-arrows-angle-expand" data-nword="' + new_word_num + '" data-nrels="0" data-tooltip="tooltip" data-placement="right" title="' + addDistCaption + '"></a><br>');
	word_div_html += '</div>';
	word_div = $.parseHTML(word_div_html);
	$("div.words_search").append(word_div);
	$(word_div).removeClass('negated');
	$(word_div).find('.word_search_r').removeClass('negated');
	$(word_div).find('.autocomplete-suggestions').remove();
	$("#n_words").attr('value', new_word_num);
	$('#search_div').removeClass('centered');
	assign_input_events();
}

function del_word_inputs(e) {
	var word_num = parseInt($(e.target).attr('data-nword'));
	if (word_num <= 0) { return; }
	var n_words = parseInt($("#n_words").attr('value')) - 1;
	$("#n_words").attr('value', n_words);
	$('#wsearch_' + word_num).remove();
	for (i = word_num + 1; i <= n_words + 1; i++) {
		$('#wsearch_' + i).html($('#wsearch_' + i).html().replace(new RegExp(i.toString(), 'g'), i - 1));
		$('#wsearch_' + i).attr('id', 'wsearch_' + (i - 1));
	}
	assign_input_events();
	hide_tooltips();
}

function expand_word_input(e) {
	$('#search_div').removeClass('centered');
	var div_extra_fields = $(e.target).parent().parent().find('.add_word_fields');
	div_extra_fields.finish();
	if (div_extra_fields.css('max-height') == '0px') {
		div_extra_fields.css('max-height', '600px');
		div_extra_fields.css('height', 'initial');
		div_extra_fields.css('visibility', 'visible');
		$(e.target).find('.tooltip_prompt').html(lessFieldsCaption);
	}
	else if (div_extra_fields.css('max-height') == '600px') {
		div_extra_fields.css('max-height', '0px');
		div_extra_fields.css('height', '0px');
		div_extra_fields.css('visibility', 'hidden');
		$(e.target).find('.tooltip_prompt').html(moreFieldsCaption);
	}
	else {
		return;
	}
	$(e.target).toggleClass('bi-box-arrow-down');
	$(e.target).toggleClass('bi-box-arrow-up');
}

function add_word_relations(e) {
	var word_num = parseInt($(e.target).attr('data-nword'));
	if (word_num <= 0) { return; }
	var nrels = parseInt($(e.target).attr('data-nrels'));
	$(e.target).attr('data-nrels', nrels + 1);
	word_rel_html = '<div class="word_rel">' + distToWordCaption + '<input type="number" class="search_input distance_input" name="word_rel_' + word_num + '_' + nrels + '" id="word_rel_' + word_num + '_' + nrels + '" value="' + (word_num - 1).toString() + '"><br>';
	word_rel_html += fromCaption + '<input type="number" class="search_input" name="word_dist_from_' + word_num + '_' + nrels + '" id="word_dist_from_' + word_num + '_' + nrels + '" value="1"><br>';
	word_rel_html += toCaption + '<input type="number" class="search_input" name="word_dist_to_' + word_num + '_' + nrels + '" id="word_dist_to_' + word_num + '_' + nrels + '" value="1"> ';
	word_rel_html += '</div>';
	word_rel_div = $.parseHTML(word_rel_html);
	$("#wsearch_" + word_num).find(".word_search_l").append(word_rel_div);
}

function choose_tags(e) {
	var field_type = $(e.target).attr('data-field');
	var word_num = parseInt($(e.target).attr('data-nword'));
	var field = field_type + word_num.toString();
	var lang = $('#lang' + word_num.toString() + ' option:selected').val();
	$('#gram_selector').attr('data-field', field);
	if (field_type == 'gr') {
		$('#gram_sel_header').html(selectGrammTagsCaption);
		$.ajax({
			url: "get_gramm_selector/" + lang,
			type: "GET",
			success: function(result) {
				gramm_gloss_selector_loaded(result);
				$('#gram_selector').modal('show');
				$('#gramm_gloss_query_viewer').text($('#' + field).val());
			},
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	else if (field_type == 'gloss_index') {
		$('#gram_sel_header').html(selectGlossCaption);
		$.ajax({
			url: "get_gloss_selector/" + lang,
			type: "GET",
			success: function(result) {
				if (result.length <= 0) {
					alert('No glosses are available for this language.');
					return;
				}
				gramm_gloss_selector_loaded(result);
				$('#gram_selector').modal('show');
				$('#gramm_gloss_query_viewer').text($('#' + field).val());
			},
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	else {
		// Additional word-level fields
		$('#gram_sel_header').html(selectGrammTagsCaption);
		$.ajax({
			url: "get_add_field_selector/" + field_type,
			type: "GET",
			success: function(result) {
				gramm_gloss_selector_loaded(result);
				$('#gram_selector').modal('show');
				$('#gramm_gloss_query_viewer').text($('#' + field).val());
			},
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
}

function gramm_gloss_selector_loaded(result) {
	$("#gram_sel_body").html(result);
	$("#gramm_selector_ok").unbind('click');
	$("#gramm_selector_ok").click(gram_selector_ok);
}

function assign_dictionary_events(){
	$(".dictionary_lemma").unbind("click");
	$(".dictionary_lemma").click(input_lemma);
}

function input_lemma(e) {
	$('#wf1').val("");
	$('#lex1').val($(e.target).html());
	$('#gr1').val($(e.target).next().html().replace(" ", ""));
}

function gram_selector_ok(e) {
	var field = '#' + $('#gram_selector').attr('data-field');
	$(field).val($('#gramm_gloss_query_viewer').text());
	$('#gram_selector').modal('toggle');
}

function change_locale(e) {
	var new_locale = $(e.target).text().toLowerCase();
	$.ajax({
		url: "set_locale/" + new_locale,
		success: function (result) { location.reload(); }
	});
}

function search_if_enter(e) {
	if (e.keyCode == 13) {
       $('#search_sent').click();        
    }
    else {
    	// Autoswitch tiers
    	let wordNum = $(e.target).attr('id').replace(/^.*[^0-9]/g, '');
    	let field = $(e.target).attr('id').replace(/[0-9]*$/g, '');
    	if (field in autoSwitchTiers) {
    		let langSwitch = autoSwitchTiers[field];
    		let curTier = $('#lang' + wordNum.toString() + ' option:selected').val();
    		if (curTier != langSwitch) {
    			$('#lang' + wordNum.toString()).val(langSwitch).change();
    		}
    	}
    }
}

async function search_if_query() {
	if ($('#query_to_load').val().length > 1) {
		await load_query();
		$('#search_sent').click();
	}
}

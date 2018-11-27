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
				$('.progress').css('visibility', 'hidden');
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
				$('.progress').css('visibility', 'hidden');
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
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_html,
			error: function(errorThrown) {
				$('.progress').css('visibility', 'hidden');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
		
	$("#search_lemma").click(function() {
		//$("#query").html( $("#search_main").serialize() );
		$.ajax({
			url: "search_lemma",
			data: $("#search_main").serialize(),
			type: "GET",
			beforeSend: start_progress_bar,
			complete: stop_progress_bar,
			success: print_html,
			error: function(errorThrown) {
				$('.progress').css('visibility', 'hidden');
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
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('visibility', 'hidden');
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
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('visibility', 'hidden');
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
				$('.progress').css('visibility', 'hidden');
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
				$('.progress').css('visibility', 'hidden');
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
			success: print_json,
			error: function(errorThrown) {
				$('.progress').css('visibility', 'hidden');
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
				$('.progress').css('visibility', 'hidden');
				alert( JSON.stringify(errorThrown) );
			}
		});
	});
	
	load_additional_word_fields();
	assign_input_events();
	assign_show_hide();
});

function start_progress_bar() {
	progressHtml = '<img src="static/img/search_in_progress.gif" style="visibility: hidden;" id="progress_gif" /><br>'
	progressHtml += '<p id="seconds_elapsed" style="visibility: hidden;">0</p>'
	$('#res_p').html(progressHtml);
	$('#res_p').addClass('in_progress');
	continue_progress_bar();
}

function continue_progress_bar() {
	setTimeout(function () {
		if ($('#res_p').hasClass('in_progress')) {
			secElapsed = parseInt($('#seconds_elapsed').html().replace(/[^0-9]/g, '')) + 1;
			if (secElapsed > 0) {
				$('#seconds_elapsed').html(secElapsed);
				$('.progress-bar').css('width', ((max_request_time - secElapsed) / max_request_time * 100) + '%');
				$('.progress-bar').attr('aria-valuenow', max_request_time - secElapsed);
				$('#progress_bar_seconds').html(max_request_time - secElapsed);
				if (secElapsed == 2) {
					hide_player();
					hide_query_panel();
					$('.progress').css('visibility', 'visible');
				}
				else if (secElapsed == 3) {
					$('#progress_gif').css('visibility', 'visible');
				}
			}
			continue_progress_bar();
		}
    }, 1000)
}

function stop_progress_bar() {
	$('#res_p').removeClass('in_progress');
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
		},
		error: function(errorThrown) {
			alert( JSON.stringify(errorThrown) );
		}
	});
}

function hide_query_panel() {
	if (!$(".img-swap").hasClass('on')) {
		$(".img-swap").click();
	}
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
	$("span.word_plus").unbind('click');
	$("span.word_minus").unbind('click');
	$("span.word_expand").unbind('click');
	$("span.add_rel").unbind('click');
	$("span.gram_selector_link").unbind('click');
	$("#search_doc").unbind('click');
	//$("neg_query_checkbox").unbind('change');
	$("span.neg_query").unbind('click');
	$("#show_help").unbind('click');
	$("#show_word_stat").unbind('click');
	$("span.locale").unbind('click');
	$(".search_input").unbind('on');
	$("#viewing_mode").unbind('change');
	$('#share_query').unbind('click');
	$('#load_query').unbind('click');
	$('#query_load_ok').unbind('click');
	$('.toggle_glossed_layer').unbind('click');
	$("span.word_plus").click(add_word_inputs);
	$("span.word_minus").click(del_word_inputs);
	$("span.word_expand").click(expand_word_input);
	$("span.add_rel").click(add_word_relations);
	$("span.gram_selector_link").click(choose_grammar);
	$("#search_doc").click(select_subcorpus);
	//$("neg_query_checkbox").change(negative_query);
	$("span.neg_query").click(negative_query_span);
	$("#show_help").click(show_help);
	$("#show_word_stat").click(show_word_stats);
	$("span.locale").click(change_locale);
	$(".search_input").on("keydown", search_if_enter);
	$("#viewing_mode").change(toggle_interlinear);
	$('#share_query').click(share_query);
	$('#load_query').click(show_load_query);
	$('#query_load_ok').click(load_query);
	$('.toggle_glossed_layer').click(toggle_glossed_layer);
}

function assign_show_hide() {
	$(".show-hide a").click(function(e){
		e.preventDefault();
		var $this=$(this),
				rel=$this.attr("rel"),
				el=$(".slide"),
				wrapper=$("#search_div"),
				dur=700;
		switch(rel){
			case "toggle-slide":
				if(!el.is(":animated")){
					imgSwap = $('.img-swap');
					if (imgSwap.attr("class") == "img-swap") {
						imgSwap.attr('src', imgSwap.attr('src').replace("_up","_down"));
						$('#hide_query_caption').css('display', 'inline');
					} else {
						imgSwap.attr('src', imgSwap.attr('src').replace("_down","_up"));
						$('#hide_query_caption').css('display', 'none');
					}
					imgSwap.toggleClass("on");
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
	if (word_div.css("background-color") != "rgb(20, 20, 20)") {
		word_div.css({"background-color": "rgb(20, 20, 20)", "color": "#fff"});
		word_r_div.css({"background-color": "rgb(60, 50, 60)", "color": "#fff"});
	}
	else {
		word_div.css({"background-color": "#fff", "color": "black"});
		word_r_div.css({"background-color": "#e1e9ef", "color": "black"});
	}
}

function negative_query_span(e) {
	var cx_neg = $(this).parent().find('.neg_query_checkbox');
	cx_neg.prop('checked', !cx_neg.prop('checked'));
	negative_query(e, this);
}

function add_word_inputs(e) {
	var new_word_num = parseInt($("#n_words").attr('value'));
	if (new_word_num <= 0) { return; }
	new_word_num += 1;
	word_div_html = '<div class="word_search" id="wsearch_' + new_word_num + '">\n' + $('#first_word').html();
	word_div_html = word_div_html.replace(/1/g, new_word_num)
	word_div_html = word_div_html.replace('<span class="add_minus_stub">', '<span class="word_minus glyphicon glyphicon-minus-sign" data-nword="' + new_word_num + '"><span class="tooltip_prompt">' + removeWordCaption + '</span></span><br>');
	word_div_html = word_div_html.replace('<span class="add_distance_stub">', '<span class="add_rel glyphicon glyphicon-resize-full" data-nword="' + new_word_num + '" data-nrels="0"><span class="tooltip_prompt">' + addDistCaption + '</span></span><br>');
	word_div_html += '</div>';
	word_div = $.parseHTML(word_div_html);
	$("div.words_search").append(word_div);
	$(word_div).find('.word_search_r').css({"background-color": "#e1e9ef", "color": "black"});
	$("#n_words").attr('value', new_word_num);
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
}

function expand_word_input(e) {
	var div_extra_fields = $(e.target).parent().parent().find('.add_word_fields');
	div_extra_fields.finish();
	if (div_extra_fields.css('max-height') == '0px') {
		div_extra_fields.css('max-height', '300px');
		div_extra_fields.css('height', 'initial');
		div_extra_fields.css('visibility', 'visible');
		$(e.target).find('.tooltip_prompt').html(lessFieldsCaption);
	}
	else if (div_extra_fields.css('max-height') == '300px') {
		div_extra_fields.css('max-height', '0px');
		div_extra_fields.css('height', '0px');
		div_extra_fields.css('visibility', 'hidden');
		$(e.target).find('.tooltip_prompt').html(moreFieldsCaption);
	}
	else {
		return;
	}
	$(e.target).toggleClass('glyphicon-chevron-down');
	$(e.target).toggleClass('glyphicon-chevron-up');
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

function choose_grammar(e) {
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
				gramm_selector_loaded(result);
				$('#gram_selector').modal('show');
				$('#gramm_query_viewer').text($('#' + field).val());
			},
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	else if (field_type == 'gloss') {
		$('#gram_sel_header').html(selectGlossCaption);
		$.ajax({
			url: "get_gloss_selector/" + lang,
			type: "GET",
			success: function(result) {
				if (result.length <= 0) {
					alert('No glosses are available for this language.');
					return;
				}
				gloss_selector_loaded(result);
				$('#gram_selector').modal('show');
			},
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
}

function select_subcorpus(e) {
	$('#subcorpus_selector').modal('show');
}

function show_help(e) {
	$.ajax({
			url: "help_dialogue",
			type: "GET",
			success: function(result) {
				$('#help_dialogue_body').html(result);
				$('#help_dialogue').modal('show');
			},
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
}

function gramm_selector_loaded(result) {
	$("#gram_sel_body").html(result);
	$("#gramm_selector_ok").unbind('click');
	$("#gramm_selector_ok").click(gram_selector_ok);
	$("#gramm_selector_cancel").unbind('click');
	$("#gramm_selector_cancel").click(function() {$('#gram_selector').modal('toggle');});
}

function gloss_selector_loaded(result) {
	$("#gram_sel_body").html(result);
	$("#gloss_selector_ok").unbind('click');
	$("#gloss_selector_ok").click(gloss_selector_ok);
	$("#gloss_selector_cancel").unbind('click');
	$("#gloss_selector_cancel").click(function() {$('#gram_selector').modal('toggle');});
}

function gram_selector_ok(e) {
	var field = '#' + $('#gram_selector').attr('data-field');
	$(field).val($('#gramm_query_viewer').text());
	$('#gram_selector').modal('toggle');
}

function gloss_selector_ok(e) {
	var field = '#' + $('#gram_selector').attr('data-field');
	var gloss_divs = $('#sortable > div');
	var gloss_field_val = '';
	gloss_divs.each(function (index) {
		var t = $(this).contents().get(0).nodeValue.replace(/[\r\n\t ]/g, '');
		if (t.length > 0) {
			gloss_field_val += t + '-';
		}
	});
	gloss_field_val = gloss_field_val.replace(/^[* -]*|[* -]$/g, '');
	gloss_field_val = gloss_field_val.replace(/-?#-?/g, '#');
	gloss_field_val = gloss_field_val.replace(/(\*-)(\*-)+/g, '*-');
	$(field).val(gloss_field_val);
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
}

function toggle_glossed_layer(e) {
	classToToggle = ".popup_" + $(this).attr('data');
	if ($(this).is(':checked')) {
		$(classToToggle).css("display", "");
	}
	else {
		$(classToToggle).css("display", "none");
	}
}

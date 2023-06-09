function change_locale(e) {
	var new_locale = $(e.target).text().toLowerCase();
	$.ajax({
		url: "set_locale/" + new_locale,
		success: function (result) { location.reload(); }
	});
}

function assign_tooltips() {
	$("[data-tooltip=tooltip]").tooltip({
		trigger: 'hover manual',
		delay: { "show": 150, "hide": 0 }
	});	
}

function hide_tooltips() {
	$("[data-tooltip=tooltip]").tooltip('hide');
	$(".tooltip").hide();
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

function show_dictionary(e) {
	var lang = $('#lang1 option:selected').val();
	$.ajax({
			url: "dictionary/" + lang,
			type: "GET",
			success: function(result) {
				$('#dictionary_dialogue_body').html(result);
				$('#dictionary_dialogue').modal('show');
				assign_dictionary_events();
			},
			error: function(errorThrown) {
			}
		});
}

function toggle_keyboards(e) {
	// Switch virtual keyboards on or off
	$('#enable_virtual_keyboard').toggleClass('keyboards_on');
	initialize_keyboards();
}

function hide_settings(e) {
	$('#display_settings').modal('hide');
}

function show_settings(e) {
	$('#display_settings').modal('show');
}

function show_history(e) {
	$('#query_history').modal('show');
}

function show_citation(e) {
	$('#citation_dialogue').modal('show');
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

function highlight_word_spans(item, i) {
	if (item == "word" || item.includes('match') || !item.startsWith("w")) return;
	$('.' + item).addClass('w_highlighted');
}

function highlight_para_spans(item, i) {
	if (item == "para" || item.includes('match') || !item.startsWith("p")) return;
	$('.' + item).addClass('p_highlighted');
}

function highlight_cur_word(e) {
	var e_obj = $(e.currentTarget);
	targetClasses = e_obj.attr('class').split(' ');
	$('.w_highlighted').removeClass('w_highlighted');
	targetClasses.forEach(highlight_word_spans);
}

function assign_para_highlight() {
	$("span.para").unbind('hover');
	$("span.para").unbind('mousemove');
	$('span.para').hover(function (e) {
		$('.p_highlighted').removeClass('p_highlighted');
		var targetClasses = $(this).attr('class').split(' ');
		targetClasses.forEach(highlight_para_spans);
	}, function () {
		$('.p_highlighted').removeClass('p_highlighted');
	});
}

function assign_sent_meta_popup() {
    $("span.sent_lang").unbind('hover');
	$("span.sent_lang").unbind('mousemove');
    $('span.sent_lang').hover(function (e) {
/*
        var sentMeta = $(this).find('.sentence_meta');
        if (sentMeta.html() != '') {
			sentMeta.show();
        }
*/
	}, function () {
		$('.sentence_meta').hide();
	});
}

function assign_gram_popup() {
	var moveLeft = 20;
	var moveDown = 10;
	$("span.word, span.word_in_table").unbind('hover');
	$("span.word, span.word_in_table").unbind('mousemove');
	$('.word, .word_in_table').hover(function (e) {
		$('#analysis').replaceWith('<div id="analysis">' + $("<textarea/>").html(($(this).attr("data-ana"))).text() + '</div>');
		anaWidth = $('#analysis').width();
		anaHeight = $('#analysis').height();
		$('#analysis').css('left', $(document).innerWidth() - anaWidth - 30);
		$('#analysis').css('top', $(document).innerHeight() - anaHeight - 30);
		$('#analysis').show();
        if ($('.sentence_meta').length > 0) {
			var prevEl = $(this).prev();
			while (prevEl.length > 0) {
				if (prevEl.hasClass('sentence_meta')) {
					break;
				}
				prevEl = prevEl.prev();
			}
			if (prevEl.hasClass('sentence_meta')) {
				$('.sentence_meta').hide();
				prevEl.show();
			}
        }
	}, function () {
		$('#analysis').hide();
        $('.sentence_meta').hide();
	});
	$('.word, .word_in_table').mousemove(function (e) {
		anaWidth = $('#analysis').width();
		anaHeight = $('#analysis').height();
		if (e.pageX + moveLeft + anaWidth + 30 < $(document).innerWidth()) {
			$('#analysis').css('left', e.pageX + moveLeft);
			$('#analysis').width(anaWidth);
		}
		else {
			$('#analysis').css('left', $(document).innerWidth() - anaWidth - 30);
			$('#analysis').width(anaWidth);
		}
		if (e.pageY + moveDown + anaHeight + 30 < $(document).innerHeight()) {
			$('#analysis').css('top', e.pageY + moveDown);
			$('#analysis').height(anaHeight);
		}
		else {
			$('#analysis').css('top', $(document).innerHeight() - anaHeight - 30);
			$('#analysis').height(anaHeight);
		}
	});
}

function toggle_interlinear() {
	if (searchType != 'sentences') {
		return;
	}
	if ($('#viewing_mode option:selected').attr('value') == 'glossed')
	{
		$('span.word, span.word_in_table').each(function (index) {
			if ($(this).find('.ana_interlinear').length > 0) {
				return;
			}
			$(this).css("display", "inline-table");
			var data_ana = $(this).attr('data-ana');
			if (data_ana == null || data_ana.length <= 0) {
				return;
			}
			data_ana = data_ana.replace('class="popup_word"', 'class="popup_word ana_interlinear"');
			data_ana = data_ana.replace(/<span class="popup_(key|wf)">.*?<\/span>/g, '');
			data_ana = data_ana.replace('class="popup_value"', 'class="popup_value_small"');
			data_ana = data_ana.replace(/(class="popup_value">[^<>]{38,100}?)[ ,;][^<>]{3,}/g, '$1...');
			if (/<div class="popup_word[^<>]*>\s*<\/div>\s*/.test(data_ana)) {
				return;
			}
			$(this).html($(this).html() + '<br>' + data_ana);
		});
	}
	else {
		$('span.word, span.word_in_table').each(function (index) {
			$(this).css("display", "inline-block");
			$(this).html($(this).html().replace(/<br>/, ''));
		});
		$('.ana_interlinear').remove();
	}
}

function html_decode(input){
  var e = document.createElement('textarea');
  e.innerHTML = input;
  return e.childNodes.length === 0 ? "" : e.childNodes[0].nodeValue;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

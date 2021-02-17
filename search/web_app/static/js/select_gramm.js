$(function() {
	$('.gloss_choice_panel').scrollLeft();

	function assign_gramm_events() {
		$('.switchable_gramm').unbind('click');
		$('.switchable_gramm').click(toggle_gramm);
	}

	function toggle_gramm(e) {
		$(this).toggleClass('gramm_enabled');
		var new_formula = build_formula();
		$('#gramm_gloss_query_viewer').text(new_formula);
	}
	
	function parse_initial_value() {
		var rx_grammtags = /[^ ,()|*+~?]+/g;
		let matches = Array.from($('#gramm_gloss_query_viewer').text().matchAll(rx_grammtags));
        var grammtags = [];
        matches.forEach(function (m) {
            grammtags.push(m[0]);
        })
		$('.switchable_gramm').each(function (index) {
			if (grammtags.includes($(this).attr('data-grammtag')) && !$(this).hasClass('gramm_enabled')) {
				$(this).toggleClass('gramm_enabled');
			}
		});
		var new_formula = build_formula();
		$('#gramm_gloss_query_viewer').text(new_formula);
	}

	function build_formula() {
		var dict_categories = new Object();
		$('.switchable_gramm').each(function (index) {
			if ($(this).hasClass('gramm_enabled')) {
				var cat = $(this).attr('data-cat');
				var val = $(this).attr('data-grammtag');
				if (!(cat in dict_categories)) {
					dict_categories[cat] = [];
				}
				dict_categories[cat].push(val);
			}
		});
		var formula = '';
		for (var cat in dict_categories) {
			var formulaPart = '';
			for (i = 0; i < dict_categories[cat].length; i++) {
				formulaPart += dict_categories[cat][i];
				if (i < dict_categories[cat].length - 1) {
					formulaPart += '|';
				}
			}
			if (dict_categories[cat].length > 1) {
				formulaPart = '(' + formulaPart + ')';
			}
			formula += formulaPart + ',';
		}
		formula = formula.replace(/,$/, '');
		return formula;
	}

	assign_gramm_events();
	parse_initial_value();
});

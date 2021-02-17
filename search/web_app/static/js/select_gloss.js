$(function() {
    function assign_gloss_events() {
        $('.switchable_gramm').unbind('click');
        $('.switchable_gramm').click(toggle_gloss);
    }

    function toggle_gloss(e) {
        var gloss = $(this).attr('data-gloss');
        var add_gloss = (($(this).hasClass('gramm_enabled')) ? false : true);
        $(this).toggleClass('gramm_enabled');
        var new_glosses = build_glosses(gloss, add_gloss);
        $('#gramm_gloss_query_viewer').text(new_glosses);
    }
    
    function parse_initial_value() {
        var rx_glosses = /[^ ,()|*+~#{}?-]+/g;
        let matches = Array.from($('#gramm_gloss_query_viewer').text().matchAll(rx_glosses));
        var glosses = [];
        matches.forEach(function (m) {
            glosses.push(m[0]);
        })
        $('.switchable_gramm').each(function (index) {
            if (glosses.includes($(this).attr('data-gloss')) && !$(this).hasClass('gramm_enabled')) {
                $(this).toggleClass('gramm_enabled');
            }
        });
    }

    function build_glosses(gloss, add_gloss) {
        var old_text = $('#gramm_gloss_query_viewer').text();
        if (add_gloss) {
            if (gloss.search("#") < 0) {
                return (old_text + '-' + gloss).replace(/^-|-$/g, '');
            }
            return (old_text + gloss).replace(/^-|-$/g, '');
        }
        else {
            if (gloss.search("#") < 0) {
                var gloss2remove = '^' + gloss + '-|-' + gloss + '-|-' + gloss + '$|^' + gloss + '$';
                var rx_gloss2remove = new RegExp(gloss2remove, 'g');
                return old_text.replace(rx_gloss2remove, '').replace(/^-|-$/g, '');
            }
            return old_text.replace(gloss, '').replace(/^-|-$/g, '');
        }
    }

    assign_gloss_events();
    parse_initial_value();
});
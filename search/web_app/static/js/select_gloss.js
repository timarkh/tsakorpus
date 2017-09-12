$(function() {
    $( "#sortable" ).sortable({
		over: function (event, ui) {
            remove_item = false;
        },
        out: function (event, ui) {
            remove_item = true;
        },
        beforeStop: function (event, ui) {
			var siblings = ui.item.siblings();
			var n_siblings = siblings.length;
			if (remove_item && n_siblings > 1) {
                ui.item.hide();
                ui.item.remove();
            }
        }
	});
    $( "#sortable" ).disableSelection();
	$( ".draggable" ).draggable({
      connectToSortable: "#sortable",
      helper: "clone",
      revert: "invalid"
    });
});
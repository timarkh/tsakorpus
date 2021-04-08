
function assign_corpus_setup_buttons() {
	$(".add_row").unbind('click');
	$(".del_row").unbind('click');
	$(".add_col").unbind('click');
	$(".del_col").unbind('click');
	$(".add_row").click(add_row);
	$(".del_row").click(del_row);
	$(".add_col").click(add_col);
	$(".del_col").click(del_col);
}


function del_row(e) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevRow = curButtonRow.prev('.removable_row');
	prevRow.remove();
}


function del_col(e) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevCol = curButtonRow.prev('.removable_column');
	prevCol.remove();
}


function add_row(e) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevRow = curButtonRow.prev('.removable_row');
	var nextRowNum = 1;
	if (prevRow.length) {
		nextRowNum = parseInt(prevRow.attr('data-nrow')) + 1;
	}
	var curColNum = curButtonRow.parent().attr('data-ncol');
	var rowStub = curButtonRow.siblings('.row_stub');
	var newRow = $(rowStub.html().replaceAll('%COL_NUMBER%', curColNum).replaceAll('%ROW_NUMBER%', nextRowNum));
	curButtonRow.before(newRow);
	assign_corpus_setup_buttons();
}


function add_col(e) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevCol = curButtonRow.prev('.removable_column');
	var nextColNum = 1;
	if (prevCol.length) {
		nextColNum = parseInt(prevCol.attr('data-ncol')) + 1;
	}
	var colStub = curButtonRow.siblings('.column_stub');
	var newCol = $(colStub.html().replaceAll('%COL_NUMBER%', nextColNum));
	curButtonRow.before(newCol);
	assign_corpus_setup_buttons();
}

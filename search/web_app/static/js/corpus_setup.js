
function assign_corpus_setup_buttons() {
	$(".add_row_below").unbind('click');
	$(".add_row_above").unbind('click');
	$(".del_row").unbind('click');
	$(".add_col").unbind('click');
	$(".del_col").unbind('click');
	$(".add_field").unbind('click');
	$(".del_field").unbind('click');
	$("#save_changes").unbind('click');
	$(".add_row_below").click(add_row_below);
	$(".add_row_above").click(add_row_above);
	$(".del_row").click(del_row);
	$(".add_col").click(add_col);
	$(".del_col").click(del_col);
	$(".add_field").click(add_field);
	$(".del_field").click(del_field);
	$("#save_changes").click(save_changes);
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


function del_field(e) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevCol = curButtonRow.prev('.removable_metafield');
	prevCol.remove();
}

function add_row_below(e) {
	return add_row(e, true);
}

function add_row_above(e) {
	return add_row(e, false);
}

function add_row(e, below) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevRow = curButtonRow.prev('.removable_row');
	var nextRowNum = 1;
	if (prevRow.length) {
		nextRowNum = parseInt(prevRow.attr('data-nrow')) + 1;
	}
	var curColNum = curButtonRow.parent().attr('data-ncol');
	var curFieldNum = curButtonRow.parent().parent().attr('data-nfield');
	var rowStub = curButtonRow.siblings('.row_stub');
	var newRowHTML = rowStub.html().replaceAll('%COL_NUMBER%', curColNum).replaceAll('%ROW_NUMBER%', nextRowNum);
	if (typeof curFieldNum !== 'undefined' && curFieldNum !== false) {
		newRowHTML = newRowHTML.replaceAll('%FIELD_NUMBER%', curFieldNum);
	}
	var newRow = $(newRowHTML);
	if (below) {
		curButtonRow.before(newRow);
	}
	else {
		curButtonRow.siblings('.selection_table_header').after(newRow);
	}
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
	var curFieldNum = curButtonRow.parent().attr('data-nfield');
	var newColHTML = colStub.html().replaceAll('%COL_NUMBER%', nextColNum);
	if (typeof curFieldNum !== 'undefined' && curFieldNum !== false) {
		newColHTML = newColHTML.replaceAll('%FIELD_NUMBER%', curFieldNum);
	}
	var newCol = $(newColHTML);
	curButtonRow.before(newCol);
	assign_corpus_setup_buttons();
}


function add_field(e) {
	var curButtonRow = $(e.currentTarget).parent().parent();
	var prevField = curButtonRow.prev('.removable_metafield');
	var nextFieldNum = 1;
	if (prevField.length) {
		nextFieldNum = parseInt(prevField.attr('data-nfield')) + 1;
	}
	var fieldStub = curButtonRow.siblings('.metafield_stub');
	var newFieldHTML = fieldStub.html().replaceAll('%FIELD_NUMBER%', nextFieldNum);
	var newField = $(newFieldHTML);
	curButtonRow.before(newField);
	assign_corpus_setup_buttons();
}

function save_changes(e) {
	e.preventDefault();
	$.ajax({
		url: "config_update",
		data: $("#settings_form").serialize(),
		type: "POST",
		dataType: "json",
		success: changes_saved,
		error: function(errorThrown) {
			alert( JSON.stringify(errorThrown) );
		}
	});
}

function changes_saved(results) {
	$('#changes_saved').addClass('show');
	setTimeout(function () { $('#changes_saved').removeClass('show'); }, 1000);
}
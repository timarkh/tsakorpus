var subcorpus_x = null;
var subcorpus_y = null;
var subcorpus_gx = null;
var subcorpus_gy = null;
var subcorpus_xAxis = null;
var subcorpus_yAxis = null;
var subcorpus_chart = null;
var subcorpus_svg = null;
var subcorpus_bar = null;

	function assign_subcorpus_events() {
		$('.switchable_subcorpus_option').unbind('click');
		$('#subcorpus_selector_ok').unbind('click');
		$('#subcorpus_selector_clear').unbind('click');
		$('#subcorpus_stats_link').unbind('click');
		$('#select_meta_stat').unbind('change');
		$('#select_meta_lang').unbind('change');
		$('.switchable_subcorpus_option').click(toggle_subcorpus_option);
		$('#load_documents_link').click(load_subcorpus_documents);
		$('#subcorpus_selector_ok').click(close_subcorpus_selector);
		$('#subcorpus_selector_clear').click(clear_subcorpus);
		$('#subcorpus_stats_link').click(load_subcorpus_stats);
		$('#select_meta_stat').change(load_subcorpus_stats);
		$('#select_meta_lang').change(load_subcorpus_stats);
		$(".subcorpus_autocomplete").each(function () {
			$(this).autocomplete({
				serviceUrl: 'autocomplete_meta/' + this.id,
				minChars: 2,
				width: 260,
				orientation: "auto",
				appendTo: $(this).parent()
			});
		});
	}
	
	function assign_document_list_events() {
		$(".doc_toggle_chk").unbind('change');
		$(".doc_toggle_chk").change(toggle_doc_exclusion);
	}

	function toggle_doc_exclusion(e) {
		var docTR = $(e.currentTarget).parent().parent();
		docTR.toggleClass('context_off');
		docID = docTR.attr('id').substring(3);
		exclude_doc(docID);
	}
	
	function exclude_doc(docID) {
		if ($.inArray(docID, excludeDocs) > -1) {
			excludeDocs = jQuery.grep(excludeDocs, function (value) { return value != docID; });
		}
		else {
			excludeDocs.push(docID);
		}
		$.ajax({
			url: "toggle_doc/" + docID,
			dataType : "json",
			success: update_subcorpus_stats
		});
	}

	function toggle_subcorpus_option(e) {
		$(this).toggleClass('subcorpus_option_enabled');
		rebuild_subcorpus_queries();
	}
	
	function update_subcorpus_stats(data) {
		$('#subcorpus_ndocs').html(parseInt($('#subcorpus_ndocs').html()) + data.n_docs);
		$('#subcorpus_nwords').html(parseInt($('#subcorpus_nwords').html()) + data.n_words);
		$('#subcorpus_size_percent').html(parseFloat($('#subcorpus_size_percent').html()) + data.size_percent + '%');
	}

	function rebuild_subcorpus_queries() {
		var dict_fields = new Object();
		$('.switchable_subcorpus_option').each(function (index) {
			var field = $(this).attr('data-name');
			if (!(field in dict_fields)) {
				dict_fields[field] = [];
			}
			if ($(this).hasClass('subcorpus_option_enabled')) {
				var val = $(this).attr('data-value');
				dict_fields[field].push(val);
			}
		});
		for (var field in dict_fields) {
			var formula = '';
			for (i = 0; i < dict_fields[field].length; i++) {
				formula += dict_fields[field][i];
				if (i < dict_fields[field].length - 1) {
					formula += '|';
				}
			}
			$('#' + field).val(formula);
		}
	}
	
	function load_subcorpus_stats(e) {
		clear_subcorpus_stats_plot();
		var metaField = $('#select_meta_stat option:selected').val();
		var lang = $('#select_meta_lang option:selected').attr("value");
		if (metaField == '') {
			return;
		}
		var url = "doc_stats/" + metaField;
		if (lang != "all") {
			url += "/" + lang;
		}
		$.ajax({
			url: url,
			data: $("#search_main").serialize(),
			type: "GET",
			success: display_subcorpus_stats_plot,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function clear_subcorpus_stats_plot(results) {
		$('#subcorpus_stats_plot').html('<svg class="subcorpus_meta_plot"></svg>');
		clear_subcorpus_table();
		$('#subcorpus_stats_nothing_found').hide();
		$('#subcorpus_stats_wait').show();
	}

	function clear_subcorpus_table() {
	    $('#subcorpus_stats_table tbody').html("");
	}

	function fill_subcorpus_table(results) {
	    var tableBody = $('#subcorpus_stats_table tbody');
	    clear_subcorpus_table();
	    if (results == null) {
			return;
		}
		for (iRes = 0; iRes < results.length; iRes++) {
			v = results[iRes];
			var rowID = "subcorpus_stats_tr_" + iRes;
			tr = "<td>" + Math.round(v.n_words) + "</td>"
			tr += "<td>" + Math.round(v.n_docs) + "</td>"
			trExisting = $('#' + rowID);
			if (trExisting.length <= 0) {
				tr = "<tr id=\"" + rowID + "\"><td>" + v.name + "</td>" + tr + "</tr>";
				tableBody.html(tableBody.html() + tr);
			}
			else {
				trExisting.html(trExisting.html() + tr);
			}
		}
	}
	
	function resize_subcorpus_svg(margin, maxHeight) {
	    var viewBoxX = 600;
	    $(".subcorpus_meta_plot").css("min-width", vw(50));
	    try {
            var viewBoxY = $(".subcorpus_meta_plot>g")[0].getBBox()["height"];
            $(".subcorpus_meta_plot").attr("viewBox", "0 0 " + viewBoxX + " " + (40 + viewBoxY));
            $(".subcorpus_meta_plot").css("min-height", Math.max(300, viewBoxY / maxHeight));
        }
        catch (e) {
		    setTimeout(function() {
		        var viewBoxY = $(".subcorpus_meta_plot>g")[0].getBBox()["height"];
                $(".subcorpus_meta_plot").attr("viewBox", "0 0 " + viewBoxX + " " + (40 + viewBoxY));
                $(".subcorpus_meta_plot").css("min-height", Math.max(300, viewBoxY / maxHeight));
		    }, 500);
		}
		$(".subcorpus_meta_plot>g").attr("transform", "translate(50," + margin["top"] + ")");
/*
		try {
		    //var yAxisWidth = document.getElementById("subcorpus_y_axis").getBBox()["width"];
			var yAxisWidth = $('.bar').first().position().left;
		    $(".subcorpus_meta_plot>g").attr("transform", "translate(" + yAxisWidth + "," + margin["top"] + ")");
		}
		catch (e) {
		    setTimeout(function() {
		        //var yAxisWidth = document.getElementById("subcorpus_y_axis").getBBox()["width"];
				var yAxisWidth = $('.bar').first().position().left;
				$(".subcorpus_meta_plot>g").attr("transform", "translate(" + yAxisWidth + "," + margin["top"] + ")");
		    }, 500);
		}
*/
	}

	function subcorpus_bar_title(v) {
	    return v.n_words + " (" + v.n_docs + ")";
	}

    function make_subcorpus_y_gridlines() {
        return d3.axisLeft(subcorpus_y)
            .ticks(5)
    }

	function display_subcorpus_stats_plot(results) {
		$('#subcorpus_stats_wait').fadeOut();

		if (results == null) {
			$('#subcorpus_stats_nothing_found').show();
			return;
		}
		var plotObj = $('#subcorpus_stats_plot');
		var nResults = results.length;
		if (nResults <= 0 || results[0].length <= 0) {
			$('#subcorpus_stats_nothing_found').show();
			return;
		}
		fill_subcorpus_table(results);
		var maxHeight = d3.max(results, function(v) { return v.n_words; });
		var divisor = 1;
		var sfx = "";
		if (maxHeight > 2000000) {
			divisor = 1000000;
			sfx = "M";
		}
		else if (maxHeight > 2000) {
			divisor = 1000;
			sfx = "K";
		}
		
		subcorpus_svg = d3.create("svg");
      	plotObj.append(subcorpus_svg);
      	plotObj.find('svg').addClass('subcorpus_meta_plot').attr("viewBox", "0 0 600 350");

		var barWidth = 20;
		var maxBars = 25;
		var nBars = nResults;
		if (nBars >= maxBars) {
			nBars = maxBars;
			$('#subcorpus_stats_max_bars').show();
		}
		else {
		    $('#subcorpus_stats_max_bars').hide();
		}
		var margin = {"top": 20, "right": 30, "bottom": 30, "left": 40};
		
	    subcorpus_x = d3.scaleBand()
            .rangeRound([0, barWidth * nBars], .1)
		    .paddingInner(0.1);

		subcorpus_y = d3.scaleLinear()
			.range([200, 0]);

		subcorpus_xAxis = d3.axisBottom().scale(subcorpus_x);
		subcorpus_yAxis = d3.axisLeft().scale(subcorpus_y).tickFormat(function (d) { return d + sfx; });
		/*
		var chart = d3.select(".subcorpus_meta_plot")
			.attr("width", barWidth * nBars + margin.left + margin.right)
			.attr("height", 320 + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		*/
		subcorpus_chart = d3.select(".subcorpus_meta_plot").append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		subcorpus_x.domain(results.map(function(v) { return v.name; }));
		subcorpus_y.domain([0, maxHeight / divisor]);
		
		subcorpus_gx = subcorpus_chart.append("g")
		    .attr("class", "x axis")
		    .attr("transform", "translate(0,200)")
		    .call(subcorpus_xAxis);
		subcorpus_gx.selectAll("text")
            .style("text-anchor", "start")
            .attr("dx", "10px")
            .attr("dy", "-5px")
            .attr("transform", "rotate(90)");
			
	    subcorpus_gy = subcorpus_chart.append("g")
		    .attr("class", "y axis")
		    .attr("id", "subcorpus_y_axis")
		    .call(subcorpus_yAxis);
		subcorpus_gy.append("g")
          .attr("class", "grid")
          .call(make_subcorpus_y_gridlines()
              .tickSize(-500)
              .tickFormat("")
          );
		/*
		chart.selectAll(".bar")
		    .data(results)
		  .enter().append("rect")
		    .attr("class", "bar")
		    .attr("x", function(v) { return x(v.name); })
			.attr("width", x.bandwidth())
		    .attr("y", function(v) { return y(v.n_words / divisor); })
		    .attr("height", function(v) { return 200 - y(v.n_words / divisor); });
		*/
		var barClass = "bar bar_default"
		subcorpus_bar = subcorpus_chart.selectAll(".bar_new")
			.data(results)
		  .enter().append("rect")
			.attr("class", "bar bar_subcorpus")
			.attr("title", subcorpus_bar_title)
			.attr("x", v => subcorpus_x(v.name))
			.attr("width", subcorpus_x.bandwidth())
			.attr("y", 200)
			.attr("height", 0)
			.transition().duration(1200)
			.attr("y", v => subcorpus_y(v.n_words / divisor))
			.attr("height", v => 200 - subcorpus_y(v.n_words / divisor));
			
		// chart.attr("height", 320 + margin.top + margin.bottom);
		setTimeout(function (){
            $('.bar').each(function () {
                $(this).html("<title>" + $(this).attr("title") + "</title>")
            });
        }, 1);
		setTimeout(function() {resize_subcorpus_svg(margin, maxHeight);}, 300);
	}
	
	function load_subcorpus_documents(e) {
		$.ajax({
			url: "search_doc",
			data: $("#search_main").serialize(),
			type: "GET",
			success: print_document_list,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function print_document_list(results) {
		$('#subcorpus_documents').html(results);
		assign_word_events();
		assign_document_list_events();
		make_sortable();
	}
	
	function close_subcorpus_selector() {
		$('.nav-tabs a[href="#select_subcorpus_parameters"]').tab('show');
		$('#subcorpus_selector').modal('hide');
	}
	
	function clear_subcorpus() {
		$('.switchable_subcorpus_option').each(function (index) {
			$(this).removeClass('subcorpus_option_enabled');
		});
		$('.subcorpus_input').each(function (index) {
			$(this).val('');
		});
		excludeDocs = [];
		$.ajax({
			url: "clear_subcorpus",
			data: $("#search_main").serialize(),
			type: "GET",
			success: close_subcorpus_selector,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}

	assign_subcorpus_events();


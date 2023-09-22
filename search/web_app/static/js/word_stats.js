var lastFreqData = null;
var margin = {"top": 20, "right": 30, "bottom": 30, "left": 80};
var x = null;
var y = null;
var gx = null;
var gy = null;
var xAxis = null;
var yAxis = null;
var chart = null;
var svg = null;
var bar = null;
var data = null;

function vw(v) {
    var w = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
    return (v * w) / 100;
}

$(function() {
	function assign_word_stats_events() {
		$('#select_meta_word_stat').unbind('change');
		$('#select_meta_query_type').unbind('change');
		$('#select_freq_stat_type').unbind('change');
		$('#select_x_axis_scale').unbind('change');
		$('#select_max_y').unbind('change');
		$('#word_stats_ok').unbind('click');
		$('#button_close_word_stats').unbind('click');
		$('#load_word_meta_stats').unbind('click');
		$('#load_word_freq_stats').unbind('click');
		$('#select_meta_word_stat').change(load_word_stats);
		$('#select_meta_query_type').change(load_word_stats);
		$('#select_freq_stat_type').change(load_freq_stats);
		$('#select_x_axis_scale').change(function () {display_word_freq_stats_plot(lastFreqData);});
		$('#select_max_y').change(function () {display_word_freq_stats_plot(lastFreqData);});
		$('#word_stats_ok').click(close_word_stats);
		$('#button_close_word_stats').click(close_word_stats);
		$('#load_word_meta_stats').click(load_word_stats);
		$('#load_word_freq_stats').click(load_freq_stats);
	}

	function assign_word_stats_table_events() {
	    $('.th_query_word').unbind('hover');
	    $('.th_query_word').hover(highlight_word, clear_word_highlight);
	}

	function assign_plot_circle_events(chart) {
	    chart.selectAll(".plot_circle")
		    .on('mouseover', function (d, i) {
                d3.select(this).transition()
                .duration('300')
                .attr('r', '7');
            })
            .on('mouseout', function (d, i) {
                d3.select(this).transition()
                .duration('300')
                .attr('r', '3.5');
            });
	}

	function close_word_stats() {
		$('#word_stats').modal('toggle');
		$('#w_id1').val('');
	}
	
	function clear_word_stats_plots(results) {
		$('#word_stats_plot').html('<svg></svg>');
		$('#word_freq_rank_stats_plot').html('<svg></svg>');
		$('#word_stats_nothing_found').hide();
		$('#word_stats_wait').show();
	}

	function highlight_word() {
	    var nWord = $(this).attr("data-nword");
	    $(".bar").addClass("almost_invisible");
	    $(".bar_w" + nWord).removeClass("almost_invisible").addClass("opaque");
	    $(".conf_int").addClass("almost_invisible");
	    $(".conf_int_w" + nWord).removeClass("almost_invisible").addClass("opaque");
	    $(".plot_line").addClass("almost_invisible");
	    $(".plot_line_w" + nWord).removeClass("almost_invisible").addClass("opaque");
	    $(".plot_circle").addClass("almost_invisible");
	    $(".plot_circle_w" + nWord).removeClass("almost_invisible").addClass("opaque");
	}

	function clear_word_highlight() {
	    var nWord = $(this).attr("data-nword");
	    $(".bar").removeClass("almost_invisible").removeClass("opaque");
	    $(".conf_int").removeClass("almost_invisible").removeClass("opaque");
	    $(".plot_line").removeClass("almost_invisible").removeClass("opaque");
	    $(".plot_circle").removeClass("almost_invisible").removeClass("opaque");
	}

	function resize_svg(margin, excessiveHeight) {
	    var viewBoxX = 600;
	    $(".word_meta_plot").css("min-width", vw(50));
	    try {
            var viewBoxY = $(".word_meta_plot>g")[0].getBBox()["height"];
            $(".word_meta_plot").attr("viewBox", "0 0 " + viewBoxX + " " + (40 + viewBoxY));
            $(".word_meta_plot").css("min-height", Math.max(300, viewBoxY / excessiveHeight));
        }
        catch (e) {
		    setTimeout(function() {
		        var viewBoxY = $(".word_meta_plot>g")[0].getBBox()["height"];
                $(".word_meta_plot").attr("viewBox", "0 0 " + viewBoxX + " " + (40 + viewBoxY));
                $(".word_meta_plot").css("min-height", Math.max(300, viewBoxY / excessiveHeight));
		    }, 500);
		}
		try {
		    var yAxisWidth = document.getElementById("y_axis").getBBox()["width"];
		    $(".word_meta_plot>g").attr("transform", "translate(" + yAxisWidth + "," + margin["top"] + ")");
		}
		catch (e) {
		    setTimeout(function() {
		        var yAxisWidth = document.getElementById("y_axis").getBBox()["width"];
		        $(".word_meta_plot>g").attr("transform", "translate(" + yAxisWidth + "," + margin["top"] + ")");
		    }, 500);
		}
	}

	function make_x_gridlines() {
        return d3.axisBottom(x)
            .ticks(5)
    }

    function make_y_gridlines() {
        return d3.axisLeft(y)
            .ticks(5)
    }

	function load_word_stats(e) {
		clear_word_stats_plots();

		var metaField = $('#select_meta_word_stat option:selected').attr('value');
		if (metaField == '') {
			return;
		}
		var queryType = $('#select_meta_query_type option:selected').attr('value');
		if (queryType == '') {
			return;
		}
		
		$.ajax({
			url: "word_stats/" + queryType + '/' + metaField,
			data: $("#search_main").serialize(),
			dataType : "json",
			type: "GET",
			success: display_word_stats_plot,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function load_freq_stats(e) {
		var freqStatType = $('#select_freq_stat_type option:selected').attr('value');
		if (freqStatType == '') {
			clear_word_stats_plots();
			return;
		}
		
		$.ajax({
			url: "word_freq_stats/" + freqStatType,
			data: $("#search_main").serialize(),
			dataType : "json",
			type: "GET",
			success: display_word_freq_stats_plot,
			//success: print_json,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}

	function bar_title(v) {
	    return Math.round(v.n_words) + " ipm [" + Math.round(v.n_words_conf_int[0]) + ", " + Math.round(v.n_words_conf_int[1]) + "]";
	}
	
	function show_bar_chart(results, maxHeight) {
		var nResults = results[0].length;
		var barWidth = 20;
		var maxBars = 25;
		var nBars = nResults;
		if (nBars >= maxBars) {
			nBars = maxBars;
			$('#word_stats_max_bars').show();
		}
		else {
		    $('#word_stats_max_bars').hide();
		}
	    x = d3.scaleBand()
            .rangeRound([0, barWidth * nBars], .1)
		    .paddingInner(0.1);
		y = d3.scaleLinear()
			.range([200, 0]);

		xAxis = d3.axisBottom().scale(x);
		yAxis = d3.axisLeft().scale(y).tickFormat(function (d) { return d + ' ipm'; });

		var queryType = $('#select_meta_query_type option:selected').val();
/*
		var chart = d3.select(".word_meta_plot")
			.attr("width", barWidth * nBars + margin.left + margin.right)
			.attr("height", 320 + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
*/
		chart = d3.select(".word_meta_plot").append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		y.domain([0, maxHeight]);
		x.domain(results[0].map(function(v) { return v.name; }));
		
		gx = chart.append("g")
		    .attr("class", "x axis")
		    .attr("transform", "translate(0,200)")
		    .call(xAxis);
		gx.selectAll("text")
            .style("text-anchor", "start")
            .attr("dx", "10px")
            .attr("dy", "-5px")
            .attr("transform", "rotate(90)");
			
	    gy = chart.append("g")
		    .attr("class", "y axis")
		    .attr("id", "y_axis")
		    .call(yAxis);
		chart.append("g")
          .attr("class", "grid")
          .call(make_y_gridlines()
              .tickSize(-500)
              .tickFormat("")
          );

        var excessiveHeight = maxHeight; // confidence intervals that go over the roof
        var dataResorted = [];
        for (iRes = 0; iRes < results[0].length; iRes++) {
            dataResorted.push([]);
        }
        for (iQueryWord = 0; iQueryWord < results.length; iQueryWord++) {
            for (iRes = 0; iRes < results[iQueryWord].length; iRes++) {
                dataResorted[iRes].push(results[iQueryWord][iRes]);
                dataResorted[iRes][iQueryWord].n_query_word = iQueryWord;
                if (results[iQueryWord][iRes].n_words_conf_int[1] > excessiveHeight) {
                    excessiveHeight = results[iQueryWord][iRes].n_words_conf_int[1];
                }
            }
        }
        excessiveHeight = excessiveHeight / maxHeight;
        for (iRes = 0; iRes < dataResorted.length; iRes++) {
            dataResorted[iRes].sort((a,b) => (a.n_words > b.n_words) ? -1 : ((b.n_words > a.n_words) ? 1 : 0));
        }
        for (iRes = 0; iRes < dataResorted.length; iRes++) {
            for (iQueryWord = 0; iQueryWord < dataResorted[iRes].length; iQueryWord++) {
                results[iQueryWord][iRes] = dataResorted[iRes][iQueryWord];
            }
        }

        for (iRes = 0; iRes < results.length; iRes++) {
            var barClass = "bar bar_default"
            if (queryType == "compare") {
                barClass = "bar bar_w" + (iRes + 1);
            }
            bar = chart.selectAll(".bar_new")
                .data(results[iRes])
              .enter().append("rect")
                .attr("class", v => "bar bar_w" + (v.n_query_word + 1))
                .attr("x", v => x(v.name))
                .attr("width", x.bandwidth())
                .attr("y", 200)
                .attr("height", 0)
                .transition().duration(1200)
                .attr("y", v => y(v.n_words))
                .attr("height", v => 200 - y(v.n_words))
                .attr("title", bar_title);
            chart.selectAll(".conf_int_new")
                .data(results[iRes])
              .enter().append("line")
                .attr("class", v => "conf_int conf_int_w" + (v.n_query_word + 1))
                .attr("x1", v => x(v.name) + barWidth / 2)
                .attr("x2", v => x(v.name) + barWidth / 2)
                .attr("y1", 200)
                .attr("y2", 200)
                .transition().duration(1200)
                .attr("y1", v => y(v.n_words_conf_int[0]))
                .attr("y2", v => y(v.n_words_conf_int[1]));
            chart.selectAll(".conf_int_cap_top_new")
                .data(results[iRes])
              .enter().append("line")
                .attr("class", v => "conf_int_cap_top conf_int conf_int_w" + (v.n_query_word + 1))
                .attr("x1", v => x(v.name) + barWidth / 2 - 3)
                .attr("x2", v => x(v.name) + barWidth / 2 + 3)
                .attr("y1", 200)
                .attr("y2", 200)
                .transition().duration(1200)
                .attr("y1", v => y(v.n_words_conf_int[0]))
                .attr("y2", v => y(v.n_words_conf_int[0]));
            chart.selectAll(".conf_int_cap_bottom_new")
                .data(results[iRes])
              .enter().append("line")
                .attr("class", v => "conf_int_cap_bottom conf_int conf_int_w" + (v.n_query_word + 1))
                .attr("x1", v => x(v.name) + barWidth / 2 - 3)
                .attr("x2", v => x(v.name) + barWidth / 2 + 3)
                .attr("y1", 200)
                .attr("y2", 200)
                .transition().duration(1200)
                .attr("y1", v => y(v.n_words_conf_int[1]))
                .attr("y2", v => y(v.n_words_conf_int[1]));
        }
        setTimeout(function (){
            $('.bar').each(function () {
                $(this).html("<title>" + $(this).attr("title") + "</title>")
            });
        }, 1);
//        chart.selectAll(".bar")
//                .data(results[iQueryWord])
//              .append("title")
//                .text();

		setTimeout(function() {resize_svg(margin, excessiveHeight);}, 300);
	}
	
	function show_line_plot(results, maxHeight, multiplier, yLabel) {
		if (results == null || results.length <= 0) {
			return;
		}
		var nResults = results[0].length;
		
		var xAxisScale = $('#select_x_axis_scale option:selected').val();
		if (xAxisScale == 'logarithmic') {
			function xTransform(v) { return parseInt(v.name) + 1; }
			x = d3.scaleLog()
				.range([0, 350]);
		}
		else {
			function xTransform(v) { return parseInt(v.name); }
			x = d3.scaleLinear()
				.range([2, 502]);
		}
		var xDomain = d3.extent(results[0], xTransform);
		y = d3.scaleLinear()
			.range([200, 0]);

		xAxis = d3.axisBottom().scale(x).tickFormat(d => Math.round(d) == d ? d + "" : "");
		yAxis = d3.axisLeft().scale(y).tickFormat(d => d + yLabel);

		chart = d3.select(".word_meta_plot").append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		y.domain([0, maxHeight * multiplier]);
		x.domain(xDomain);
		
		gx = chart.append("g")
		    .attr("class", "x axis")
		    .attr("id", "x_axis")
		    .attr("transform", "translate(0,200)")
		    .call(xAxis);
		gx.selectAll("text")  
            .style("text-anchor", "start")
            .attr("dx", "10px")
            .attr("dy", "-5px")
            .attr("transform", "rotate(90)");
			
	    gy = chart.append("g")
		    .attr("class", "y axis")
		    .attr("id", "y_axis")
		    .call(yAxis);

		chart.append("g")
          .attr("class", "grid")
          .attr("transform", "translate(0,200)")
          .call(make_x_gridlines()
              .tickSize(-200)
              .tickFormat("")
          );

        chart.append("g")
          .attr("class", "grid")
          .call(make_y_gridlines()
              .tickSize(-500)
              .tickFormat("")
          );

        var excessiveHeight = maxHeight; // confidence intervals that go over the roof
        for (iQueryWord = 0; iQueryWord < results.length; iQueryWord++) {
            for (iRes = 0; iRes < results[iQueryWord].length; iRes++) {
                if ('n_words_conf_int' in results[iQueryWord][iRes] && results[iQueryWord][iRes].n_words_conf_int[1] > excessiveHeight) {
                    excessiveHeight = results[iQueryWord][iRes].n_words_conf_int[1];
                }
            }
        }
        excessiveHeight = excessiveHeight / maxHeight;
		
		for (iQueryWord = 0; iQueryWord < results.length; iQueryWord++) {
			var valueline = d3.line()
				.x(v => x(xTransform(v)))
				.y(v => y(v.n_words * multiplier))
				.curve(d3.curveBasis);
				//.curve(d3.curveLinear);
			var valuelineInitial = d3.line()
				.x(v => x(xTransform(v)))
				.y(200)
				.curve(d3.curveBasis);
			chart.append("path")
				.data([results[iQueryWord]])
				.attr("class", "plot_line_w" + (iQueryWord + 1) + " plot_line")
				.attr("d", valuelineInitial)
				.transition().duration(1200)
				.attr("d", valueline);
			chart.selectAll("dot")
				.data(results[iQueryWord])
			  .enter().append("circle")
				.attr("r", 3.5)
				.attr("cx", v => x(xTransform(v)))
				.attr("cy", 200)
				.attr("class", "plot_circle plot_circle_w" + (iQueryWord + 1))
				.transition().duration(1200)
				.attr("cy", v => y(v.n_words * multiplier));

			if ('n_words_conf_int' in results[iQueryWord][0]) {
			    chart.selectAll(".plot_circle_w" + (iQueryWord + 1))
		            .data(results[iQueryWord])
		          .append("title")
		            .text(v => Math.round(v.n_words) + " ipm [" + Math.round(v.n_words_conf_int[0]) + ", " + Math.round(v.n_words_conf_int[1]) + "]");

				chart.selectAll(".conf_int_new")
				    .data(results[iQueryWord])
				  .enter().append("line")
				    .attr("class", "conf_int conf_int_w" + (iQueryWord + 1))
				    .attr("x1", v => x(xTransform(v)))
					.attr("x2", v => x(xTransform(v)))
					.attr("y1", 200)
					.attr("y2", 200)
					.transition().duration(1200)
				    .attr("y1", v => y(v.n_words_conf_int[0] * multiplier))
				    .attr("y2", v => y(v.n_words_conf_int[1] * multiplier));
				chart.selectAll(".conf_int_cap_top_new")
				    .data(results[iQueryWord])
				  .enter().append("line")
				    .attr("class", "conf_int_cap_top conf_int conf_int_w" + (iQueryWord + 1))
				    .attr("x1", v => x(xTransform(v)) - 3)
					.attr("x2", v => x(xTransform(v)) + 3)
					.attr("y1", 200)
					.attr("y2", 200)
					.transition().duration(1200)
				    .attr("y1", v => y(v.n_words_conf_int[0] * multiplier))
				    .attr("y2", v => y(v.n_words_conf_int[0] * multiplier));
				chart.selectAll(".conf_int_cap_bottom_new")
				    .data(results[iQueryWord])
				  .enter().append("line")
				    .attr("class", "conf_int_cap_bottom conf_int conf_int_w" + (iQueryWord + 1))
				    .attr("x1", v => x(xTransform(v)) - 3)
					.attr("x2", v => x(xTransform(v)) + 3)
					.attr("y1", 200)
					.attr("y2", 200)
					.transition().duration(1200)
				    .attr("y1", v => y(v.n_words_conf_int[1] * multiplier))
				    .attr("y2", v => y(v.n_words_conf_int[1] * multiplier));
			}
		}
		setTimeout(assign_plot_circle_events(chart), 300)
		setTimeout(function() {resize_svg(margin, excessiveHeight);}, 300);
	}

	function clear_table() {
	    $('#word_stats_table tbody').html("");
	    $('#word_stats_table_header_top').html("<th></th>");
	    $('#word_stats_table_header_bottom').html("");
	}

	function fill_table(results) {
	    var tableBody = $('#word_stats_table tbody');
	    var tableHeaderTop = $('#word_stats_table_header_top');
	    var tableHeaderBottom = $('#word_stats_table_header_bottom');
	    clear_table();
	    if (results == null) {
			return;
		}
		tableHeaderBottom.html(tableHeaderBottom.html() + $('#header_template_start').html());
		for (iQueryWord = 0; iQueryWord < results.length; iQueryWord++) {
		    tableHeaderTop.html(tableHeaderTop.html() + "<th colspan=\"2\" class=\"th_query_word\" data-nword=\"" + (iQueryWord + 1) + "\">"
		                        + "<div class=\"circle circle_w" + (iQueryWord + 1) + "\"></div>"
		                        + queryWordCaption + " " + (iQueryWord + 1) + "</th>");
            tableHeaderBottom.html(tableHeaderBottom.html() + $('#header_template_end').html());
		    for (iRes = 0; iRes < results[iQueryWord].length; iRes++) {
		        v = results[iQueryWord][iRes];
		        var rowID = "word_stats_tr_" + iRes;
		        tr = "<td>" + Math.round(v.n_words) + "</td>"
                tr += "<td class=\"conf_int_span\"> ["
                      + Math.round(v.n_words_conf_int[0])
                      + ", " + Math.round(v.n_words_conf_int[1]) + "]</td>";
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
		assign_word_stats_table_events();
	}
	
	function display_word_stats_plot(results) {
		clear_word_stats_plots();
		clear_table();
		$('#word_stats_wait').fadeOut();

		data = results;
		if (results == null) {
			$('#word_stats_nothing_found').show();
			return;
		}
		var plotObj = $('#word_stats_plot');
		if (results.length <= 0 || results[0].length <= 0) {
			$('#word_stats_nothing_found').show();
			return;
		}
		var metaField = $('#select_meta_word_stat option:selected').val();
		if (metaField == '') {
			return;
		}
		var maxHeight = 1
		for (iQueryWord = 0; iQueryWord < results.length; iQueryWord++) {
			var curMaxHeight = d3.max(results[iQueryWord], v => v.n_words);
			if (curMaxHeight > maxHeight) {
				maxHeight = curMaxHeight;
			}
		}
		fill_table(results);
		svg = d3.create("svg");
      	plotObj.append(svg);
      	plotObj.find('svg').addClass('word_meta_plot').attr("viewBox", "0 0 600 350");
		if (metaField.startsWith('year') || intMetaFields.includes(metaField)) {
			show_line_plot(results, maxHeight, 1, ' ipm');
		}
		else
		{
			show_bar_chart(results, maxHeight);
		}
	}
	
	function display_word_freq_stats_plot(results) {
		clear_word_stats_plots();
		clear_table();
		$('#word_stats_wait').fadeOut();
		if (results == null) {
			$('#word_stats_nothing_found').show();
			return;
		}
		lastFreqData = results;
		var plotObj = $('#word_freq_rank_stats_plot');
		if (results.length <= 0 || results[0].length <= 0) {
			$('#word_stats_nothing_found').show();
			return;
		}
		var maxHeight = 0
		var maxYUser = $('#select_max_y option:selected').val();
		if (maxYUser == "as_in_data") {
            for (iRes = 0; iRes < results.length; iRes++) {
                var curMaxHeight = d3.max(results[iRes], v => v.n_words);
                if (curMaxHeight > maxHeight) {
                    maxHeight = curMaxHeight;
                }
            }
		}
		else {
		    maxHeight = maxYUser / 100;
		}
		svg = d3.create("svg");
      	plotObj.append(svg);
      	plotObj.find('svg').addClass('word_meta_plot').attr("viewBox", "0 0 600 350");
		show_line_plot(results, maxHeight, 100, '%');
	}

	assign_word_stats_events();
});

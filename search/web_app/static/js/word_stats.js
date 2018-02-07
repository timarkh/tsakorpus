var lastFreqData = null;

$(function() {
	function assign_word_stats_events() {
		$('#select_meta_word_stat').unbind('change');
		$('#select_meta_query_type').unbind('change');
		$('#select_freq_stat_type').unbind('change');
		$('#select_x_axis_scale').unbind('change');
		$('#word_stats_ok').unbind('click');
		$('#button_close_word_stats').unbind('click');
		$('#load_word_meta_stats').unbind('click');
		$('#load_word_freq_stats').unbind('click');
		$('#select_meta_word_stat').change(load_word_stats);
		$('#select_meta_query_type').change(load_word_stats);
		$('#select_freq_stat_type').change(load_freq_stats);
		$('#select_x_axis_scale').change(function () {display_word_freq_stats_plot(lastFreqData);});
		$('#word_stats_ok').click(close_word_stats);
		$('#button_close_word_stats').click(close_word_stats);
		$('#load_word_meta_stats').click(load_word_stats);
		$('#load_word_freq_stats').click(load_freq_stats);
	}

	function load_word_stats(e) {
		var metaField = $('#select_meta_word_stat option:selected').attr('value');
		if (metaField == '') {
			clear_word_stats_plots();
			return;
		}
		var queryType = $('#select_meta_query_type option:selected').attr('value');
		if (queryType == '') {
			clear_word_stats_plots();
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
	
	function close_word_stats() {
		$('#word_stats').modal('toggle');
		$('#w_id1').val('');
	}
	
	function clear_word_stats_plots(results) {
		$('#word_stats_plot').html('<svg></svg>');
		$('#word_freq_rank_stats_plot').html('<svg></svg>');
	}
	
	function show_bar_chart(results, maxHeight, margin) {
		var nResults = results.length;
		var barWidth = 20;
		var maxBars = 25;
		var nBars = nResults;
		if (nBars > maxBars) {
			nBars = maxBars;
		}
	    var x = d3.scaleBand()
            .rangeRound([0, barWidth * nBars], .1)
		    .paddingInner(0.1);
		var y = d3.scaleLinear()
			.range([200, 0]);

		var xAxis = d3.axisBottom().scale(x);
		var yAxis = d3.axisLeft().scale(y).tickFormat(function (d) { return d + ' ipm'; });

		var chart = d3.select(".word_meta_plot")
			.attr("width", barWidth * nBars + margin.left + margin.right)
			.attr("height", 320 + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		y.domain([0, maxHeight]);
		x.domain(results.map(function(v) { return v.name; }));
		
		chart.append("g")
		    .attr("class", "x axis")
		    .attr("transform", "translate(0,200)")
		    .call(xAxis)
			  .selectAll("text")  
              .style("text-anchor", "start")
              .attr("dx", "10px")
              .attr("dy", "-5px")
              .attr("transform", "rotate(90)");
			
	    chart.append("g")
		    .attr("class", "y axis")
		    .call(yAxis);
		chart.selectAll(".bar")
		    .data(results)
		  .enter().append("rect")
		    .attr("class", "bar")
		    .attr("x", function(v) { return x(v.name); })
			.attr("width", x.bandwidth())
		    .attr("y", function(v) { return y(v.n_words); })
		    .attr("height", function(v) { return 200 - y(v.n_words); });
		chart.selectAll(".conf_int")
		    .data(results)
		  .enter().append("line")
		    .attr("class", "conf_int")
		    .attr("x1", function(v) { return x(v.name) + barWidth / 2; })
			.attr("x2", function(v) { return x(v.name) + barWidth / 2; })
		    .attr("y1", function(v) { return y(v.n_words_conf_int[0]); })
		    .attr("y2", function(v) { return y(v.n_words_conf_int[1]); });
		chart.attr("height", 320 + margin.top + margin.bottom);
	}
	
	function show_line_plot(results, maxHeight, margin, multiplier, yLabel) {
		if (results == null || results.length <= 0) {
			return;
		}
		var nResults = results[0].length;
		
		var xAxisScale = $('#select_x_axis_scale option:selected').val();
		if (xAxisScale == 'logarithmic') {
			function xTransform(v) { return parseInt(v.name) + 1; }
			var x = d3.scaleLog()
				.range([0, 350]);
		}
		else {
			function xTransform(v) { return parseInt(v.name); }
			var x = d3.scaleLinear()
				.range([0, 350]);
		}
		var xDomain = d3.extent(results[0], xTransform);
		var y = d3.scaleLinear()
			.range([200, 0]);

		var xAxis = d3.axisBottom().scale(x);
		var yAxis = d3.axisLeft().scale(y).tickFormat(function (d) { return d + yLabel; });

		var chart = d3.select(".word_meta_plot")
			.attr("width", 350 + margin.left + margin.right)
			.attr("height", 320 + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		y.domain([0, maxHeight * multiplier]);
		x.domain(xDomain);
		
		chart.append("g")
		    .attr("class", "x axis")
		    .attr("transform", "translate(0,200)")
		    .call(xAxis)
			  .selectAll("text")  
              .style("text-anchor", "start")
              .attr("dx", "10px")
              .attr("dy", "-5px")
              .attr("transform", "rotate(90)");
			
	    chart.append("g")
		    .attr("class", "y axis")
		    .call(yAxis);
		
		for (iQueryWord = 0; iQueryWord < results.length; iQueryWord++) {	
			var valueline = d3.line()
				.x(function(v) { return x(xTransform(v)); })
				.y(function(v) { return y(v.n_words * multiplier); })
				.curve(d3.curveBasis);
				//.curve(d3.curveLinear);
			chart.append("path")
				.data([results[iQueryWord]])
				.attr("class", "plot_line_w" + (iQueryWord + 1) + " plot_line")
				.attr("d", valueline);
			chart.selectAll("dot")
				.data(results[iQueryWord])
			  .enter().append("circle")
				.attr("r", 3.5)
				.attr("cx", function(v) { return x(xTransform(v)); })
				.attr("cy", function(v) { return y(v.n_words * multiplier); });
		}
		chart.attr("height", 320 + margin.top + margin.bottom);
	}
	
	function display_word_stats_plot(results) {
		clear_word_stats_plots();
		if (results == null) {
			return;
		}
		var plotObj = $('#word_stats_plot');
		if (results.length <= 0 || results[0].length <= 0) {
			plotObj.html('<p>' + nothingFoundCaption + '</p>');
			return;
		}
		var metaField = $('#select_meta_word_stat option:selected').val();
		if (metaField == '') {
			return;
		}
		var maxHeight = 1
		for (iRes = 0; iRes < results.length; iRes++) {
			var curMaxHeight = d3.max(results[iRes], function(v) { return v.n_words; });
			if (curMaxHeight > maxHeight) {
				maxHeight = curMaxHeight;
			}
		}
		var margin = {"top": 20, "right": 30, "bottom": 30, "left": 65};
		plotObj.html('<svg class="word_meta_plot"></svg>');
		if (metaField.startsWith('year')) {
			show_line_plot(results, maxHeight, margin, 1, ' ipm');
		}
		else
		{
			show_bar_chart(results[0], maxHeight, margin);
		}
	}
	
	function display_word_freq_stats_plot(results) {
		clear_word_stats_plots();
		if (results == null) {
			return;
		}
		lastFreqData = results;
		var plotObj = $('#word_freq_rank_stats_plot');
		if (results.length <= 0 || results[0].length <= 0) {
			plotObj.html('<p>' + nothingFoundCaption + '</p>');
			return;
		}
		var maxHeight = 0
		for (iRes = 0; iRes < results.length; iRes++) {
			var curMaxHeight = d3.max(results[iRes], function(v) { return v.n_words; });
			if (curMaxHeight > maxHeight) {
				maxHeight = curMaxHeight;
			}
		}
		var margin = {"top": 20, "right": 30, "bottom": 30, "left": 65};
		plotObj.html('<svg class="word_meta_plot"></svg>');
		show_line_plot(results, maxHeight, margin, 100, '%');
	}

	assign_word_stats_events();
});

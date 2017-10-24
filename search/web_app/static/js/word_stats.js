$(function() {
	function assign_word_stats_events() {
		$('#select_meta_word_stat').unbind('change');
		$('#word_stats_ok').unbind('click');
		$('#select_meta_word_stat').change(load_word_stats);
		$('#word_stats_ok').click(close_word_stats);
	}

	function load_word_stats(e) {
		var metaField = $('#select_meta_word_stat option:selected').text();
		if (metaField == '') {
			clear_word_stats_plot();
			return;
		}
		
		$.ajax({
			url: "word_stats/" + metaField,
			data: $("#search_main").serialize(),
			dataType : "json",
			type: "GET",
			success: display_word_stats_plot,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function close_word_stats() {
		$('#word_stats').modal('toggle');
	}
	
	function clear_word_stats_plot(results) {
		$('#word_stats_plot').html('<svg class="word_meta_plot"></svg>');
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
		chart.attr("height", 320 + margin.top + margin.bottom);
	}
	
	function show_line_plot(results, maxHeight, margin) {
		var nResults = results.length;
		var barWidth = 20;
		var maxBars = 25;
		var nBars = nResults;
		if (nBars > maxBars) {
			nBars = maxBars;
		}
		var xDomain = d3.extent(results, function(v) { return parseInt(v.name); });
	    var x = d3.scaleLinear()
            .range([0, 350]);
		var y = d3.scaleLinear()
			.range([200, 0]);

		var xAxis = d3.axisBottom().scale(x);
		var yAxis = d3.axisLeft().scale(y).tickFormat(function (d) { return d + ' ipm'; });

		var chart = d3.select(".word_meta_plot")
			.attr("width", 350 + margin.left + margin.right)
			.attr("height", 320 + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		y.domain([0, maxHeight]);
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
		
		var valueline = d3.line()
            .x(function(v) { return x(parseInt(v.name)); })
            .y(function(v) { return y(v.n_words); })
			.curve(d3.curveBasis);
		chart.append("path")
            .data([results])
            .attr("class", "plot_line")
            .attr("d", valueline);
		chart.attr("height", 320 + margin.top + margin.bottom);
	}
	
	function display_word_stats_plot(results) {
		if (results.length <= 0) {
			$('#word_stats_plot').html('<p>Nothing found.</p>');
			return;
		}
		var metaField = $('#select_meta_word_stat option:selected').text();
		if (metaField == '') {
			return;
		}
		var maxHeight = d3.max(results, function(v) { return v.n_words; });
		var margin = {"top": 20, "right": 30, "bottom": 30, "left": 65};
		$('#word_stats_plot').html('<svg class="word_meta_plot"></svg>');
		if (metaField.startsWith('year')) {
			show_line_plot(results, maxHeight, margin);
		}
		else
		{
			show_bar_chart(results, maxHeight, margin);
		}
	}

	assign_word_stats_events();
});

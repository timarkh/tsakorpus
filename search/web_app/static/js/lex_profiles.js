var x = null;
var y = null;
var gx = null;
var gy = null;
var xAxis = null;
var yAxis = null;
var chart = null;
var bar = null;

$(function() {
	function draw_plot(index) {
		let data = JSON.parse($(this).html());
		let sumValues = 0;
		let maxHeight = 1;
		for (i = 0; i < data.length; i++) {
			sumValues += data[i][1];
			if (data[i][1] > maxHeight) {
				maxHeight = data[i][1];
			}
		}

		if (sumValues > 0) {
			$(this).html('<svg></svg>');
		} else {
			$(this).html('<p>∅</p>')
		}
      	$(this).find('svg').addClass('lex_profile_plot_svg').attr("viewBox", "-75 -20 700 175")
      	$(this).find('svg').attr("id", $(this).attr('id') + '_plot');
		draw_bar_chart('#' + $(this).attr('id') + '_plot', data, maxHeight, sumValues);
	}
	
	function draw_plots() {
		$('.lex_profile_plot').each(draw_plot);
	}

	function bar_title(v, sumValues) {
	    let title = v[1];
	    if (title > 0 && sumValues > 0) {
	    	title += " (" + (Math.round(v[1] * 1000 / sumValues) / 10) + "%)";
	    }
	    return title;
	}

	function draw_bar_chart(plotID, data, maxHeight, sumValues) {
		var barWidth = Math.min(90, Math.max(35, Math.round(400 / data.length)));
		var nBars = data.length;
	    x = d3.scaleBand()
            .rangeRound([0, barWidth * nBars], .1)
		    .paddingInner(0.1);
		y = d3.scaleLinear()
			.range([100, 0]);

		xAxis = d3.axisBottom().scale(x).tickSizeInner(0);
		yAxis = d3.axisLeft().scale(y).ticks(2).tickFormat(function (d) { return d; });

		chart = d3.select(plotID).append("g");
		
		y.domain([0, maxHeight]);
		x.domain(data.map(function(v) { return v[0]; }));
		
		gx = chart.append("g")
		    .attr("class", "x axis")
		    .attr("transform", "translate(0,-15)")
		    .call(xAxis);
		gx.selectAll("text")
            .style("text-anchor", "start")
            .attr("dx", "0px")
            .attr("dy", "5px")
            .attr("transform", "rotate(90)");
			
	    gy = chart.append("g")
		    .attr("class", "y axis")
		    .attr("id", "y_axis")
		    .call(yAxis);

        bar = chart.selectAll(".bar_new")
            .data(data)
          .enter().append("rect")
            .attr("class", v => "bar bar_default")
            .attr("x", v => x(v[0]))
            .attr("width", x.bandwidth())
            .attr("y", 100)
            .attr("height", 0)
            .transition().duration(1200)
            .attr("y", v => y(v[1]))
            .attr("height", v => Math.max(2, 100 - y(v[1])))
            .attr("title", v => bar_title(v, sumValues));

        setTimeout(function (){
            $(plotID + ' .bar').each(function () {
                $(this).html("<title>" + $(this).attr("title") + "</title>")
            });
        }, 1300);
	}

	draw_plots();
	assign_tooltips();
});
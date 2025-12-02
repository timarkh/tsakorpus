var margin = {"top": 20, "right": 30, "bottom": 30, "left": 80};
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
		var data = JSON.parse($(this).html());
		return;

		// TODO: continue here
		$(this).html('<svg></svg>');
		var svg = d3.create("svg");
		$(this).append(svg);
      	$(this).find('svg').addClass('lex_profile_plot').attr("viewBox", "0 0 400 50")
      	$(this).find('svg').attr("id", $(this).attr('id') + '_plot');
		draw_bar_chart('#' + $(this).attr('id') + '_plot', data, 200);
	}
	
	function draw_plots() {
		$('.lex_profile_plot').each(draw_plot);
	}

	function bar_title(v) {
	    return v[1];
	}

	function draw_bar_chart(plotID, data, maxHeight) {
		var barWidth = 20;
		var nBars = data.length;
	    x = d3.scaleBand()
            .rangeRound([0, barWidth * nBars], .1)
		    .paddingInner(0.1);
		y = d3.scaleLinear()
			.range([100, 0]);

		xAxis = d3.axisBottom().scale(x);
		yAxis = d3.axisLeft().scale(y).tickFormat(function (d) { return d; });

		chart = d3.select(plotID).append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		y.domain([0, maxHeight]);
		x.domain(data.map(function(v) { return v[0]; }));
		
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

        for (i = 0; i < data.length; i++) {
            var barClass = "bar bar_default"
            bar = chart.selectAll(".bar_new")
                .data(data[i])
              .enter().append("rect")
                .attr("class", v => "bar")
                .attr("x", v => x(v[0]))
                .attr("width", x.bandwidth())
                .attr("y", 100)
                .attr("height", 0)
                .transition().duration(1200)
                .attr("y", v => y(v[1]))
                .attr("height", v => 100 - y(v[1]))
                .attr("title", bar_title);
        }
        setTimeout(function (){
            $('.bar').each(function () {
                $(this).html("<title>" + $(this).attr("title") + "</title>")
            });
        }, 1);
	}

	draw_plots();
});
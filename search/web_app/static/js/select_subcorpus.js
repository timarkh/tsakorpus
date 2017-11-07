
	function assign_subcorpus_events() {
		$('.switchable_subcorpus_option').unbind('click');
		$('#subcorpus_selector_ok').unbind('click');
		$('#subcorpus_selector_clear').unbind('click');
		$('#subcorpus_stats_link').unbind('click');
		$('#select_meta_stat').unbind('change');
		$('.switchable_subcorpus_option').click(toggle_subcorpus_option);
		$('#load_documents_link').click(load_subcorpus_documents);
		$('#subcorpus_selector_ok').click(close_subcorpus_selector);
		$('#subcorpus_selector_clear').click(clear_subcorpus);
		$('#subcorpus_stats_link').click(load_subcorpus_stats);
		$('#select_meta_stat').change(load_subcorpus_stats);
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
		var metaField = $('#select_meta_stat option:selected').val();
		if (metaField == '') {
			clear_subcorpus_stats_plot();
			return;
		}
		$.ajax({
			url: "doc_stats/" + metaField,
			data: $("#search_main").serialize(),
			type: "GET",
			success: display_subcorpus_stats_plot,
			error: function(errorThrown) {
				alert( JSON.stringify(errorThrown) );
			}
		});
	}
	
	function clear_subcorpus_stats_plot(results) {
		$('#subcorpus_stats_plot').html('<svg class="meta_plot"></svg>');
	}
	
	function display_subcorpus_stats_plot(results) {
		var nResults = results.length;
		if (nResults <= 0) {
			$('#subcorpus_stats_plot').html('<p>' + nothingFoundCaption + '</p>');
			return;
		}
		
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
		
		$('#subcorpus_stats_plot').html('<svg class="meta_plot"></svg>');
		var barWidth = 20;
		var maxBars = 25;
		var nBars = nResults;
		if (nBars > maxBars) {
			nBars = maxBars;
		}
		var margin = {"top": 20, "right": 30, "bottom": 30, "left": 40};
		
	    var x = d3.scaleBand()
            .rangeRound([0, barWidth * nBars], .1)
		    .paddingInner(0.1);

		var y = d3.scaleLinear()
			.range([200, 0]);

		var xAxis = d3.axisBottom().scale(x);

		var yAxis = d3.axisLeft().scale(y).tickFormat(function (d) { return d + sfx; });

		var chart = d3.select(".meta_plot")
			.attr("width", barWidth * nBars + margin.left + margin.right)
			.attr("height", 320 + margin.top + margin.bottom)
		  .append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
		
		x.domain(results.map(function(v) { return v.name; }));
		y.domain([0, maxHeight / divisor]);
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
		    .attr("y", function(v) { return y(v.n_words / divisor); })
		    .attr("height", function(v) { return 200 - y(v.n_words / divisor); });
		chart.attr("height", 320 + margin.top + margin.bottom);
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


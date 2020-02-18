(function($) {

  var $body = $('body');

  if($body.hasClass('single-greenchamber') || $body.hasClass('single-redchamber')) {

    var data = [];

    $.getJSON( "https://v2.polytics.ca/api/person/summary", {pid: pid}, function( data ) {

      })
      .success(function(data) {
        recent_summary_title(data.recent_summary_title);
        recent_list_title(data.recent_list_title);
        if (data.total_comms > 0) {
          total_comms(data.total_comms);
          count_table(data.corp_count, "Organization", '#corp-count');
          count_table(data.subj_count, "Subject", '#subj-count');
          comm_list(data.comms_list);
        } else {
          $('#corp-count').append('<p>No communication reports found for this period.</p>');
          $("#meeting_list").append('<p>No communication reports found for this period.</p>');
        }
        heat_map(data.heat_map_data);
      })

      .fail(function() {
        recent_list_title("No communication reports available");
        recent_summary_title("No communication reports available");
      });

    function total_comms(n) {
      $('#total-n').append('<div class="number">' + n + '</div><small>Communications reported</small>');
    }

    function recent_summary_title(text) {
      $('#recent_comms_summary_title').append(text);
    }

    function recent_list_title(text) {
      $('#recent_comms_list_title').append(text);
    }

    function count_table(data, header, div_id) {
      var tableHTML = '<table class="lobbying-table"><tr><th>' + header + '</th><th>Reports</th></tr>';
      $.each( data, function( index, d ){
        tableHTML += '<tr><td>'+ d._id +'</td><td>'+ d.n_communications +'</td></tr>';
      });
      tableHTML += '</table>';
      $(div_id).append(tableHTML);
    }

    function comm_list(data) {
      var tableHTML = '';

      $.each( data, function( index, d ){
        dpoh_li = ''
        $.each(d.dpoh, function( i, oh){
          var dpoh_str = (oh.pid != null && oh.pid != pid) ? '<a href="/?p=' + oh.pid + '">' + oh.text + '</a>':oh.text;
          dpoh_li += '<li>'+ dpoh_str +'</li>';
        });
        tableHTML += '<div class="comm_list_row"><div class="comm_card">'
        tableHTML += '<div class="comm_date"><strong class="comm_subj">Date:</strong> '+ d.com_date +'</div>'
        tableHTML += '<div class="comm_org"><strong class="comm_subj">Org:</strong> '+ d.org +'</div>'
        tableHTML += '<div class="comm_registrant"><strong class="comm_subj">Registrant:</strong> '+ d.registrant +'</div>'
        tableHTML += '<div class="comm_dpoh"><strong class="comm_subj">DPOHs:</strong><ul class="info-list">'+ dpoh_li +'</ul></div>'
        tableHTML += '<strong class="comm_subj">Subjects:</strong> '+ d.subj
        tableHTML += '</div></div>';
      });

      tableHTML += '</table>';
      $("#meeting_list").append(tableHTML);

    }


    function heat_map(data){
      var heat_map_options = {
        responsive: true,
        maintainAspectRatio: true,
        colorInterpolation: "palette",
        colors: [ "#fff", '#deebf7','#c6dbef','#9ecae1','#6baed6','#4292c6','#2171b5','#08519c','#08306b'],
        showLabels: false,
        tooltipTemplate: "<%= yLabel %> (<%= xLabel %>): <%= value %>"
      }
      var ctx = document.getElementById('heatmap').getContext('2d');
      var newChart = new Chart(ctx).HeatMap(data, heat_map_options);
    };

  }

})( jQuery );
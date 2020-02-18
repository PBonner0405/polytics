function group_heatmap(div_id, gid) {
var d3 = Plotly.d3;

var WIDTH_IN_PERCENT_OF_PARENT = 100,
    HEIGHT_IN_PERCENT_OF_PARENT = 100;

var gd3 = d3.select(div_id)
    .append('div')
    .style({
        width: WIDTH_IN_PERCENT_OF_PARENT + '%',
        'margin-left': (100 - WIDTH_IN_PERCENT_OF_PARENT) / 2 + '%',

    });

var gd = gd3.node();

var url='https://v2.polytics.ca/api/group/' + gid + '/by_month';


d3.json(url, function(error, api_data) {
  if (error) return console.warn(error);


  var data = [
    {
      z: api_data.values,
      y: api_data.names,
      x: api_data.dates,
      text: api_data.hover,
      colorscale: [
        [0, '#deebf7'],
        [1.0, '#08306b']
      ],
      type: 'heatmap',
      xgap: 2,
      ygap: 2,
      hoverinfo: 'text',
      showscale: false,
      colorbar:{
        autotick: false,
        tick0: 0,
        dtick: 1
      }
    }
  ];

  var layout = {title: 'IP Lobbying by Month',
               xaxis: {showgrid: false,
                      side: 'top',
                       zeroline: false,
                       type: "category",
  },
               yaxis: {showgrid: false,
                      zeroline: false,
                      },
               height: api_data.names.length * 40 +150,
               autosize: true,

               margin: {
                 l: 200,
                 t: 150,

  }};

Plotly.newPlot(gd, data, layout, {displayModeBar: false});
})
window.onresize = function() {
    Plotly.Plots.resize(gd);
};
};

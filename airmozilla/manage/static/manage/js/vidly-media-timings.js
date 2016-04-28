$(function() {
    d3.json(location.pathname + 'data/', function(data) {
        MG.data_graphic({
            title: "Correlation of video duration and Vid.ly transcoding time",
            description: "Showing the last " + data.points.length + " Vid.ly submissions",
            data: data.points,
            least_squares: true,
            chart_type: 'point',
            full_width: true,
            height: 600,
            left: 110,
            bottom: 50,
            x_label: "Video duration",
            y_label: "Time to finish",
            axes_not_compact: true,
            target: '#plot',

            yax_format: function(f) {
                return moment.duration(f, 'seconds').humanize();
            },
            xax_format: function(f) {
                return moment.duration(f, 'seconds').humanize();
            },
            x_accessor: 'x',
            y_accessor: 'y',

        });

        $('.summary .slope').text(data.slope.toFixed(2));
        document.title = 'Slope: ' + data.slope.toFixed(2);
        var examples = [60 * 2, 60 * 10, 60 * 30, 60 * 60 * 2];
        var $container = $('.summary .examples');
        $.each(examples, function(i, t) {
            var time = moment.duration(t * data.slope, 'seconds').humanize();
            var duration = moment.duration(t, 'seconds').humanize();
            $('<li>')
                .html(
                    'About <b>' + time + '</b> for a <b>' +
                    duration + '</b> video'
                )
                .appendTo($container);
        });
    });
});

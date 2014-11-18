/*  This code is part of an experiment to play with JW Player.
    It doesn't do anything unless there's a id="jwplayer-ajax"
    element on the page. */
$(function() {
    var container = $('#jwplayer-ajax');
    if (container.length) {
        var tag = container.data('tag');
        $.get('/videoredirector/', {tag: tag})
        .then(function(response) {
            console.log('Videoredirector response', response);
            var playlist = [];
            var sources = [];
            $.each(response.urls, function(i, url) {
                sources.push({file: url});
            });
            playlist.push({sources: sources});

            jwplayer("jwplayer-ajax").setup({
                playlist: playlist,
                width: "100%",
                aspectratio: "16:9",
            });
        });
    }
});

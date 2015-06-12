$(function() {
    if (!$('.islive').length) return;
    if (typeof jwplayer === 'undefined') {
        console.warn('No jwplayer loaded');
        return;
    }
    if (typeof jwplayer("player").id === 'undefined') {
        console.warn('No jwplayer("player") to hook events to');
        return;
    }

    // http://stackoverflow.com/a/2646441/205832
    function addCommas(nStr) {
        nStr += '';
        var x = nStr.split('.');
        var x1 = x[0];
        var x2 = x.length > 1 ? '.' + x[1] : '';
        var rgx = /(\d+)(\d{3})/;
        while (rgx.test(x1)) {
            x1 = x1.replace(rgx, '$1' + ',' + '$2');
        }
        return x1 + x2;
    }

    function update(response) {
        // Doing this if because we don't want to display 0 views
        // when you're the first one to view and your own view hasn't
        // counted yet.
        if (response.hits) {
            $('.islive b').text(addCommas(response.hits));
            $('.islive').show();
        }
    }
    var url = $('.islive').data('url');
    // send a POST after some time to count this as a view
    jwplayer("player").onPlay(function() {
        var data = {
            csrfmiddlewaretoken:
            $('.islive input[name="csrfmiddlewaretoken"]').val()
        };
        $.post(url, data).then(update);
    });

    var loop = null;
    function fetch() {
        $.getJSON(url)
        .then(update)
        .fail(function() {
            if (loop !== null) {
                clearInterval(loop);
            }
        });
    }
    // first do an immediate AJAX get to get the number
    fetch();
    // then set up a loop
    setInterval(fetch, 10 * 1000);

});

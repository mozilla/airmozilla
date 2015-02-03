$(function() {
    if (!$('.islive').length) return;

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

    var submitted = false;
    var loop = setInterval(function() {
        var req, url = $('.islive').data('url');
        if (submitted) {
            req = $.getJSON(url);
        } else {
            var data = {
                csrfmiddlewaretoken:
                $('.islive input[name="csrfmiddlewaretoken"]').val()
            };
            req = $.post(url, data);
            submitted = true;
        }
        req.then(function(response) {
            if (response.hits) {
                $('.islive b').text(addCommas(response.hits));
                $('.islive').show();
            }
        })
        .fail(function() {
            clearInterval(loop);
        });
    }, 10 * 1000);
});

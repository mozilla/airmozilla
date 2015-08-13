$(function() {

    var timer;
    function showThumbnails($img, thumbnails) {
        $img.data('orig', $img.attr('src'));
        var index = 0;
        if (timer) {
            // Don't ever start another timer if we haven't cleared
            // the previous one.
            // We have to do this because of the async nature
            // of depending on an AJAX async query.
            clearInterval(timer);
        }
        timer = setInterval(function() {
            $img.attr('src', thumbnails[index % thumbnails.length]);
            index++;
        }, 500);
    }

    var fetched = {};
    var startedFetching = [];
    var stillover = false;
    $('#content').on('mouseover', 'img[data-eventid]', function() {
        var img = $(this);
        var eventid = img.data('eventid');
        if (fetched[eventid]) {
            showThumbnails(img, fetched[eventid]);
        } else if (startedFetching.indexOf(eventid) === -1) {
            var data = {
                id: eventid,
                width: img.attr('width'),
                height: img.attr('height'),
            };
            startedFetching.push(eventid);
            $.getJSON($('#content').data('thumbnails-url'), data)
            .then(function(response) {
                if (response.thumbnails.length) {
                    fetched[eventid] = response.thumbnails;
                    if (stillover) {
                        showThumbnails(img, response.thumbnails);
                    }
                }
            })
            .fail(function() {
                console.error.apply(console, arguments);
            });
        }
        stillover = true;
    });

    $('#content').on('mouseout', 'img[data-eventid]', function() {
        stillover = false;
        var img = $(this);
        if (img.data('orig') && img.attr('src') !== img.data('orig')) {
            img.attr('src', img.data('orig'));
        }
        if (timer) {
            clearInterval(timer);
        }
    });

});

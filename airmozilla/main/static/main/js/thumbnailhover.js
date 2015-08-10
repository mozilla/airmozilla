$(function() {

    var timer;
    function showThumbnails($img, thumbnails) {
        $img.data('orig', $img.attr('src'));
        var index = 0;
        timer = setInterval(function() {
            $img.attr('src', thumbnails[index % thumbnails.length]);
            index++;
        }, 500);
    }

    var fetched = {};
    var stillover = false;
    $('#content').on('mouseover', 'img[data-eventid]', function() {
        var img = $(this);
        var eventid = img.data('eventid');
        if (fetched[eventid]) {
            showThumbnails(img, fetched[eventid]);
        } else {
            var data = {
                id: eventid,
                width: img.attr('width'),
                height: img.attr('height'),
            };
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

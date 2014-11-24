/*global Camera */


$(function() {
    Camera.setup(100, function() {
        $('.starting').hide();
        $('.started').show();

    });

    function flash() {
        var element = $('.flash').show();
        setTimeout(function() {
            element.addClass('fadeout');
            setTimeout(function() {
                element.hide().removeClass('fadeout');
            }, 1000);
        }, 200);
    }

    var countdown_timer;
    function countDown(seconds, callback) {
        $('.countdown').text(seconds).show();
        countdown_timer = setTimeout(function() {
            $('.countdown').hide();
            if (seconds > 1) {
                countDown(seconds - 1, callback);
            } else {
                callback();
            }
        }, 1000);
    }

    // var blobs = [];

    var snap_blob;

    $('.save-picture button').click(function() {
        var self = $(this);
        self.hide();
        $('.save-picture .saving').show();
        var csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]').val();
        var fd = new FormData();
        fd.append('placeholder_img', snap_blob);
        fd.append('csrfmiddlewaretoken', csrfmiddlewaretoken);
        $.ajax({
            url: location.href,
            type: 'POST',
            data: fd,
            cache: false,
            processData: false,
            contentType: false
        })
        .done(function(response) {
            // console.log('RESPONSE', response);
            if (response.url) {
                $('.save-picture .saving').hide();
                location.href = response.url;
            }
        })
        .fail(function() {
            console.error(arguments);
            self.show();
        });
    });

    $('button.snap').click(function() {
        $('.snap-instruction').show();
        $('.started .preview').hide();
        $('.started canvas').show();
        $('.save-picture').hide();

        $(this).hide();
        countDown(3, function() {
            // console.log('Take the picture!!');

            flash();

            var canvas = Camera.getCanvas();
            canvas.toBlob(function(blob) {
                snap_blob = blob; // keep it in memory
            });
            $('.preview img').attr('src', canvas.toDataURL());
            $('.started canvas').hide();
            $('.started .preview').show();

            document.getElementById('shutter-sound').play();
            $(this).text('Snap another').show();
            $('.snap-instruction').hide();
            $('.save-picture').show();
        }.bind(this));
    });
});

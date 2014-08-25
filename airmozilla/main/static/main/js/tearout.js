$(function() {
    var iframe_clone = null;
    var popup = null;
    var placeholder = null;

    $('.tearout').on('mouseover', 'a.open', function(event) {
        if (!$('.tearout .problem:visible').length) {
            $('.tearout .warning-about-time').fadeIn(100);
        }
    }).on('mouseout', 'a.open', function(event) {
        $('.tearout .warning-about-time').fadeOut(300);
    });

    var player_width = null, player_height = null;

    $('.tearout').on('click', 'a.open', function(event) {
        event.preventDefault();
        var iframe = $('.entry-content iframe');
        var player_wrapper = $('.entry-content #player_wrapper');

        var video_url = location.href + 'video/?embedded=false&autoplay=true';
        var video_name = '_blank';
        var features = 'menubar=no,location=no,resizable=no,scrollbars=no,status=no';
        if (player_width === null || player_height === null) {
            if (iframe.length) {
                // probably a vid.ly iframe
                player_width = parseInt(iframe.attr('width'), 10);
                player_height = parseInt(iframe.attr('height'), 10);
            } else if (player_wrapper.length) {
                // probably a live event using jwplayer
                player_width = parseInt(player_wrapper.css('width'), 10);
                player_height = parseInt(player_wrapper.css('height'), 10);
            } else {
                console.warn('No iframe, so hard to guess the width and height of popup');
                // some sensible defaults
                player_width = 640;
                player_height = 360;
            }
        }
        features += ',width=' + player_width;
        features += ',height=' + player_height;

        popup = window.open(video_url, video_url, features);
        if (popup === null) {
            $('.tearout .problem')
            .text('Unable to make a pop-up Window. Perhaps ' +
                  'you need to unblock pop-up blockers for this site.'
            ).fadeIn(400);
        } else {
            // safe and useful if opened before under the same name
            popup.focus();

            // in case it previously didn't work
            $('.tearout .problem').hide();

            $('.tearout a.open').hide();
            $('.tearout a.restore').fadeIn(400);
            if (iframe.length) {
                iframe_clone = iframe.detach();
            } else {
                player_wrapper = player_wrapper.detach();
            }

            if (placeholder === null) {
                placeholder = $('<div>')
                    .addClass('tearout-placeholder');

                placeholder.css('width', player_width);
                placeholder.css('height', player_height);

                // and insert a restore link in it
                $('<a>')
                    .addClass('restore')
                    .attr('title', "Close the pop-up window and restore this page")
                    .text("Close the pop-up and restore video here")
                    .appendTo(placeholder);

                placeholder.on('click', 'a.restore', function(event) {
                    placeholder = placeholder.detach();
                    if (iframe.length) {
                        iframe_clone.insertBefore($('.tearout'));
                    } else {
                        player_wrapper.insertBefore($('.tearout'));
                    }

                    $('.tearout a.open').show();
                    if (popup !== null) {
                        popup.close();
                    }
                });
            }
            placeholder.insertBefore($('.tearout'));
        }
    });

});

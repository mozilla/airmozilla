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

    $('.tearout').on('click', 'a.open', function(event) {
        event.preventDefault();
        var iframe = $('.entry-content iframe');
        var player_wrapper = $('.entry-content #player_wrapper');

        var video_url = location.href + 'video/?embedded=false&autoplay=true';
        var video_name = '_blank';
        var features = 'menubar=no,location=no,resizable=no,scrollbars=no,status=no';
        if (iframe.length) {
            // probably a vid.ly iframe
            features += ',width=' + iframe.attr('width');
            features += ',height=' + iframe.attr('height');
        } else if (player_wrapper.length) {
            // probably a live event using jwplayer
            features += ',height=' + player_wrapper.css('height');
            features += ',width=' + player_wrapper.css('width');
        } else {
            console.warn('No iframe, so hard to guess the width and height of popup');
            // some sensible defaults
            features += ',width=640,height=360';
        }

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
                if (iframe.length) {
                    placeholder.css('width', iframe.attr('width'));
                    placeholder.css('height', iframe.attr('height'));
                } else if (player_wrapper.length) {
                    placeholder.css('width', player_wrapper.css('width'));
                    placeholder.css('height', player_wrapper.css('height'));
                } else {
                    placeholder.css('width', 640).css('height', 360);
                }
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

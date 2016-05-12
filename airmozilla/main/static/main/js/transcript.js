$(function() {

    var parent = $('.transcript');
    var scrollFocus = function(id) {
        var elem = $('#' + id);
        // based on http://stackoverflow.com/a/18927969/205832
        // The -100 is to make it roughly appear in the "middle"
        parent.animate({
            scrollTop: parent.scrollTop() - parent.offset().top + elem.offset().top - 100
        }, 500);
    };

    var trackTranscript = function(player) {
        var transcripts = $('p', parent);
        if (!transcripts.length) {
            return;
        }
        var times = {};
        var ids = [];
        transcripts.each(function(p) {
            var $p = $(this);
            var id = 'transcript' + $p.data('start') + $p.data('end');
            $p.attr('id', id);
            times[id] = [$p.data('start'), $p.data('end')];
            ids.push(id);
        });

        setInterval(function() {
            if (player.getState() === 'playing') {
                var p = player.getPosition() * 1000;
                var found = false;
                $.each(times, function(id, startend) {
                    if (!found && p >= startend[0] && p < startend[1]) {
                        $('.transcript p.active').removeClass('active');
                        $('#' + id).addClass('active');
                        scrollFocus(id);
                    }
                });
            }
        }, 1000);
    };

    var attempts = 0;
    var waiter = setInterval(function() {
        if (typeof jwplayer === 'function' && typeof playerid !== 'undefined' && jwplayer(playerid).getState()) {
            trackTranscript(jwplayer(playerid));
            clearInterval(waiter);
        } else {
            attempts++;
            if (attempts > 4) {
                clearInterval(waiter);
            }
        }
    }, 1000);

});

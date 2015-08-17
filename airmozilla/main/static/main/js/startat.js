$(function() {
    var regex = /#@((\d{1,2})h)?((\d{1,2})m)?((\d{1,2})s)/;
    if (regex.test(location.hash)) {
        // convert this to a big number of seconds
        var matched = regex.exec(location.hash);
        var hours = parseInt(matched[2] || 0, 10);
        var minutes = parseInt(matched[4] || 0, 10);
        minutes += hours * 60;
        var seconds = parseInt(matched[6], 10);
        seconds += minutes * 60;
        var attempts = 0;
        var timer = setInterval(function() {
            if (typeof jwplayer === 'function') {
                clearInterval(timer);
                // it has fully loaded!
                var jwplayer_player = jwplayer();
                jwplayer_player.seek(seconds);  // this will start playing!
            } else if (attempts > 4) {
                // give up
                console.warn('No playable jwplayer to found to fast forward');
                clearInterval(timer);
            }
            attempts++;
        }, 1000);
    }

});

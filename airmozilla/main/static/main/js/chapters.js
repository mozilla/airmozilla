$(function() {
    var jwplayer_player = null;

    var attempts = 0;
    var waiter = setInterval(function() {
        if (typeof jwplayer === 'function' && jwplayer(playerid).getState()) {
            jwplayer_player = jwplayer();
            clearInterval(waiter);
        } else {
            attempts++;
            if (attempts > 4) {
                clearInterval(waiter);
            }
        }
    }, 1000);

    $('.chapters').on('click', 'a[data-ts]', function() {
        if (jwplayer_player !== null) {
            jwplayer_player.seek($(this).data('ts'));
        }
        return false;
    });
});

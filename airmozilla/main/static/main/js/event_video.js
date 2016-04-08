window.onload = function() {
    if (window.opener && typeof window.opener.popup_position !== 'undefined') {
        var position = window.opener.popup_position;
        // now we need to wait for jwplayer to be added to the global scope
        var attempts = 0;
        var waiter = setInterval(function() {
            if (typeof jwplayer === 'function' && jwplayer(playerid).getState()) {
                var player = jwplayer(playerid);
                clearInterval(waiter);
                player.on('ready', function(setupTime) {
                    if (position > 0) {
                        player.seek(position);
                    }
                    // update this windows location hash every second
                    if (window.opener) {
                        var updater = setInterval(function() {
                            if (player.getState() === 'complete') {
                                window.opener.popup_position = 0;
                            } else {
                                window.opener.popup_position = player.getPosition();
                            }
                        }, 500);
                    }
                });

            } else {
                attempts++;
                if (attempts > 100) {
                    clearInterval(waiter);
                    console.warn('Had to give up waiting for jwplayer(playerid)');
                }
            }
        }, 75);
    }
};


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


    /* Applicable if it's an upcoming event */
    initRefreshIn();
};


var initRefreshIn = function() {
    var upcoming = document.querySelector('.upcoming');
    if (!upcoming) {
        return;
    }
    var refreshIn = parseInt(upcoming.dataset.refreshIn, 10);
    if (!refreshIn) {
        return;
    }
    if (refreshIn < 0) {
        // it's too late
        return;
    }
    if (refreshIn > 60 * 60 * 24) {
        // it's too far into the future to set up a setTimeout
        return;
    }
    // The refreshIn is a number of seconds.
    // If many people sit and wait for an upcoming event to change
    // to a live one, to avoid a stampeding herd, add a litter
    // staggering which is going to be different for every user
    var randomStagger = Math.random() * 5; // seconds
    console.log(
        "This page will automatically refresh in " + refreshIn + " seconds"
    );
    setTimeout(function() {
        location.reload();
    }, (refreshIn + randomStagger) * 1000);
};

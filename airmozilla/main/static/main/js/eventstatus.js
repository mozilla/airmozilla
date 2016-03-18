$(function () {
    var container = $('.entry-content');

    function checkStatus() {
        return $.get(location.pathname + 'status/')
        .then(function (data) {
            if (container.data('event-status') !== data.status) {
                location.reload();
            }
        });
    }

    var CHECK_INTERVAL = 10;  // seconds

    if (typeof window.Fanout !== 'undefined') {
        Fanout.subscribe('/' + container.data('subscription-channel-status'), function() {
            // Supposedly the status has changed.
            // For security, let's not trust the data but just take it
            // as a hint that it's worth doing an AJAX query
            // now.
            checkStatus();
        });
        // In case fanout flakes out, still use the regular interval
        // but make it much less frequent.
        CHECK_INTERVAL = 60 * 5;
    }
    var interval = setInterval(function () {
        checkStatus()
        .fail(function () {
            console.warn("Failed to fetch event status. Stops looking.");
            clearInterval(interval);
        });
    }, CHECK_INTERVAL * 1000);


});

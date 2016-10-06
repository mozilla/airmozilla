$(function () {
    var refreshIn = $('.event-content').data('refresh-in');
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
    setTimeout(function() {
        location.reload();
    }, (refreshIn + randomStagger) * 1000);

});

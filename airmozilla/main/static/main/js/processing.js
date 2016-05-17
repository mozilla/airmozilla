/*global $ humanizeDuration */
/* This file is used to display a comforting message about the
transcoding progress. */

$(function() {
    var container = $('.processing');
    if (!container.length) {
        // If it's not in the state of processing, don't bother with
        // the rest of this file.
        return;
    }

    // This is the number of seconds the server things we have left.
    var timeLeft = container.data('time-left');
    var origTimeLeft = timeLeft;

    // This is the age of seconds since the processing started. This
    // is useful to show a percentage.
    var timeRun = container.data('time-run');
    var timeTotal = timeRun + origTimeLeft;

    var timeLeftOutput = $('.time-left b', container);
    var progressBar = $('.progress-bar progress', container);
    var progressValue = $('.progress-bar .progress-value', container);

    var showTimeLeft = function() {
        timeLeftOutput.text(humanizeDuration(timeLeft * 1000));
        var p = 100 * (timeRun + origTimeLeft - timeLeft) / timeTotal;
        progressBar
        .attr('value', p)
        .attr('title', parseInt(p, 10) + '%');
        progressValue.text(parseInt(p, 10) + '% transcoded');
    };

    var updateTimeLeft = function() {
        if (timeLeft < 0) {
            // something's really wrong.
            $('.time-left', container).hide();
            $('.progress-bar', container).hide();
            $('.time-overdue', container).fadeIn(400);
            // just give up!
            clearInterval(interval);
        } else {
            // all is well
            showTimeLeft();
        }
        timeLeft--;
    };
    // If there is actually a positive timeLeft, show the progress bar
    if (timeLeft > 0) {
        $('.time-left', container).fadeIn(400);
        $('.progress-bar', container).fadeIn(400);
    }
    updateTimeLeft();
    var interval = setInterval(updateTimeLeft, 1000);

});

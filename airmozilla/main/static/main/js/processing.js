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

    // How much the next picture should be shifted to the right
    var MARGIN_LEFT_OFFSET = 35;  // in pixels
    var MIN_MARGIN_TOP_DIFF = 0.2; // between 0 and 1
    // The max number of timenails to show depends on the max space
    // available (896px). We know the width of the whole container.
    // It's hard-coded.
    // And we have a margin (50px) for *all* timenails within that
    // container. On both sides. Next, we need to offset the width
    // of at least the last thumbnail (160px).
    // Every thumbnail also as a border (2px) which we need to offset for
    // Then, it's only a matter of how many can we fit and lastly
    // round down to the nearest integer.
    var MAX_TIMENAILS = Math.floor(
        (896 - 50 * 2 - 160) / (MARGIN_LEFT_OFFSET + 2)
    );
    // How much max, we let the rotation randomness is allowed to be.
    var MAX_ROTATION_PERCENT = 6; // %
    // How much max, we let the up and down is allowed to randomly be.
    var MAX_MARGIN_TOP_PERCENT = 30; // %
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

    var maxTimenails = null;
    var marginLeft = 0;
    var zIndex = 0;
    var odd = -1;
    var prevMarginTop = {};
    var allMarginTops = [];

    var updateTimenails = function() {
        var url = container.data('url-timenails');
        if (!url) {
            return;
        }
        var p = 100 * (timeRun + origTimeLeft - timeLeft) / timeTotal;

        var nextRotation = function(odd) {
            return odd * Math.random() * MAX_ROTATION_PERCENT;
        };
        var nextMarginTop = function(odd) {
            function getNext() {
                return parseInt(
                    odd * Math.random() * MAX_MARGIN_TOP_PERCENT,
                    10
                );
            }
            function getDiff(next) {
                return Math.abs(1 - next / prevMarginTop[odd]);
            }
            var next = getNext();
            if (prevMarginTop[odd]) {
                var diff = getDiff(next);
                // If the difference compared to the previous one
                // is less than 20%, get another one.
                // Or if the randomly picked marginTop has ever been used
                // before, then also get a different one.
                while (diff <= MIN_MARGIN_TOP_DIFF || allMarginTops.indexOf(next) > -1) {
                    next = getNext();
                    diff = getDiff(next);
                }
            }
            prevMarginTop[odd] = next;

            // remember all returned marginTops
            allMarginTops.push(next);
            // but only keep the last 6.
            allMarginTops = allMarginTops.slice(
                allMarginTops.length - 6, allMarginTops.length
            );
            return next;
        };
        if (maxTimenails === null) {
            // When it's the first time we run this function, we'll try to
            // load as many old/existing timenails as we can.
            maxTimenails = MAX_TIMENAILS;
        }
        $.getJSON(url, { percent: p, max: maxTimenails})
        .done(function(response) {
            if (response.pictures.length) {
                var subcontainer = $('.progress-timenails', container);
                var pictures = response.pictures;
                // If we'll now have MORE than MAX_TIMENAILS, we need to
                // remove some of the oldest ones and move all others
                // a bit to the left.
                while ($('img.timenail', subcontainer).length >= MAX_TIMENAILS) {
                    // Remove the oldest ones
                    $('img.timenail', subcontainer).first().remove();
                    $('img.timenail', subcontainer).each(function() {
                        var self = $(this);
                        var newMargin = self.data('margin-left') - MARGIN_LEFT_OFFSET;
                        self.css('margin-left', newMargin + 'px');
                        self.data('margin-left', newMargin);
                    });
                    marginLeft -= MARGIN_LEFT_OFFSET;
                }

                $.each(pictures, function(i, picture) {
                    // if it's already there, don't bother adding it again
                    if ($('#timenail' + picture.id).length) {
                        return;
                    }
                    odd *= -1;
                    marginTop = nextMarginTop(odd);
                    rotation = nextRotation(odd);
                    marginLeft += MARGIN_LEFT_OFFSET;
                    zIndex++;
                    $('<img>')
                    .attr('src', picture.thumbnail.url)
                    .attr('alt', picture.timestamp)
                    .attr('id', 'timenail' + picture.id)
                    .addClass('timenail')
                    .css('transform', 'rotate(' + rotation + 'deg)')
                    .css('z-index', zIndex)
                    .data('margin-left', marginLeft)
                    .css('margin-left', marginLeft + 'px')
                    .css('margin-top', marginTop + 'px')
                    .appendTo(subcontainer)
                    .fadeIn(600);
                });
                subcontainer.show();

                // This means that the next time, it's going to only
                // ask for 1 timenail. And it doesn't matter if it's
                // been received before.
                maxTimenails = 1;
            }
        })
        .error(function() {
            console.error.apply(console, arguments);
        });

    };

    var updateTimeLeft = function() {
        if (timeLeft < 0) {
            // something's really wrong.
            $('.time-left', container).hide();
            $('.progress-bar', container).hide();
            $('.time-overdue', container).fadeIn(400);
            // just give up!
            clearInterval(interval);
            clearInterval(timenailsInterval);
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

    // update every 30 seconds
    var timenailsInterval = setInterval(updateTimenails, 30 * 1000);
    // but start showing it with a slight delay
    setTimeout(updateTimenails, 3 * 1000);


});

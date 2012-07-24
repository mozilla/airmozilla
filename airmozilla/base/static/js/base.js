$(function() {
    'use strict';
    $('time.jstime').each(function(i, time) {
        // Find all relevant <time> elements and replace with formatted time.
        var $element = $(time);
        var datetime = $element.attr('datetime');
        var format = $element.attr('data-format');
        var parsed = moment(datetime);
        $element.text(parsed.format(format));
    });
    $.timeago.settings.allowFuture = true;
    $('time.timeago').timeago();

    $('button.cancel').click(function() {
        return confirm('Are you sure you want to cancel?');
    });
});

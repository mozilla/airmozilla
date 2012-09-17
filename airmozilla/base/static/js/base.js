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
        if (!$(this).parents('form').data('changes')) {
            return true;
        }
        return confirm('Discard changes without saving?');
    });

    // assume all forms to have 0 changes
    $('form').data('changes', 0);

    // register any change so we can't decide on needing a cancel dialog later
    $('input,textarea,select').change(function() {
        var form = $(this).parents('form');
        form.data('changes', form.data('changes') + 1);
    });

});

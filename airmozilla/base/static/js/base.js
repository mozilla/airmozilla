/*global $ moment confirm */

var AutoUpdateTime = (function() {
    var _selector;
    var _initial_time = (new Date()).getTime();

    function loop() {
        $(_selector).each(function() {
            var $element = $(this);
            var datetime = $element.attr('datetime');
            var format = $element.attr('data-format');
            var parsed = moment(datetime);
            var time_past = ((new Date()).getTime() - _initial_time) / 1000;
            parsed.add(time_past, 'seconds');
            $element.text(parsed.format(format));
        });
        setTimeout(loop, 60 * 1000);
    }
    return {
       init: function(selector) {
           _selector = selector;
           // it actually doesn't matter so much how often we loop
           // because it'll work based on `_initial_time` compared to now
           // but start a little earlier on the first one
           setTimeout(loop, 30 * 1000);
       }
    };
})();

function setupJSTime(container) {
    $.timeago.settings.allowFuture = true;
    $('time.jstime', container).each(function(i, time) {
        // Find all relevant <time> elements and replace with formatted time.
        var $element = $(time);
        var datetime = $element.attr('datetime');
        var format = $element.attr('data-format');
        var parsed = moment(datetime);
        $element.text(parsed.format(format));
    });
    $('time.timeago', container).timeago();
}
// make it available globally
window.setupJSTime = setupJSTime;

$(function() {
    'use strict';

    setupJSTime(document);
    AutoUpdateTime.init('time.autoupdate');
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

    $('.alert .close').click(function() {
        $(this).parent('.alert').fadeOut(400);
        return false;
    });

});

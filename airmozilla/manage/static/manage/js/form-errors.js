/*global $ */
$(function() {
    'use strict';
    $('div.error input, div.error textarea').change(function() {
        var container = $(this).parents('div.error');
        $('.help-inline', container).fadeOut(400);
        container.removeClass('error');
    });
});

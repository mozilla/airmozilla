$(function() {
    'use strict';

    $('table').on('click', 'a.expander', function() {
        var index = $(this).data('index');
        $('.glyphicon', this).toggle();
        $('pre.explanation-' + index).toggle();
        return false;
    });
});

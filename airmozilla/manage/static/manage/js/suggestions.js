/*global $:true */

$(function() {
    'use strict';

    if (location.hash.match(/#s\d+$/)) {
        var id = location.hash.replace(/[^\d]/g, '');
        $('tr').each(function() {
            if ($(this).data('id')== id) {
                $(this).effect('highlight', {}, 5000);
            }
        });
    }

});

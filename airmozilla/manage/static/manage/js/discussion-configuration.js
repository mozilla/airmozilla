$(function() {
    'use strict';

    // all the things we're going to do select2 on,
    // explicitely make sure they're 100%
    $('#id_moderators').css('width', '100%');

    $('#id_moderators').select2();
});

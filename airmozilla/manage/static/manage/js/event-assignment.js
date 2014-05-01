$(function() {
    'use strict';

    // all the things we're going to do select2 on,
    // explicitely make sure they're 100%
    $('#id_users, #id_locations').css('width', '100%');

    $('#id_users, #id_locations').select2();
});

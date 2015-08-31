/*global $:true */
$(function() {
    'use strict';

    $('#id_tags').css('width', '87%');

    var process_tags = function process_tags(element, callback) {
        var data = [];
        $(element.val().split(',')).each(function () {
            data.push({id: this, text: this});
        });
        callback(data);
    };

    // Autocomplete tags - uses the select2 library
    $('#id_tags').select2({
        tags: [],
        initSelection: process_tags
    });

    $.getJSON('/all-tags/')
    .then(function(response) {
        $('#id_tags').select2({tags: response.tags});
    }).fail(function() {
        console.log('Unable to download all tags');
        console.error.apply(console, arguments);
    });

    $('form[method="post"]').submit(function() {
        $('button', this).css('opacity', 0.6);
        $('.saving', this).show();
    });
});

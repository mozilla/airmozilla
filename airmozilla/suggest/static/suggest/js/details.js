/*global $:true */
$(function() {
    'use strict';

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
        ajax: {
            url: '/manage/tag-autocomplete',
            dataType: 'json',
            data: function (term, page) {
                return {q: term};
            },
            results: function (data, page) {
                return {results: data.tags};
            }
        },
        initSelection: process_tags
    });

    // Datetime picker (jQuery UI)
    $('#id_start_time').datetimepicker({
        stepHour: 1,
        stepMinute: 15,
        dateFormat: 'yy-mm-dd',
        timeFormat: 'HH:mm'
    });

    // Fill in the timezone from the selected location
    $('#id_location').select2();
    $('#id_location').bind('change', function() {
        $.getJSON('/manage/locations/tz/',
            {'location': $('#id_location').val()},
            function(data) {
                $('#id_timezone').select2('val', data.timezone);
            }
        );
    });
    $('#id_timezone').select2();
    $('#id_category').select2();
    $('#id_channels').select2();

});

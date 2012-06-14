$(function() {
    'use strict';
    // Autocomplete tags - uses the select2 library
    $('#id_tags').select2({
        tags: [],
        ajax: {
            url: '/manage/tag_autocomplete',
            dataType: 'json',
            data: function (term, page) {
                return {q: term};
            },
            results: function (data, page) {
                return {results: data.tags};
            }
        }
    });

    // Datetime picker (jQuery UI)
    $('#id_start_time').datetimepicker({
        stepHour: 1,
        stepMinute: 15,
        onClose: function(dateText, inst) {
            $('#id_end_time').datetimepicker('option',
                'minDate', new Date(dateText));
            $('#id_end_time').val(dateText);
        }
    });
    $('#id_end_time').datetimepicker({
        stepHour: 1,
        stepMinute: 15
    });
});

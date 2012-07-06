$(function() {
    'use strict';
    var process_tags = function process_tags(element) {
        var data = [];
        $(element.val().split(',')).each(function () {
            data.push({id: this, text: this});
        });
        return data;
    }
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
    });

    // Autocomplete participants (select2)
    $('#id_participants').select2({
        tags: [],
        ajax: {
            url: '/manage/participant-autocomplete',
            dataType: 'json',
            data: function (term, page) {
                return {q: term};
            },
            results: function(data, page) {
                return {results: data.participants};
            }
        },
        initSelection: process_tags
    });

    // Autofill template environments
    $('#id_template').change(function() {
        var selected = $('#id_template').val();
        if (selected) {
            $.getJSON('/manage/templates/env-autofill',
                {'template': selected},
                function(data) {
                    $('#id_template_environment').val(data['variables']);
                }
            );
        }
    });
});

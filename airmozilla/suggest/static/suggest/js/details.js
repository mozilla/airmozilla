/*global $:true */
$(function() {
    'use strict';

    $('#id_tags').css('width', '100%');
    $('#id_channels').css('width', '100%');
    $('#id_curated_groups').css('width', '100%');

    // Autocomplete tags - uses the select2 library
    $('#id_tags').select2({tags: true});

    $.getJSON('/all-tags/')
    .then(function(response) {
        $('#id_tags').select2({tags: response.tags});
    }).fail(function() {
        console.log('Unable to download all tags');
        console.error.apply(console, arguments);
    });

    $('#id_curated_groups').select2({
        placeholder: "Search for a Mozillians group",
        ajax: {
            url: '/curated-groups-autocomplete/',
            dataType: 'json',
            delay: 250,
            data: function(params) {
                return {q: params.term};
            },
            processResults: function(data, params) {
                var existing = $('#id_curated_groups').val();
                var results = [];
                var emails = [];
                $.each(data.groups, function(i, group) {
                    results.push({
                        id: group[0],
                        text: group[1],
                    });
                });
                return {
                    results: results,
                };
            },
            cache: true
        },
        minimumInputLength: 2,
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
    $('#id_channels').select2();

    $('div.select2-container').each(function() {
        var $controls = $(this).parents('.control-group');
        var help_text = $('p.help-block', $controls).text();

        if (help_text && $.trim(help_text)) {
            $(this).attr('title', help_text).tooltipster({
               position: 'right'
            });
        }
    });

    // The Curated Groups input is only applicable if you
    // select "Some Contributors" on the privacy field.
    var toggleCuratedGroupsInput = function() {
        if ($('#id_privacy').val() === 'some_contributors') {
            $('#id_curated_groups').parents('div.form-group').show();
        } else {
            $('#id_curated_groups').parents('div.form-group').hide();
        }
    };
    $('#id_privacy').on('change', toggleCuratedGroupsInput);
    // and onload
    toggleCuratedGroupsInput();

});

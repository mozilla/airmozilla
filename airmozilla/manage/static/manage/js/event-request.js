/*global $:true */

$(function() {
    'use strict';

    // all the things we're going to do select2 on,
    // explicitely make sure they're 100%
    $('#id_tags, #id_location,  #id_channels').css('width', '100%');

    // Autocomplete tags - uses the select2 library
    $('#id_tags').select2({
        tags: true,
    });
    $.getJSON('/all-tags/')
    .then(function(response) {
        $('#id_tags').select2({tags: response.tags});
    }).fail(function() {
        console.log('Unable to download all tags');
        console.error.apply(console, arguments);
    });

    // Datetime picker (jQuery UI)
    $('#id_start_time, #id_archive_time').datetimepicker({
        stepHour: 1,
        stepMinute: 15,
        dateFormat: 'yy-mm-dd',
        timeFormat: 'HH:mm'
    });

    // Slider for archive time (jQuery UI)
    var $archive_time_slider = $('#archive_time_slider');
    if ($archive_time_slider.length > 0) {
        var $id_archive_time = $('#id_archive_time');
        var $id_archive_time_parent = $id_archive_time.parent();
        $id_archive_time_parent.addClass('input-prepend');
        $id_archive_time.before('<span class="add-on">Now + </span>');
        $id_archive_time_parent.addClass('input-append');
        $id_archive_time.after('<span class="add-on"> minutes</span>');
        $('#id_archive_time').datetimepicker('destroy');
        $('#id_archive_time').val('90');
        $archive_time_slider.slider({
            min: 0,
            max: 240,
            value: 90,
            step: 5,
            range: 'min',
            slide: function(event, ui) {
                $('#id_archive_time').val(ui.value);
            }
        });
    }

    // Fill in the timezone from the selected location
    $('#id_location').select2();
    $('#id_channels').select2();

    // Autofill template environments
    $('#id_template').change(function() {
        var selected = $('#id_template').val();
        if (selected) {
            $.getJSON('/manage/templates/env-autofill/',
                {'template': selected},
                function(data) {
                    $('#id_template_environment').val(data.variables);
                }
            );
        }
    });

});

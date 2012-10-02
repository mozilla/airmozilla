$(function() {
    'use strict';
    $('#id_groups').change(function() {
        // if you select someone to be a group,
        // they have to be a staff member surely
        if (!$('#id_is_staff:checked').size() &&
            $('option:selected', this).size()) {
            $('#id_is_staff').trigger('click');
        }
    });
});

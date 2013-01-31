/*global $:true alert:true */
$(function() {
    'use strict';
    $('input[name="url"]').on('keypress', function() {
        $(this).val($(this).val().replace(' ', '-'));
    }).on('change', function() {
        if ($(this).val().substring(0, 8) === 'sidebar_') {
            if (!$('#id_title').val().length) {
                $('#id_title').val('(will be automatically set when you save)');
            }
        }
    });

    $('#content form[method="post"]').submit(function() {
        var url = $('input[name="url"]', this).val();
        if (!(url.charAt(0) == '/' || url.substring(0, 8) === 'sidebar_')) {
            alert("URL must start with a / or sidebar_");
            return false;
        }
        return true;
    });
});

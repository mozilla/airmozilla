/*global $:true alert:true */
$(function() {
    'use strict';
    $('input[name="url"]').on('keypress', function() {
        $(this).val($(this).val().replace(' ', '-'));
    });
    $('#content form[method="post"]').submit(function() {
        var url = $('input[name="url"]', this).val();
        if (url.charAt(0) != '/') {
            alert("URL must start with a /");
            return false;
        }
        return true;
    });
});

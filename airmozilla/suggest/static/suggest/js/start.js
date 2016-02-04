/*global $:true */

$(function() {
    'use strict';

    $('a.accepted-and-scheduled').each(function() {
        $('.hide-accepted-scheduled:hidden').show();
        $(this).parents('tr').addClass('accepted-scheduled').hide();
    });

    $('.hide-accepted-scheduled input[name="hide_accepted_scheduled"]').change(function() {
        $('tr.accepted-scheduled').toggle('slow');
    });

    function reset_buttons() {
        $('.delete-button:hidden').show();
        $('.delete-confirm-question:visible,' +
          '.delete-confirm:visible,' +
          '.delete-cancel:visible').hide();
    }

    $('.delete-button').click(function() {
        reset_buttons();
        var parent = $(this).parents('td.delete');
        $(this).hide();
        $('.delete-confirm-question,.delete-confirm,.delete-cancel', parent).show();
        return false;
    });

    $('.delete-confirm').click(function() {
        var parent = $(this).parents('td.delete');
        var delete_url = parent.data('delete-url');
        $.post(delete_url, function() {
            parent.parents('tr').remove();
        });
        return false;
    });

    $('.delete-cancel').click(function() {
        reset_buttons();
        return false;
    });

    $('#id_title').on('focus', function() {
        $('.start-tooltip:hidden').fadeIn(900);
    }).on('blur', function() {
        if (!$(this).val()) {
            $('.start-tooltip:visible').fadeOut(600);
        }
    });

});

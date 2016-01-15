/*global $:true */
$(function() {
    'use strict';

    $('#id_tags').css('width', '100%');
    $('#id_channels').css('width', '100%');
    $('#id_recruitmentmessage').css('width', '100%');

    // Autocomplete tags - uses the select2 library
    $('#id_tags').select2({tags: true});

    $.getJSON('/all-tags/')
    .then(function(response) {
        $('#id_tags').select2({tags: response.tags});
    }).fail(function() {
        console.log('Unable to download all tags');
        console.error.apply(console, arguments);
    });

    $('#id_channels').select2();
    $('#id_recruitmentmessage').select2();

    $('div.select2-container').each(function() {
        var $controls = $(this).parents('.control-group');
        var help_text = $('p.help-block', $controls).text();

        if (help_text && $.trim(help_text)) {
            $(this).attr('title', help_text).tooltipster({
               position: 'right'
            });
        }
    });

    var submitting = false;
    function _preSave($form) {
        $('.has-error .error-text', $form).remove();
        $('.has-error', $form).removeClass('has-error');
        $('.saving', $form).show();
        submitting = true;
    }

    $('form button[name="cancel"]').on('click', function(event) {
        event.preventDefault();
        location.href = $('form[data-eventurl]').data('eventurl');
    });

    $('form.event-edit').submit(function() {
        if (submitting) {
            console.warn('Accidental double-submit');
            return false;
        }
        _preSave($(this));
        return true;
    });

    function updatePlaceholderThumbnail(url) {
        var $parent = $('#id_placeholder_img').closest('.form-group');
        $('img', $parent).remove();
        $('<img>')
            .attr('src', url)
            .attr('alt', 'Existing picture')
            .attr('title', 'Existing picture')
            .addClass('existing-picture')
            .prependTo($parent);
    }

    if ($('form.event-edit').data('thumbnail-url')) {
        updatePlaceholderThumbnail($('form.event-edit').data('thumbnail-url'));
    }

    function updateConflictErrors($form, conflict_errors) {
        $.each(conflict_errors, function(i, name) {
            var $input = $('[name="' + name + '"]');
            if ($input.length) {
                var $parent = $input.closest('.form-group').addClass('has-error');
                $('<li>')
                    .text($parent.find('label').text())
                    .appendTo($('.conflict-errors'));
            } else {
                console.warn('Unable to find ', name);
            }
        });
    }

    if ($('form.event-edit').data('conflict-errors')) {
        updateConflictErrors(
            $('form.event-edit'),
            $('form.event-edit').data('conflict-errors')
        );
    }
});

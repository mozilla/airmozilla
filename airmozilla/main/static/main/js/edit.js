/*global $:true */
$(function() {
    'use strict';

    $('#id_tags').css('width', '100%');
    $('#id_channels').css('width', '100%');

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

    var submitting = false;
    function _preSave($form) {
        $('.has-error .error-text', $form).remove();
        $('.has-error', $form).removeClass('has-error');
        $('.saving', $form).show();
        submitting = true;
    }

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

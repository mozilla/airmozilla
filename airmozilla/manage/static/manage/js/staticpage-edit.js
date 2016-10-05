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

    if (FancyEditor.isEnabled('staticpage-edit')) {
        var $field = $('#id_content').hide();
        var $editor = $('<div>').attr('id', 'editor').text('\n');

        $('<div>')
          .addClass('editor-container')
          .append($editor)
          .insertBefore($field);

        var editor = ace.edit("editor");
        editor.setTheme("ace/theme/textmate");
        editor.setShowPrintMargin(false);
        var headers = $('#id_headers').val();
        if (headers.search('Content-Type: application/javascript') > -1) {
            editor.getSession().setMode("ace/mode/javascript");
        } else if (headers.search('Content-Type: application/xml') > -1) {
            editor.getSession().setMode("ace/mode/xml");
        } else if (headers.search('Content-Type: application/json') > -1) {
            editor.getSession().setMode("ace/mode/json");
        } else {
            editor.getSession().setMode("ace/mode/html");
        }
        editor.setValue($field.val());
        // otherwise it starts all selected
        editor.selection.clearSelection();

        $('form[method="post"]').submit(function() {
            $('#id_content').val(editor.getValue());
        });
    }

});

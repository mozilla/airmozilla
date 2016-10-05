$(function() {
    'use strict';

    if (FancyEditor.isEnabled('template-edit')) {
        var $field = $('#id_content').hide();
        var $editor = $('<div>').attr('id', 'editor').text('\n');

        $('<div>')
          .addClass('editor-container')
          .append($editor)
          .insertBefore($field);

        var editor = ace.edit("editor");
        editor.setTheme("ace/theme/textmate");
        editor.setShowPrintMargin(false);
        editor.getSession().setMode("ace/mode/html");
        editor.setValue($field.val());
        // otherwise it starts all selected
        editor.selection.clearSelection();

        $('form[method="post"]').submit(function() {
            $('#id_content').val(editor.getValue());
        });
    }

});

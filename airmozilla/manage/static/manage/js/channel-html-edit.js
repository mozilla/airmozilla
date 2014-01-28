$(function() {
    var $field = $('#id_description').parents('div.form-group').hide();
    var $editor = $('<div>').attr('id', 'editor').text('\n');

    var $container = $('<div>')
      .addClass('editor-container')
      .append($editor)
      .insertBefore($('.form-buttons'));

    var editor = ace.edit("editor");
    editor.setTheme("ace/theme/textmate");
    editor.getSession().setMode("ace/mode/html");

    editor.setValue($('#id_description').val());

    $('form[method="post"]').submit(function() {
        $('#id_description').val(editor.getValue());
    });

});

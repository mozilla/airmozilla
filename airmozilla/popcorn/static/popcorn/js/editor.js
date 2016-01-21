$(document).ready(function () {
    PopcornEditor.listen(PopcornEditor.events.loaded, function () {
        $.get($('#editor').data('url'), {
            slug: $('#editor').data('slug')
        })
        .done(function (response) {
            if(response.data) {
                PopcornEditor.loadInfo(response.data);
            }
            else {
                PopcornEditor.loadInfo(
                    PopcornEditor.createTemplate(response.metadata)
                );
            }
        })
        .fail(function() {
            console.warn("Unable to load popcorn data :(");
            console.error.apply(console, arguments);
        });
    });
    // Initialize the editor with the div id and path to Popcorn Editor.
    PopcornEditor.init('editor', window.POPCORN_EDITOR_CDN_URL + '/PopcornEditor/editor.html');
    PopcornEditor.listen('save', function (message) {
        $.post($('#editor').data('save'), {
            data: JSON.stringify(message),
            slug: $('#editor').data('slug'),
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        })
        .done(function (response) {
            document.location = '/popcorn/status/' + $('#editor').data('slug');
        })
        .fail(function () {
            console.warn('Unable to save edit :(');
            console.error.apply(console, arguments);
        });
    });
});

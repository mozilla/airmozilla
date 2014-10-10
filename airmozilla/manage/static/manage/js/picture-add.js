Dropzone.autoDiscover = false;

$(function() {
    var form_id = '#picture-dropzone';
    var dropzone = new Dropzone(form_id);
    dropzone.options.acceptedFiles = 'image/png,image/jpeg';
    dropzone.options.addRemoveLinks = true;

    dropzone.on('removedfile', function(file) {
        var $form = $(form_id);
        var data = {
            'remove': true,
            'name': file.name,
            'size': file.size,
            'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]', $form).val()
        };
        $.post($form.attr('action'), data).then(function(removed) {
            console.log("Removed?", removed);
        });

        // console.log(file.name, file.size);
    });
});

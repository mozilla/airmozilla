$(function() {
    $('#id_channels_include, #id_channels_exclude')
    .css('width', '100%')
    .select2();

    $('#id_tags_include, #id_tags_exclude')
    .css('width', '100%')
    .select2({tags: true});

    $.getJSON('/all-tags/')
    .then(function(response) {
        $('#id_tags_include, #id_tags_include').select2({tags: response.tags});
    }).fail(function() {
        console.log('Unable to download all tags');
        console.error.apply(console, arguments);
    });

    $('form[method="post"]').submit(function() {
        $('.saving').show();
    });

    if ($('.findable').length) {
        $.getJSON('.', {sample: true})
        .then(function(r) {
            $('.findable span.findingout')
            .addClass('number')
            .removeClass('findingout')
            .text(r.events);
            $('.findable').show(300);
        })
        .fail(function() {
            console.error.apply(console, arguments);
            $('.findable').hide();
        });
    }

});

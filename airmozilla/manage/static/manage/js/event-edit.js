/*global $:true process_vidly_status_response:true */


$(function() {
    'use strict';
    // Previously checked approval groups can not be unchecked
    $('input[name="approvals"]:checked').each(function() {
        $(this)
          .attr('disabled', 'disabled')
          .attr('title', "You can't uncheck previously requested approvals")
          .parents('label')
            .addClass('un-uncheckable')
            .append($('<small>').text("(Once checked, you can't uncheck it)"));
    });

    if ($('#vidly-submission').length) {
        var $element = $('#vidly-submission');
        $.ajax({
          url: '/manage/vidly/status/',
          data: {id: $element.data('id')},
          success: function(response) {
              process_vidly_status_response(response, $element);
          }
        });
    }

    $('#id_recruitmentmessage').select2();
    $('#id_curated_groups').select2({
        placeholder: "Search for a Mozillians group",
        ajax: {
            // url: $('#id_emails').data('autocomplete-url'),
            url: '/manage/curated-groups-autocomplete/',
            dataType: 'json',
            delay: 250,
            data: function(params) {
                return {q: params.term};
            },
            processResults: function(data, params) {
                var existing = $('#id_curated_groups').val();
                var results = [];
                var emails = [];
                $.each(data.groups, function(i, group) {
                    results.push({
                        id: group[0],
                        text: group[1],
                    });
                });
                return {
                    results: results,
                };
            },
            cache: true
        },
        minimumInputLength: 2,
    });

    // due to our integration with bootstrap 3 we have to do this to all select2 widgets
    $('#id_curated_groups').css('width', '100%');
    $('#id_recruitmentmessage').css('width', '100%');

    // Do these additional things a little bit later so the page
    // has a chance to settle first
    setTimeout(function() {
        // first one
        var url = $('#privacy-vidly-mismatch').data('url');
        $.getJSON(url)
        .then(function(response) {
            if (response) {
                $('#privacy-vidly-mismatch').fadeIn(800);
            }
        });

        // next one
        url = $('#template-environment-mismatch').data('url');
        $.getJSON(url)
        .then(function(response) {
            if (response) {
                $('#template-environment-mismatch a.link')
                .attr('href', response.url);
                $('#template-environment-mismatch').fadeIn(800);
            }
        });

        // We might consider putting these in sequence later.
    }, 1000);


    $('a.really-delete').click(function() {
        $('.really-delete-metadata').toggle();
        $('.really-delete-confirmation').toggle();
        return false;
    });
    $('.really-delete-confirmation a.cancel').click(function() {
        $('.really-delete-metadata').toggle();
        $('.really-delete-confirmation').toggle();
        return false;
    });
});

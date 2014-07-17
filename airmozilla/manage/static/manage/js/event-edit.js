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

    // Curated groups is only available during event edit
    // Autocomplete curated groups
    function process_curated_groups(element, callback) {
        var data = [];
        $(element.val().split(',')).each(function () {
            data.push({id: this, text: this});
        });
        console.log('process_curated_groups');console.dir(data);
        callback(data);
    }

    $('#id_recruitmentmessage').select2();
    $('#id_curated_groups').select2({
        placeholder: "Search for a Mozillians group",
        tags: [],
        minimumInputLength: 2,
        ajax: {
            url: '/manage/curated-groups-autocomplete/',
            dataType: 'json',
            data: function (term, page) {
                return {q: term};
            },
            results: function (data, page) {
                //console.log('DATA');
                //console.dir(data);
                var rows = [];
                $.each(data.groups, function(i, group) {
                    rows.push({id: group[0], text: group[1]});
                });
                return {results: rows};
            },
        },
        formatSelection: function(object) {
            console.log('OBJECT', object);
            return object.id;
        },
        xxxmatcher: function (term, text, option) {
            console.log('term', term, 'text', text);
            return false;
        },
        initSelection: process_curated_groups
    });

    // due to our integration with bootstrap 3 we have to do this to all select2 widgets
    $('#id_curated_groups').css('width', '100%');
    $('#id_recruitmentmessage').css('width', '100%');


});

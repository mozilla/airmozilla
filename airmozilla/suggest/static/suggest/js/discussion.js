$(function() {

    function process_emails(element, callback) {
        var data = [];
        var emails = [];
        var first = true;
        var disabled = true;
        $.each(element.val().trim().split(','), function(i, email) {
            email = email.trim();
            if ($.inArray(email, emails) > -1) {
                return;
            }
            if (first) {
                disabled = true;
                first = false;
            } else {
                disabled = false;
            }
            data.push({id: email, text: email, disabled: disabled});
            emails.push(email);
        });
        callback(data);
    }

    $('#id_emails')
        .css('width', '100%')
        .select2({
            tags: [],
            ajax: {
                url: $('#id_emails').data('autocomplete-url'),
                dataType: 'json',
                data: function(term) {
                    return {q: term};
                },
                results: function(data) {
                    var options = [];
                    $.each(data.emails, function(i, email) {
                        options.push({id: email, text: email});
                    });
                    return {results: options};
                }
            },
            initSelection: process_emails
        });

    $('#id_enabled').change(function() {
        if (this.checked) {
            $('.disabled').removeClass('disabled');
        } else {
            $('.form-group').each(function() {
                console.log($('#id_enabled', this));
                if (!$('#id_enabled', this).length) {
                    $(this).addClass('disabled');
                }
            });
        }
    }).change();
});

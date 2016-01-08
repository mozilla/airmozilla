$(function() {

    $('#id_emails')
        .css('width', '100%')
        .select2({
            ajax: {
                url: $('#id_emails').data('autocomplete-url'),
                dataType: 'json',
                delay: 250,
                data: function(params) {
                    return {q: params.term};
                },
                processResults: function(data, params) {
                    var existing = $('#id_emails').val();
                    var results = [];
                    var emails = [];
                    $.each(data.emails, function(i, email) {
                        email = email.trim();
                        if ($.inArray(email, existing) > -1) {
                            return;
                        }
                        results.push({
                            id: email,
                            text: email,
                        });
                    });
                    return {
                        results: results,
                    };
                },
                cache: true
            },
            minimumInputLength: 1,
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

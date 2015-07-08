$(function() {
    var $survey = $('#survey');
    if (!$survey.length) {
        return;
    }

    $('#survey').on('click', 'input[type="submit"]', function(event) {
        $('#survey .submission').hide();
        $('#survey .loading').show();
        var data = $('#survey form').serializeObject();
        var clicked = $(event.target);
        if (clicked.attr('name')) {
            data[clicked.attr('name')] = clicked.val();
        }
        $.post(url, data)
        .then(load)
        .fail(function() {
            $('#survey .inner').empty();
            $('#survey .error').fadeIn(200);
        });
        return false;
    });

    $('#survey').on('click', '.error', load);

    var url = $survey.data('load-url');
    function load() {
        $('#survey .error').hide();
        $.ajax({
            url: url,
            dataType: 'html'
        }).then(function(response) {
            $('#survey .inner').empty();
            $('#survey .inner').append(response);
            $('#survey').fadeIn(200);
        }).fail(function() {
            console.warn('Failed to load survey');
            console.warn(arguments);
        });
    }
    load();

    $.fn.serializeObject = function() {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function() {
            if (o[this.name] !== undefined) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                o[this.name].push(this.value || '');
            } else {
                o[this.name] = this.value || '';
            }
        });
        return o;
    };
});

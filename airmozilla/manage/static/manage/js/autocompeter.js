$(function() {
    $('form.stats').on('submit', function() {
        $('form.stats pre').show();
        $.getJSON($(this).data('url'))
        .then(function(response) {
            console.log(response);
            $('form.stats pre').text(JSON.stringify(response, undefined, 4));
        })
        .fail(function() {
            console.error(arguments);
            $('form.stats pre').text('Error downloading.');
        });
        return false;
    });

    $('form.test').on('submit', function() {
        $('form.test pre').show();
        data = {
            'term': $('form.test input[type="text"]').val(),
        };
        $.getJSON($(this).data('url'), data)
        .then(function(response) {
            $('form.test pre').text(JSON.stringify(response, undefined, 4));
        })
        .fail(function() {
            console.error(arguments);
            $('form.test pre').text('Error testing.');
        });
        return false;
    });
});

$(function() {
    $('.open-download').click(function(event) {
        event.preventDefault();
        $('.download, .close-download').show();
        $('.open-download').hide();
    });

    $('.close-download').click(function(event) {
        event.preventDefault();
        $('.download, .close-download').hide();
        $('.open-download').show();
    });

});

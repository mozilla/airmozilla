$(function() {
    $('.open-embed').click(function(event) {
        event.preventDefault();
        $('.embed, .close-embed').show();
        $('.open-embed').hide();
    });

    $('.close-embed').click(function(event) {
        event.preventDefault();
        $('.embed, .close-embed').hide();
        $('.open-embed').show();
    });

    $('.embed textarea').on('focus', function() {
        this.select();
    });

});

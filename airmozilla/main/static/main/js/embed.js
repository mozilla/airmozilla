$(function() {
    $('.embed a.open').click(function(event) {
        event.preventDefault();
        $('.embed .code').show();
        $(this).parents('p').addClass('hidden');
    });

    $('.embed a.close').click(function(event) {
        event.preventDefault();
        $('.embed .hidden').removeClass('hidden');
        $('.embed .code').hide();
    });

    $('.embed textarea').on('focus', function() {
        this.select();
    });

});

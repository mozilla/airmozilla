$(function() {
    $('li.has-sub-items > a').on('click', function() {
        $('.sub-options').hide();
        $('.sub-options', $(this).parents('li')).fadeIn(250);
        return false;
    });
    $('#page').on('click', function() {
        $('.sub-options').hide();
    });
    $('.sub-options a.close').on('click', function() {
        $('.sub-options', $(this).parents('li.has-sub-items')).fadeOut(250);
        return false;
    });
});

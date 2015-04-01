$(function() {
    var open = false;
    $('#nav-new > a').on('click', function() {
        $('#nav-new .sub-options').toggle();
        open = !open;
        return false;
    });
    $('#page').on('click', function() {
        if (open) {
            $('#nav-new > a').click();
        }
    });
    $('#nav-new .sub-options a.close').on('click', function() {
        $('#nav-new > a').click();
        return false;
    });
});

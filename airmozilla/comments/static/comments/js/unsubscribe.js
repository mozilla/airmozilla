$(function() {
    $('input[name="cancel"]').click(function() {
        if ($('a.event').length) {
            location.href = $('a.event').attr('href');
        } else {
            location.href = '/';
        }
        return false;
    });
});

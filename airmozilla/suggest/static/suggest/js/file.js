$(function() {
    $('input[name="upload"]').change(function() {
        $('li.selected').removeClass('selected');
        if (this.checked) {
            $(this).parents('li').addClass('selected');
        }
    });
    $('input[name="upload"]').change();
});

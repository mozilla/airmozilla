$(function() {
    $('input[name="hideequals"]').on('change', function() {
        if (this.checked) {
            $('#durations tbody tr').hide();
            $('td a.different').parents('tr').show();
        } else {
            $('#durations tr').show();
        }
    });
});

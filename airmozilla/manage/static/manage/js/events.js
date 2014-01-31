$(function() {
    var opts = {format: 'yyyy-mm-dd'};
    $('#dp_start_time')
        .datepicker(opts)
        .on('changeDate', function(ev) {
            // so that angular's $scope is updated
            $(this).change();
            $(this).datepicker('hide');
        });
});

$(function() {
    var config = $('autocompeter');
    if (config.length) {
        var options = {};
        if (config.data('url')) {
            options.url = config.data('url');
        }
        if (config.data('groups')) {
            options.groups = config.data('groups');
        }
        if (config.data('domain')) {
            options.domain = config.data('domain');
        }
        Autocompeter(document.getElementById('id_q'), options);
    }
});

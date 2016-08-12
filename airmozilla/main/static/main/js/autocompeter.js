$(function() {
    if (typeof Autocompeter === 'undefined') {
        // If it doesn't exist it's most likely because the network
        // failed on us. Don't let this be a blocker.
        return;
    }
    var config = $('autocompeter-config');
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

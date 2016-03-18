window.Fanout = (function() {
    var _loaded = false;
    var _client = null;
    var _locks = {};
    var config = $('fanout');

    var loadJS = function loadJS(cb) {
        if (_loaded) {
            return cb();
        }
        var script = document.createElement('script');
        script.onload = function() {
            loaded = true;
            cb();
        };
        script.src = config.data('js-url');
        document.head.appendChild(script);
    };

    return {
        /* This function wraps fanout's client. The purpose is to have throttle
        the callbacks. It's not unrealistic that the server side will fire
        events repeatedly. Because often the events are fired by ORM signals.
        */
        subscribe: function(channel, cb) {
            loadJS(function() {
                if (_client === null) {
                    _client = new Faye.Client(config.data('client-url'));
                }
                _client.subscribe(channel, function(data) {
                    if (_locks[channel]) {
                        // throttled
                        return;
                    }
                    _locks[channel] = true;
                    cb(data);
                    setTimeout(function() {
                        _locks[channel] = false;
                    }, 500);
                });
            });

        }
    };
})();

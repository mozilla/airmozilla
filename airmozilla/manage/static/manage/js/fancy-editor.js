window.FancyEditor = function() {

    function getCacheKey(context) {
        if (context) {
            currentContext = context; // store this for later use
        } else {
            context = currentContext;  // use the previously stored
        }
        return 'use-fancy-editor:' + context;
    }

    function isDisabled(context) {
        var cacheKey = getCacheKey(context);
        return localStorage.getItem(cacheKey);
    }

    function toggle(context) {
        var cacheKey = getCacheKey(context);
        if (localStorage.getItem(cacheKey)) {
            localStorage.removeItem(cacheKey);
        } else {
            localStorage.setItem(cacheKey, true);
        }
    }

    $('button.ace-enable, button.ace-disable').on('click', function(event) {
        event.preventDefault();
        toggle();
        location.reload();
    });

    var currentContext = null;

    return {
        isEnabled: function(context) {
            var cacheKey = getCacheKey(context);
            var disabled = localStorage.getItem(cacheKey);
            if (disabled) {
                $('button.ace-enable').show();
                $('button.ace-disable').hide();
            } else {
                $('button.ace-enable').hide();
                $('button.ace-disable').show();
            }
            return !disabled;
        }
    };
}();

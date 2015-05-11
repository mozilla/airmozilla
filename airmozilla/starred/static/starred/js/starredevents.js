var EventLoader = (function() {
    var container = $('#events');

    // If you're signed in, it won't start the page with an AJAX load
    // so there's no point ever showing the loading notice.
    var shownLoadingNotice = Stars.isSignedIn();

    return {
        load: function() {
            var stars = Stars.getStars();
            if (stars.length === 0) {
                $('.no-stars').show();
                container.hide();
            } else {
                $('.no-stars').hide();
                var url = window.location.pathname;
                if (!Stars.isSignedIn()) {
                    url += '?ids=' + stars.join(',');
                }
                if (!shownLoadingNotice) {
                    // The "please wait" message should only ever be shown
                    // once. It's only useful to our users when the arrive
                    // on the Starred page with NOTHING to display.
                    //
                    // Suppose instead, after some time, they have events
                    // displayed and decide to un-star one of them. When
                    // they do that, the page will AJAX re-load and replace
                    // the content of the container with events (except
                    // now with one event less).
                    $('.loading-stars').show();
                    shownLoadingNotice = true;
                }
                container.load(url, function() {
                    // Most of the time it's already hidden (e.g. when
                    // un-starring) but this operation is quicker than
                    // doing something like `$('.loading-stars:visible').hide()`
                    $('.loading-stars').hide();
                    $('a.star').each(function(i, element){
                        Stars.setToolTip(element);
                    });
                }).show();
            }
        }
    };
}());

$(function() {
    if (!Stars.isSignedIn()) {
        EventLoader.load();
    }
    Stars.registerPostSync(EventLoader.load);
});

var EventLoader = (function() {
    var container = $('#events');
    return {
        load: function() {
            var stars = Stars.getStars();
            if (stars.length === 0) {
                container.html($( '.no-stars' ).clone().toggleClass('no-stars').show());
            }
            else {
                var url = window.location.pathname;
                if (!Stars.isSignedIn()) {
                    url = url + '?ids=' + stars.join(',');
                }
                container.load(url);
            }
        }
    }
}());

$(function() {
    EventLoader.load();
    Stars.registerPostSync(EventLoader.load);
});

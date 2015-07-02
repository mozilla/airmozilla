$(function() {

    var url = window.location.pathname + 'related-content/';

    $('#content-sub').load(url, function(response) {
        if ($('#content-sub article').length) {
            // new HTML contains <time> tags that need the jQuery timeago
            // functionality added to them.
            setupJSTime('#content-sub');
            $('#content-sub').show();
        } else {
            $('#content-sub').hide();
        }

    });

});

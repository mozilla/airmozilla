window.Stars = (function() {
    var stars = [],
        csrfToken, signedIn, postSyncCallback = false;


        function sync() {
            if (!signedIn) {
                if (postSyncCallback) {
                    postSyncCallback();
                }
            }
            else {
                $.post($('starred-event').data('post'), $.param( {
                    'ids': stars,
                    'csrfmiddlewaretoken': csrfToken
                }, true))
                .then( function(response) {
                    if (response) {
                        csrfToken = response.csrf_token;
                        stars = response.ids;
                        stars = stars.slice(0, 500);
                        localStorage.setItem('stars', JSON.stringify(stars));
                        if (postSyncCallback) {
                            postSyncCallback();
                        }
                    }
                });
            }
        }

        function triggerClickedStars() {
            $('a.star').each(function(i, element) {
                var $element = $(element);
                var index = stars.indexOf($element.data('id'));
                if (index > -1) {
                    $element.addClass('star-on');
                }
                Stars.setToolTip($element);
            });
        }

    return {

        registerPostSync: function (callback) {
            postSyncCallback = callback;
        },

        getStars: function () {
            return stars;
        },

        initialSync: function () {
            signedIn = !!$('starred-event').length;
            var fromBrowser = localStorage.getItem('stars');

            if (fromBrowser) {
                stars = JSON.parse(fromBrowser);
                triggerClickedStars();
            }

            if (signedIn) {
                // then the <starred-event> tag would have the list of ids
                var serverStars = [];
                var ids = $('starred-event').data('ids').toString();
                if (ids.length) {
                    ids.split(',').forEach(function(id) {
                        serverStars.push(parseInt(id, 10));
                    });
                }
                csrfToken = $('starred-event input[name="csrfmiddlewaretoken"]').val();
                // jquery array comparison http://stackoverflow.com/a/7726509/205832
                if (!($(stars).not(serverStars).length === 0 &&
                      $(serverStars).not(stars).length === 0)) {
                    stars = stars.concat(serverStars);
                    triggerClickedStars();
                    sync();
                }
            }
        },

        isSignedIn: function () {
            return !!$('starred-event').length;
        },

        toggleArrayPresence: function (id) {
            var index = stars.indexOf(id);
            if (index > -1) {
                stars.splice(index, 1);
            } else {
                stars.unshift(id);
            }
            stars = stars.slice(0, 500);
            localStorage.setItem('stars', JSON.stringify(stars));
            sync();
        },

        setToolTip: function ($element) {
            var title;
            if ($element.hasClass('star-on')) {
                title = $element.data('star-on');
            } else {
                title = $element.data('star-off');
            }
            $element.attr('title', title);
        }
    };
}());

$(function() {

    $('#content').on('click', 'a.star', function () {
        var id = $(this).data('id');
        var modified = $('a.star[data-id=' + id + ']');
        modified.toggleClass('star-on');
        modified.each(function(_, e) {
            Stars.setToolTip($(e));
        });
        Stars.toggleArrayPresence(id);
    });

    Stars.initialSync();
});

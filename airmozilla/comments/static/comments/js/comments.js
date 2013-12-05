var RELOAD_INTERVAL = 5;  // seconds

var Comments = (function() {

    var since = null;
    var halt_reload_loop = false;
    var pause_reload_loop = false;

    function approve_comment(clicked, container) {
        var parent = $(clicked).closest('.comment');
        var data = {
            approve: parent.data('id'),
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', container).val()
        };
        var req = $.post(container.data('url'), data);
        req.done(function(response) {
            if (response.ok) {
                $('a.action-approve', parent).hide();
                $('.not-approved', parent).fadeOut(300);
                $('a.action-unapprove', parent).show();
            } else {
                alert("Sorry. Unable to approve this comment at the moment.");
            }
        });
        req.fail(function() {
            alert("Sorry. An error happened trying to approve this. Please try again later.");
        });
    }

    function unapprove_comment(clicked, container) {
        var parent = $(clicked).closest('.comment');
        var data = {
            unapprove: parent.data('id'),
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', container).val()
        };
        var req = $.post(container.data('url'), data);
        req.done(function(response) {
            if (response.ok) {
                $('a.action-approve', parent).show();
                $('a.action-unapprove', parent).hide();
                $('.not-approved', parent).fadeIn(300);
            } else {
                alert("Sorry. Unable to unapprove this comment at the moment.");
            }
        });
        req.fail(function() {
            alert("Sorry. An error happened trying to approve this. Please try again later.");
        });
    }

    function remove_comment(clicked, container) {
        var parent = $(clicked).closest('.comment');
        var data = {
            remove: parent.data('id'),
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', container).val()
        };
        var req = $.post(container.data('url'), data);
        req.done(function(response) {
            if (response.ok) {
                parent.fadeTo(200, 0.1, function() {
                    $(this).html('Comment removed').addClass('removed-pending').fadeTo(100, 1.0);
                    setTimeout(function() {
                        $('.removed-pending').fadeOut(500).remove();
                    }, 5 * 1000);
                });
            } else {
                alert("Sorry. Unable to remove this comment at the moment.");
            }
        });
        req.fail(function() {
            alert("Sorry. An error happened trying to remove this. Please try again later.");
        });
    }

    function flag_comment(clicked, container) {
        var parent = $(clicked).closest('.comment');
        var data = {
            flag: parent.data('id'),
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', container).val()
        };
        var req = $.post(container.data('url'), data);
        req.done(function(response) {
            if (response.ok) {
                $('a.action-flag', parent).hide();
                $('a.action-unflag', parent).show();
                $('.flagged-by-user', parent).show();
                $('.flagged', parent).fadeIn(300);
            } else {
                alert("Sorry. Unable to flag this comment at the moment.");
            }
        });
        req.fail(function() {
            alert("Sorry. An error happened trying to flag this. Please try again later.");
        });
    }

    function unflag_comment(clicked, container) {
        var parent = $(clicked).closest('.comment');
        var data = {
            unflag: parent.data('id'),
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', container).val()
        };
        var req = $.post(container.data('url'), data);
        req.done(function(response) {
            if (response.ok) {
                $('a.action-unflag', parent).hide();
                $('.unflagged-by-user', parent).show();
                $('.flagged', parent).fadeOut(300);
            } else {
                alert("Sorry. Unable to unflag this comment at the moment.");
            }
        });
        req.fail(function() {
            alert("Sorry. An error happened trying to unflag this. Please try again later.");
        });
    }

    return {
        load: function(container, callback) {
            console.log('LOAD');
            var req = $.getJSON(container.data('url'));
            req.then(function(response) {
                if (!response.discussion.enabled) {
                    container.remove();
                    console.log('Discussion not enabled on this page');
                    return;
                }
                since = response.latest_comment;
                $('.comments-outer', container).html(response.html).show();
                $('time.timeago', container).timeago();
                $('a.permalink', container).click(function() {
                    $(this).closest('.comment').addClass('focus-on');
                    setTimeout(function() {
                        $('.focus-on').removeClass('focus-on');
                    }, 500);
                });
                $('a.action-reply', container).click(function() {
                    var parent = $(this).closest('.comment');
                    $('form input[name="reply_to"]', container).val(parent.data('id'));
                    // put the comment form under this
                    var comment_container = $(this).closest('.comment');
                    $('form', container).detach().appendTo(comment_container);
                    $('form button.cancel', container).show();
                    return false;
                });
                $('a.action-approve', container).click(function() {
                    approve_comment(this, container);
                    return false;
                });
                $('a.action-unapprove', container).click(function() {
                    unapprove_comment(this, container);
                    return false;
                });
                $('a.action-remove', container).click(function() {
                    remove_comment(this, container);
                    return false;
                });
                $('a.action-flag', container).click(function() {
                    flag_comment(this, container);
                    return false;
                });
                $('a.action-unflag', container).click(function() {
                    unflag_comment(this, container);
                    return false;
                });
                $('.failed-loading:visible', container).hide();
                if (callback) callback();
            });
            req.fail(function() {
                $('.failed-loading', container).fadeIn(300);
            });
            req.always(function() {
                $('.loading', container).remove();
            });
        },
        reload_loop: function(container) {
            if (halt_reload_loop || pause_reload_loop) {
                return;
            }
            var data = {since: since};
            var req = $.getJSON(container.data('reload-url'), data);
            req.then(function(response) {
                console.log('New latest_comment', response.latest_comment);
                if (response.latest_comment) {
                    since = response.latest_comment;
                    Comments.load(container);
                }
            });
            req.fail(function() {
                console.warn('Error checking latest, so halt');
                halt_reload_loop = true;
            });
            console.log('SINCE=', since);
        },
        pause_loop: function() {
            pause_reload_loop = true;
        },
        resume_loop: function() {
            pause_reload_loop = false;
        }
    };
})();

(function(window, $) {
    "use strict";

    $(function() {
        var container = $('#comments');
        if (!container.length) {
            console.log('No #comments container on this page');
            return;
        }
        if (!$('input[name="name"]', container).val()) {
            // fetch the name async
            var element = $('input[name="name"]', container);
            $.getJSON(element.data('url')).then(function(response) {
                if (response.name) {
                    element.val(response.name);
                }
            });
        }
        Comments.load(container, function() {
            if (location.hash && location.hash.search(/#comment-\d+/) > -1) {
                // we should find a permalink with this href
                $('a.permalink', container).each(function(i, each) {
                    if ($(each).attr('href') === location.hash) {
                        var $parent = $(each).closest('.comment').addClass('focus-on');
                        $('html, body').animate({scrollTop: $parent.position().top}, "slow", function() {
                            $('.focus-on').removeClass('focus-on');
                        });
                    }
                });
            }
            setInterval(function() {
                Comments.reload_loop(container);
            }, 5 * 1000);
        });


        $('button.cancel', container).click(function() {
            $(this).hide();
            $('form', container).detach().insertAfter($('.comments-outer', container));
            $('form input[name="reply_to"]', container).val('');
            return false;
        });

        $('form textarea', container).on('focus', function() {
            Comments.pause_loop();
        }).on('blur', function() {
            Comments.resume_loop();
        });

        $('form', container).submit(function() {
            var $form = $(this);
            var comment = $.trim($('textarea[name="comment"]', this).val());
            if (!comment) return false;
            var data = {
                comment: comment,
                name: $('input[name="name"]', this).val(),
                reply_to: $('input[name="reply_to"]', this).val(),
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', this).val()
            };
            // We don't want to run the reload loop whilst waiting for the submission post
            Comments.pause_loop();
            var req = $.post(container.data('url'), data);
            req.done(function(response) {
                $('form').data('changes', 0);
                $('textarea[name="comment"]', $form).val('');
                $('.submission-success', $form).show();
                $('form button.cancel:visible', container).click();
                Comments.load(container);
                setTimeout(function() {
                    $('.submission-success', $form).fadeOut(600);
                }, RELOAD_INTERVAL * 1000);
            });
            req.always(function() {
                $('button[type="submit"]').removeProp('disabled');
                Comments.resume_loop();
            });
            req.fail(function(jqXHR, textStatus, errorThrown) {
                console.log('jqXHR', jqXHR);
                console.log('textStatus', textStatus);
                console.log('errorThrown', errorThrown);
                $('.other-error', container).show();
            });
            return false;
        });

    });

})(window, $);

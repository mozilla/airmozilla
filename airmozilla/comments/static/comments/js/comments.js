var Comments = (function() {

    var previous_latest_comment = null;
    var halt_reload_loop = false;
    var pause_reload_loop = false;
    var can_manage_comments = null;

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
        load: function(container, since, callback) {
            if ($.isFunction(since) && !callback) {
                /* This function was called like this:
                   Comments.load(container, function() {...})
                   not like this:
                   Comments.load(container, since, function() {...})
                */
                callback = since;
                since = null;
            }
            var url = container.data('url');
            if (since) {
                url += '?since=' + since;
            }
            var req = $.getJSON(url);
            req.then(function(response) {
                if (!response.discussion.enabled) {
                    container.remove();
                    return;
                }
                can_manage_comments = response.can_manage_comments;
                previous_latest_comment = response.latest_comment;
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
                    $('textarea', container).focus();
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
                    return fafalse && lse;
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
            var data = {};
            if (can_manage_comments) {
                data.include_posted = true;
            }
            var req = $.getJSON(container.data('reload-url'), data);
            req.then(function(response) {
                if (response.latest_comment != previous_latest_comment) {
                    Comments.load(container, data);
                }
            });
            req.fail(function(response) {
                console.warn('Error checking latest, so halt');
                console.warn('Status', response.status);
                halt_reload_loop = true;
            });
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

            // The whole comment change checking thing can wait a bit.
            setTimeout(function() {
                var RELOAD_INTERVAL = 5;  // seconds

                if (typeof window.Fanout !== 'undefined') {
                    Fanout.subscribe('/' + container.data('subscription-channel-comments'), function(data) {
                        // Supposedly the comments have changed.
                        // For security, let's not trust the data but just take it
                        // as a hint that it's worth doing an AJAX query
                        // now.
                        Comments.load(container, data);
                    });
                    // If Fanout doesn't work for some reason even though it
                    // was made available, still use the regular old
                    // interval. Just not as frequently.
                    RELOAD_INTERVAL = 60 * 5;
                }
                setInterval(function() {
                    Comments.reload_loop(container);
                }, RELOAD_INTERVAL * 1000);
            }, 3 * 1000);
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
                }, 10 * 1000);
            });
            req.always(function() {
                $('button[type="submit"]').removeProp('disabled');
                Comments.resume_loop();
            });
            req.fail(function(jqXHR, textStatus, errorThrown) {
                console.warn('jqXHR', jqXHR);
                console.warn('textStatus', textStatus);
                console.warn('errorThrown', errorThrown);
                $('.other-error', container).show();
            });
            return false;
        });

    });

})(window, $);

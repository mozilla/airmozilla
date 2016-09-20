var VIDLY_URL_TO_SHORTCUT = $('#vidly-shortcutter').data('vidly-url-to-shortcut');

var VidlyShortcutter = (function() {
    var container = $('#vidly-shortcutter');

    function close_helper() {
        $('form', container).hide();
        $('.hint', container).fadeIn(200);
        location.hash = '';
        $('.loading', container).hide();
    }

    function open_helper() {
        $('form', container).hide().fadeIn(400);
        $('.hint', container).hide();
    }

    function ready() {
        // set up opener
        $('.hint a', container).click(function() {
            open_helper();
            return true;
        });

        // set up closer
        $('button.cancel', container).click(function() {
            close_helper();
            return false;
        });

        // set up form submission handler
        //
        $('form', container).submit(function() {
            $('.loading', container).show();
            $.ajax({
               url: VIDLY_URL_TO_SHORTCUT,
                type: 'POST',
                data: $(this).serializeObject(),
                success: function(response) {
                    $('.loading', container).hide();
                    var shortcode = response.shortcode;
                    var vidly_template;
                    if ($('[name="default_archive_template"]').length) {
                        vidly_template = $('[name="default_archive_template"]').val();
                    } else {
                        $('#id_template option').each(function(i, each) {
                            if ($(each).text().search(/Vid\.ly/) > -1) {
                                vidly_template = $(each).val();
                            }
                        });
                    }
                    if (!vidly_template) {
                        alert("Could not find a Vid.ly template in the drop-down");
                    } else {
                        $('#id_template').val(vidly_template).change();
                        $('.last-result code', container).text(response.shortcode);
                        $('.last-result', container).show();
                        $('.last-url code', container).text(response.url);
                        $('.last-url', container).show();
                        setTimeout(function() {
                            $('#id_template_environment').val('tag=' + response.shortcode);
                        }, 1000);
                        close_helper();
                    }
                },
                error: function(xhr, status, error_thrown) {
                    $('.loading', container).hide();
                    var msg = status;
                    if (xhr.responseText) {
                        msg += ': ' + xhr.responseText;
                    }
                    alert(msg);
                }
            });
            return false;
        });

        // initial load if applicable
        if (location.hash === '#vidly-shortcutter') {
            $('.hint a', container).click();
        }
    }

    return {ready: ready};

})();

$.fn.serializeObject = function() {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


$(VidlyShortcutter.ready);

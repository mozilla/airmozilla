$(function() {
    var form = $('form#upload');
    var in_progress = false;
    var progress = $('#progressbar');
    var progress_bar = $('progress', progress);
    progress_bar.attr('value', 0);
    var progress_value = $('.progress-value', progress);
    progress_value.text('0 %');
    var verify_size_url = form.data('verify_size_url');
    var save_url = form.data('save_url');

    $('button.start', form).click(function() {
        if (!$('#file').val()) return false;
        if (in_progress) return false;  // double-click?
        progress.show();
        in_progress = true;
        $('.pre-progress', form).hide();
        $('.in-progress', form).show();
        var s3upload = new S3Upload({
            file_dom_selector: '#file',
            s3_sign_put_url: form.data('sign_upload_url'),

            onProgress: function(percent, message) {
                progress_bar.attr('value', percent);
                progress_value.text(percent + ' %');
            },
            onFinishS3Put: function(url) {
                $('.in-progress', form).hide();
                $('.mid-progress', form).show();

                $.get(verify_size_url, {url: url})
                  .then(function(result) {
                      $('input[name="url"]', form).val(url);
                      $('#status').text('');
                      $('.post-progress .file-size', form).text(result.size_human);
                      $('.post-progress', form).show();

                      var params = {
                          url: url,
                          csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', form).val()
                      };
                      $.post(save_url, params)
                        .then(function(response) {
                            $('.post-save', form).show();
                            if (response.suggested_event) {
                                $('.post-save .suggested-event a')
                                  .attr('href', response.suggested_event.url)
                                  .text(response.suggested_event.title);
                                $('.post-save .suggested-event').show();
                            } else {
                                $('.post-save .suggested-event').hide();
                            }
                        }).fail(function() {
                            $('#status').text('Unable to save the upload.');
                        }).always(function() {
                        });
                      //$('#status').html('Size ' + result.size_human);
                  }).fail(function() {
                      $('#status').text('Unable to verify size');
                  }).always(function() {
                      $('.mid-progress', form).hide();
                      $('button.start', form).show();
                  });
                in_progress = false;
            },
            onError: function(status) {
                $('#status').html('Upload error: ' + status);
                in_progress = false;
                $('.pre-progress', form).show();
                $('.in-progress', form).hide();
                $('.post-progress', form).hide();
            }
        });
        return false;
    });

    form.submit(function() {
        return $('input[name="url"]', form).val();
    });
});

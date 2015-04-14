
$(function() {

    var video_stream;

    function captureUserMedia(config, callback) {
        // console.log('navigator.mozGetUserMedia')
        navigator.getUserMedia = navigator.mozGetUserMedia || navigator.webkitGetUserMedia;
        navigator.getUserMedia(config, function(stream) {
            video_stream = stream;
            var video = $('video.recorder')[0];
            video.src = URL.createObjectURL(stream);
            video.muted = config.muted || false;
            video.controls = config.controls || false;
            video.play();

            callback(stream);
        }, function(error) { console.error(error); });
    }

    var audioVideoRecorder;

    var started = false;

    function startViewfinder(callback) {
        // we don't need the audio right now but we want the user
        // to approve that we can use it.
        var conf = {audio: true, video: true, muted: true, controls: false};
        // override and be more specific
        conf.video = { width: 1280, height: 720 };
        if (navigator.userAgent.indexOf('Firefox/37') > -1) {
            // Hack! If you're running an old Firefox we're not allowed to
            // set the constraints.
            conf.video = true;
        }
        // conf.video = { width: 640, aspectRatio: 16/9 };
        captureUserMedia(conf, function(stream) {
            // console.log('stream started');
            $('.starting').hide();
            $('.started').show();
            audioVideoRecorder = window.RecordRTC(stream, {
                type: 'video' // don't forget this; otherwise you'll get video/webm instead of audio/ogg
            });
            // window.audioVideoRecorder.startRecording();
            started = true;
            if (callback) {
                callback();
            }
        });
    }

    startViewfinder();

    var _duration_timer;
    var _duration_total = 0;
    function startDurationCounter() {
        $('.duration b').text(formatDuration(_duration_total));
        $('.duration').show();
        _duration_timer = setInterval(function() {
            _duration_total++;
            $('.duration b').text(formatDuration(_duration_total));
        }, 1000);
    }

    function formatDuration(seconds) {
        var minutes = Math.floor(seconds / 60);
        seconds = seconds % 60;
        out = '';
        if (minutes) {
            out += minutes + ' min ';
        }
        out += seconds + ' seconds';
        return out;
    }

    function stopDurationCounter() {
        clearInterval(_duration_timer);
        // $('.duration').hide();
    }

    $('.start-recording').on('click', function() {
        $('.start-recording').hide();
        $('.start-recording-hint').hide();
        $('.instructions').hide();
        $('.stop-recording').show();

        if (!started) {
            location.reload();
        } else {
            startDurationCounter();
            audioVideoRecorder.startRecording();
        }
    });

    var video_blob;

    $('button.start').on('click', function(event) {
        var form = $('form#upload');
        S3Upload.prototype.handleFileSelect = function() {
            var results = [];
            results.push(this.uploadFile(video_blob));
            return results;
        };
        $('.uploading').show();
        var in_progress = false;
        var progress = $('#progressbar');
        var progress_bar = $('progress', progress);
        progress_bar.attr('value', 0);
        var progress_value = $('.progress-value', progress);
        progress_value.text('0 %');
        var verify_size_url = form.data('verify_size_url');
        var save_url = form.data('save_url');
        $('button.start', form).hide();

        var s3upload = new S3Upload({
            file_dom_selector: 'anything',
            s3_sign_put_url: form.data('sign_upload_url'),
            onProgress: function(percent, message) {
                // console.log('percent', percent, 'message', message);
                progress_bar.attr('value', percent);
                progress_value.text(percent + ' %');
            },
            onFinishS3Put: function(url) {
                $('.uploading').hide();
                console.log('URL', url);
                $.get(verify_size_url, {url: url})
                .then(function(result) {
                    console.log('RESULT', result);
                    $('.saving .file-size').text(result.size_human);
                    $('.saving').show();
                    var params = {
                        url: url,
                        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]', form).val()
                    };
                    console.log('SAVING', params);
                    $.post(save_url, params)
                    .then(function(response) {
                        console.log('RESPONSE', response);
                        $('.finished').show();
                    })
                    .fail(function() {
                        console.error('Unable to save the upload.', arguments);
                    }).always(function() {
                        $('.saving').hide();
                    });

                }).fail(function() {
                    // $('#status').text('Unable to verify size');
                    console.error('Unable to verify size', arguments);
                }).always(function() {
                    // $('', form).hide();
                    // $('button.start', form).show();
                });
            },
            onError: function(status) {
                console.error(status);
            }
        });
    });

    $('.stop-recording').on('click', function() {
        stopDurationCounter();
        $('.stop-recording').hide();
        $('.start-recording').text('Start recording again').show();
        $('video.recorder').hide();
        // $('.stop-recording').attr('disabled', true);
        // $('.start-recording').attr('disabled', false);

        audioVideoRecorder.stopRecording(function(url) {
            video_blob = audioVideoRecorder.getBlob();

            $('.videosize b').text(bytesToSize(video_blob.size));
            $('.videosize').show();

            // downloadURL.innerHTML = '<a href="' + url + '" download="RecordRTC.webm" target="_blank">Save RecordRTC.webm to Disk!</a>';
            // var fileType = 'video'; // or "audio"

            // var video = $('video')[0];
            var video = $('video.playback')[0];
            video.src = url;
            video.muted = false;
            video.controls = true;
            video.play();
            $('video.playback').show();

            video.onended = function() {
                video.pause();
                // dirty workaround for: "firefox seems unable to playback"
                video.src = URL.createObjectURL(audioVideoRecorder.getBlob());
            };
            $('button.start').show();
            started = false;
        });
        video_stream.stop();
        console.log('Stream stopped');

    });
});

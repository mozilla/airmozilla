function humanFileSize( bytes, precision ) {
    'use strict';
    var units = [
       'bytes',
       'Kb',
       'Mb',
       'Gb',
       'Tb',
       'Pb'
    ];

    if ( isNaN( parseFloat( bytes )) || !isFinite( bytes ) ) {
        return '?';
    }

    var unit = 0;

    while ( bytes >= 1024 ) {
      bytes /= 1024;
      unit++;
    }

    return bytes.toFixed( +precision ) + ' ' + units[ unit ];
}

var originalDocumentTitle = document.title;
function showUploadProgress(percent, filesize) {
    var $parent = $('#progress');
    if (percent) {
        var progress = humanFileSize(filesize * percent / 100) + ' of ' +
            humanFileSize(filesize);
        document.title = percent + '% (' + progress + ')';
        $('progress', $parent).attr('value', percent);
        $('.progress-size', $parent).text(progress);
        $('.progress-value', $parent).text(percent + '%');
        $parent.show();
    } else {
        $parent.hide();
    }
}

function hideUploadProgress(celebrate) {
    $('#progress').hide();
    celebrate = celebrate || false;
    if (celebrate) {
        document.title = '\\o/ Upload finished! \\o/';
        setTimeout(function() {
            document.title = originalDocumentTitle;
        }, 3 * 1000);
    } else {
        document.title = originalDocumentTitle;
    }
}

angular.module('new.services', [])

.service('eventService',
    ['$state', '$interval', '$http',
    function($state, $interval, $http) {
        var _id = null;
        var _uploading = false;
        var _picture = null;
        var service = {};

        var $appContainer = angular.element('#content');
        var scrapeUrl = $appContainer.data('screencaptures-url');
        var eventUrl = $appContainer.data('event-url');
        var archiveUrl = $appContainer.data('archive-url');

        // The scrape is fired off at the same time as we
        // start the archiving and the order of these finishing
        // is not guaranteed. So setting this higher scope
        // boolean allows the interval of looking for picture
        // to be cancelled.
        var scrapeFailed = false;

        service.setId = function(id) {
            _id = id;
            sessionStorage.setItem('lastNewId', id);
        };
        service.getId = function() {
            return _id;
        };
        service.handleErrorStatus = function(data, status) {
            if (status === 404) {
                $state.go('problem.notfound');
            } else if (status === 403) {
                $state.go('problem.notyours');
            } else {
                console.error('STATUS', status, data);
            }
        };
        service.isUploading = function() {
            return _uploading;
        };
        service.setUploading = function(toggle) {
            _uploading = toggle;
        };
        service.setPicture = function(picture) {
            _picture = picture;
        };
        service.getPicture = function() {
            return _picture;
        };
        service.scrape = function(eventId) {
            // Screencaps will use the S3 upload to make
            // screencaptures independent of Vid.ly
            return $http.post(
                scrapeUrl.replace('0', eventId)
            )
            .success(function() {
                // statusService.set(
                //     'Screencaptures scraped from the video', 3
                // );
            })
            .error(function() {
                console.error.apply(console, arguments);
                scrapeFailed = true;
            });
        };
        service.lookForPicture = function(eventId) {
            // start looking for a picture
            var url = eventUrl.replace('0', eventId);
            var keepLooking = $interval(function() {
                if (scrapeFailed) {
                    // Some future version we might, here,
                    // remove the "Loading preview" thing
                    console.warn(
                        'Scrape failed so don\'t bother looking repeatedly.'
                    );
                    $interval.cancel(keepLooking);
                    return;
                }
                $http.get(url)
                .success(function(response) {
                    if (response.event.picture) {
                        // console.log('YAY we have a picture now');
                        service.setPicture(
                            response.event.picture
                        );
                        $interval.cancel(keepLooking);
                    } else {
                        // console.log('No picture yet');
                    }
                })
                .error(function() {
                    console.error.apply(console, arguments);
                    $interval.cancel(keepLooking);
                });
            }, 1.5 * 1000);
        };
        service.archive = function(eventId) {
            // Archiving will submit the upload URL to vid.ly
            return $http.post(
                archiveUrl.replace('0', eventId)
            )
            .success(function() {
                service.lookForPicture(eventId);
            })
            .error(console.error.bind(console));
        };
        return service;
    }]
)


.service('statusService',
    ['$timeout',
    function($timeout) {
        var _message = null, _nextMessage = null;
        var _messageTimer = null;

        this.set = function(msg, stick) {
            stick = stick || 0;
            if (stick > 0) {
                if (stick <= 10) {
                    // you specified seconds, not milliseconds
                    stick *= 1000;
                }
                _message = msg;
                _nextMessage = null;
                _messageTimer = $timeout(function() {
                    _message = _nextMessage;
                }, stick);
            } else {
                _message = msg;
                $timeout.cancel(_messageTimer);
            }

        };
        this.get = function() {
            return _message;
        };
    }]
)

.service('localProxy',
    ['$q', '$http', '$timeout',
    function($q, $http, $timeout) {
        var service = {};
        var memory = {};

        service.get = function(url, store, once) {
            var deferred = $q.defer();
            var already = memory[url] || null;
            if (already !== null) {
                $timeout(function() {
                    if (once) {
                        deferred.resolve(already);
                    } else {
                        deferred.notify(already);
                    }
                });
            } else if (store) {
                already = sessionStorage.getItem(url);
                if (already !== null) {
                    already = JSON.parse(already);
                    $timeout(function() {
                        if (once) {
                            deferred.resolve(already);
                        } else {
                            deferred.notify(already);
                        }
                    });
                }
            }

            $http.get(url)
            .success(function(r) {
                memory[url] = r;
                deferred.resolve(r);
                if (store) {
                    sessionStorage.setItem(url, JSON.stringify(r));
                }
            })
            .error(function() {
                deferred.reject(arguments);
            });
            return deferred.promise;
        };

        service.remember = function(url, data, store) {
            memory[url] = data;
            if (store) {
                sessionStorage.setItem(url, JSON.stringify(data));
            }
        };

        return service;
    }]
)

.service('uploadService',
    ['$q', '$http', '$interval', 'statusService', 'eventService',
    function($q, $http, $interval, statusService, eventService) {
        var service = {};
        var $appContainer = angular.element('#content');
        var signURL = $appContainer.data('sign-upload-url');
        var verifyURL = $appContainer.data('verify-size-url');
        var uploadUrl = $appContainer.data('sign-upload-url');
        var saveUrl = $appContainer.data('save-url');
        // var archiveUrl = $appContainer.data('archive-url');
        // var scrapeUrl = $appContainer.data('screencaptures-url');
        // var eventUrl = $appContainer.data('event-url');
        var _failed = false;

        var signed = {};
        var _dataFile = null;
        service.setDataFile = function(dataFile) {
            _dataFile = dataFile;
        };
        service.unsetDataFile = function() {
            _dataFile = null;
        };
        service.hasFailed = function() {
            return !!_failed;
        };
        service.start = function(duration) {
            var deferred = $q.defer();

            // override so we can set the file selection to an array
            S3Upload.prototype.handleFileSelect = function() {
                var results = [];
                results.push(this.uploadFile(_dataFile));
                return results;
            };
            // override so we can get more information from the signage
            S3Upload.prototype.executeOnSignedUrl = function(file, callback, opts) {
                var type = opts && opts.type || file.type;
                var name = opts && opts.name || file.name;
                if (!name) {
                    if (type === 'video/webm') {
                        name = 'file.webm';
                    } else {
                        console.warn('type', type);
                        throw "No name and unrecognized type";
                    }
                }
                var this_s3upload = this;
                $http({
                    url: signURL,
                    method: 'GET',
                    params: {
                        s3_object_type: type,
                        s3_object_name: name
                    }
                })
                .success(function(response) {
                    signed = response; // XXX why does this need to be on the scope!?
                    callback(response.signed_request, response.url);
                })
                .error(function() {
                    this_s3upload.onError('Unable to sign request');
                    console.warn(arguments);
                });
            };

            statusService.set('Uploading video file...');
            eventService.setUploading(true);
            // $state.go('preemptiveDetails');

            var startTime = new Date();
            var s3upload = new S3Upload({
                file_dom_selector: 'anything',
                s3_sign_put_url: uploadUrl,
                onProgress: function(percent, message, public_url, file) {
                    // Use jQuery for this because we don't want to have
                    // to apply the scope for every little percent tick.
                    showUploadProgress(percent, file.size);
                },
                onError: function(msg, file) {
                    hideUploadProgress();
                    _failed = true;
                    deferred.reject(msg, file);
                },
                onFinishS3Put: function(url) {
                    var endTime = new Date();
                    var uploadTime = parseInt((endTime - startTime) / 1000, 10);
                    signed.url = url;
                    statusService.set('Verifying upload size');
                    // oh how I wish I could do $http.get(url, params)
                    $http({
                        url: verifyURL,
                        method: 'GET',
                        params: {url: url}
                    })
                    .success(function(response) {
                        hideUploadProgress(true);
                        _failed = false;

                        // $scope.$apply(function() {
                            eventService.setUploading(false);
                            _failed = false;
                        // });
                        signed.size = response.size;
                        signed.upload_time = uploadTime;
                        // uploadSize = response.size_human;
                        statusService.set('Saving upload');
                        signed.duration = duration;
                        // Save will create an event that will have an upload
                        $http.post(saveUrl, signed)
                        .success(function(saveResponse) {
                            statusService.set('Upload saved', 2);
                            // in case the user reloads when URL is /new/details
                            sessionStorage.setItem('lastNewId', saveResponse.id);
                            eventService.setId(saveResponse.id);
                            deferred.resolve();
                        })
                        .error(function() {
                            console.error.appy(console, arguments);
                            deferred.reject('Failed to save the upload.');
                        });
                    })
                    .error(function() {
                        console.error.appy(console, arguments);
                        deferred.reject('Failed to verify the upload.');
                    });
                }
            }); // new S3Upload(...)
            return deferred.promise;
        };
        service.startAndProcess = function(duration) {
            // This will upload the set dataFile and when it has saved the
            // upload it will commence the archiving and scraping.
            return service.start(duration)
            .then(function() {
                // kick off the archiving
                eventService.archive(eventService.getId())
                .success(function() {
                    statusService.set(
                        'Video sent in for transcoding', 3
                    );
                });
                // simultaneousishly kick off the scraping
                eventService.scrape(eventService.getId())
                .success(function() {
                    statusService.set(
                        'Screencaptures scraped from the video', 3
                    );
                });
                // let that piece of memory be freed up
                service.unsetDataFile();
            })
            .catch(function(msg) {
                statusService.set('Upload failed for unknown reason');
                eventService.setUploading(false);
                console.error(msg);
            });
        };

        return service;
    }]
)

.service('staticService',
    function() {
        var injected = [];
        var endsWith = function(string, suffix) {
            return string.indexOf(suffix, string.length - suffix.length) !== -1;
        };
        var nothingCallback = function() {};
        return function(url, onload) {
            onload = onload || nothingCallback;
            if (injected.indexOf(url) === -1) {
                if (endsWith(url, '.js')) {
                    var script = document.createElement('script');
                    script.src = url;
                    script.onload = onload;
                    document.head.appendChild(script);
                } else if (endsWith(url, '.css')) {
                    var link = document.createElement('link');
                    link.rel = 'stylesheet';
                    link.href = url;
                    link.onload = onload;
                    document.head.appendChild(link);
                }
                injected.push(url);
            }
        };
    }
)


.service('youtubeService',
    ['$http',
    function($http) {
        var service = {};
        var $appContainer = angular.element('#content');
        var youtubeExtractUrl = $appContainer.data('youtube-extract-url');
        var youtubeCreateUrl = $appContainer.data('youtube-create-url');

        service.extractVideoInfo = function(url) {
            return $http({
                url: youtubeExtractUrl,
                method: 'GET',
                params: {
                    url: url
                }
            });

        };

        service.createEvent = function(data) {
            return $http.post(youtubeCreateUrl, data);
        };

        return service;
    }]
)

;

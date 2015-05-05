function humanFileSize( bytes, precision ) {
    var units = [
       'bytes',
       'Kb',
       'Mb',
       'Gb',
       'Tb',
       'Pb'
    ];

    if ( isNaN( parseFloat( bytes )) || ! isFinite( bytes ) ) {
        return '?';
    }

    var unit = 0;

    while ( bytes >= 1024 ) {
      bytes /= 1024;
      unit ++;
    }

    return bytes.toFixed( + precision ) + ' ' + units[ unit ];
}

function showUploadProgress(percent, filesize) {
    var $parent = $('#progress');
    if (percent) {
        $('progress', $parent).attr('value', percent);
        $('.progress-size', $parent).text(
            humanFileSize(filesize * percent / 100) + ' of ' +
            humanFileSize(filesize)
        );
        $('.progress-value', $parent).text(percent + '%');
        $parent.show();
    } else {
        $parent.hide();
    }
}

function hideUploadProgress() {
    $('#progress').hide();
}


angular.module('new.controllers', ['new.services'])

.filter('filesize', function () {
    return humanFileSize;
})

.directive('stopEvent', function () {
    return {
        restrict: 'A',
        link: function (scope, element, attr) {
            element.bind(attr.stopEvent, function (e) {
                e.stopPropagation();
                e.preventDefault();
            });
        }
    };
 })

.directive('loading', function() {
    return {
        restrict: 'E',
        scope: {
            on: '=',  // two-way
            size: '@', // one-way
            message: '@'
        },
        template: '<div ng-show="ld.on" ng-class="ld.outerClass">' +
                  '  <p class="loading">' +
                  '  {{ ld.message }}' +
                  '  </p>' +
                  '</div>',
        controllerAs: 'ld',
        controller: function($scope) {
            this.message = $scope.message;
            this.on = $scope.on;
            $scope.$watch('on', function (val) {
                this.on = val;
            }.bind(this));
            var size = $scope.size || 'large';
            this.outerClass = 'loading-outer-' + size;
        }
    };
})

.controller('StartController', ['$scope', '$http', '$state',
    function($scope, $http, $state) {
        var $appContainer = angular.element('#content');
        var yoursUrl = $appContainer.data('yours-url');
        var deleteUrl = $appContainer.data('delete-url');
        var videoUrl = $appContainer.data('video-url');
        $scope.loading = true;

        $scope.formatDate = function(date) {
            return moment(date).format('ddd, MMM D, YYYY, h:mma UTCZZ');
        };

        $http.get(yoursUrl)
        .success(function(response) {
            $scope.events = response.events;
            $scope.events.forEach(function(event) {
                var nextUrl;
                if (event.title) {
                    if (event.picture) {
                        nextUrl = $state.href('summary', {id: event.id});
                    } else {
                        nextUrl = $state.href('picture', {id: event.id});
                    }
                } else {
                    nextUrl = $state.href('details', {id: event.id});
                }
                event._nextUrl = nextUrl;
                event._video = null;
                var url = videoUrl.replace('0', event.id);
                $http.get(url)
                .success(function(response) {
                    event._video = response;
                });
            });
        })
        .error(console.error.bind(console))
        .finally(function() {
            $scope.loading = false;
        });

        $scope.deleteEvent = function(event) {
            event._deleting = true;
            $http.post(deleteUrl.replace('0', event.id))
            .success(function() {
                $scope.events.splice($scope.events.indexOf(event), 1);
            })
            .error(console.error.bind(console));
        };
    }
])


// from http://uncorkedstudios.com/blog/multipartformdata-file-upload-with-angularjs
.directive('fileModel', ['$parse', function ($parse) {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            var model = $parse(attrs.fileModel);
            var modelSetter = model.assign;

            element.bind('change', function(){
                scope.$apply(function(){
                    modelSetter(scope, element[0].files[0]);
                });
            });
        }
    };
}])

// .controller('ProgressController',
//     ['$scope', 'progressService',
//     function($scope, progressService) {
//         $scope.progress = progressService;
//         // console.log('$scope.progress', $scope.progress);
//         //
//         // progressService.set(0);
//         // // $scope.progress = progressService;
//         // $timeout(function() {
//         //     progressService.set(10);
//         // }, 1000);
//         // setTimeout(function() {
//         //     progressService.set(15);
//         //     $scope.$apply();
//         // }, 2000);
//     }]
// )

.controller('StatusController',
    ['$scope', 'statusService',
    function($scope, statusService) {
        $scope.status = statusService;
    }]
)

.controller('UploadController',
    ['$scope', '$http', '$state', 'eventService',
     'statusService', '$interval',
    function(
        $scope, $http, $state, eventService,
        statusService, $interval
    ) {
        var $appContainer = angular.element('#content');
        var saveUrl = $appContainer.data('save-url');
        var uploadUrl = $appContainer.data('sign-upload-url');
        var archiveUrl = $appContainer.data('archive-url');
        var scrapeUrl = $appContainer.data('screencaptures-url');
        $scope.fileError = null;
        $scope.signed = {};

        hideUploadProgress();
        // progressService.set(null);

        var acceptedFiles = [
            'video/webm',
            'video/quicktime',
            'video/mp4',
            'video/x-flv',
            'video/ogg',
            'video/x-msvideo',
            'video/x-ms-wmv',
            'video/x-m4v',
        ];

        $scope.startUpload = function() {
            // var fakei = $interval(function() {
            //     progressService.set(1 + progressService.get());
            //     var file = {};
            //     file.size = 12345678;
            //     var percent = progressService.get();
            //     progressService.setSize(
            //         humanFileSize(file.size * percent / 100) +
            //         ' of ' + humanFileSize(file.size)
            //     );
            //     if (progressService.get() >= 100) {
            //         $interval.cancel(fakei);
            //         eventService.setId(1234);
            //     }
            // }, 0.2*1000);
            // $state.go('preemptiveDetails');
            // return;
            //
            //


            if (!$scope.dataFile) return;
            $scope.fileError = null;
            var file = $scope.dataFile;

            // commented out temporarily so I don't have to upload movie files every time!!!!!!
            if (acceptedFiles.indexOf(file.type) === -1) {
                $scope.fileError = "Not a recognized file type (" +
                    file.type + ")";
                return;
            }

            // let's start uploading it to S3
            S3Upload.prototype.handleFileSelect = function() {
                var results = [];
                results.push(this.uploadFile(file));
                return results;
            };
            // override so we can get more information from the signage
            S3Upload.prototype.executeOnSignedUrl = function(file, callback, opts) {
                var type = opts && opts.type || file.type;
                var name = opts && opts.name || file.name;
                var this_s3upload = this;
                $http({
                    url: $appContainer.data('sign-upload-url'),
                    method: 'GET',
                    params: {
                        s3_object_type: type,
                        s3_object_name: name
                    }
                })
                .success(function(response) {
                    $scope.signed = response;
                    callback(response.signed_request, response.url);
                })
                .error(function() {
                    this_s3upload.onError('Unable to sign request');
                    console.warn(arguments);
                });
            };

            statusService.set('Uploading video file...');
            $state.go('preemptiveDetails');

            var s3upload = new S3Upload({
                file_dom_selector: 'anything',
                s3_sign_put_url: uploadUrl,
                onProgress: function(percent, message, public_url, file) {
                    // Use jQuery for this because we don't want to have
                    // to apply the scope for every little percent tick.
                    showUploadProgress(percent, file.size);
                },
                onError: function(msg) {
                    // progressService.set(null);
                    hideUploadProgress();
                    statusService.set(msg);
                    console.error(msg);
                    // $state.go('upload', {id: response.id}); // good idea?!
                },
                onFinishS3Put: function(url, file) {
                    $scope.signed.url = url;
                    // console.log("FINISHED!", url, file);
                    // progressService.set(null);
                    statusService.set('Verifying upload size');
                    // oh how I wish I could do $http.get(url, params)
                    $http({
                        url: $appContainer.data('verify-size-url'),
                        method: 'GET',
                        params: {url: url},
                    })
                    .success(function(response) {
                        hideUploadProgress();
                        $scope.signed.size = response.size;
                        $scope.uploadSize = response.size_human;
                        // console.log('Size verified', response);
                        statusService.set('Saving upload');

                        // Save will create an event that will have an upload
                        $http.post(saveUrl, $scope.signed)
                        .success(function(response) {
                            // console.log('Upload saved', response);
                            statusService.set('Upload saved.', 2);
                            eventService.setId(response.id);

                            // Archiving will submit the upload URL to vid.ly
                            $http.post(
                                archiveUrl.replace('0', eventService.getId())
                            )
                            .success(function(response) {
                                console.log("Archiving finished");

                            })
                            .error(console.error.bind(console));

                            // Screencaps will use the S3 upload to make
                            // screencaptures independent of Vid.ly
                            $http.post(
                                scrapeUrl.replace('0', eventService.getId())
                            )
                            .success(function() {
                                console.log("Finished screencaps scraping");
                            })
                            .error(console.error.bind(console));

                        })
                        .error(console.error.bind(console));

                    })
                    .error(console.error.bind(console));
                }
            }); // new S3Upload(...)

        };

    }
])

.controller('DetailsController',
    ['$scope', '$stateParams', '$http', '$state', '$timeout', 'eventService',
     'statusService', 'localProxy',
    function(
        $scope, $stateParams, $http, $state, $timeout, eventService,
        statusService, localProxy
    ) {
        $scope.eventService = eventService;
        var $appContainer = angular.element('#content');
        var eventUrl = $appContainer.data('event-url');
        $scope.event = {};
        $scope.errors = {};
        $scope.hasErrors = false;
        // console.log("$stateParams.id", $stateParams.id);
        if (typeof $stateParams.id !== 'undefined') {
            // $scope.id = parseInt($stateParams.id, 10);
            eventService.setId(parseInt($stateParams.id, 10));
        } else {
            // we have to pick some defaults
            $scope.event.privacy = 'public';
        }

        function decodeChannelsList(channels) {
            // needed for angularjs
            var dict = {};
            channels.forEach(function(channel) {
                if (channel instanceof Object) {
                    dict[channel.id] = true;
                } else {
                    dict[channel] = true;
                }
            });
            return dict;
        }

        function encodeChannelsList(channels) {
            // needed for django
            var flat = [];
            for (var id in channels) {
                if (channels[id]) {
                    flat.push(id);
                }
            }
            return flat;
        }

        // $scope.loading=true;return;

        if (eventService.getId() === null) {
            // the upload progress is still going on
            $scope.loading = false;
        } else {
            $scope.loading = true;
            var url = eventUrl.replace('0', eventService.getId());
            $http.get(url)
            .success(function(response) {
                if (response.event.status !== 'initiated') {
                    $state.go('published', {id: eventService.getId()});
                }
                $scope.event = response.event;
                // exceptional for editing
                $scope.event.channels = decodeChannelsList(
                    response.event.channels
                );
                $scope.loading = false;
                // use jQuery to find out if any of the channels you have
                // selected is in the hidden part
                $timeout(function() {
                    for (var id in $scope.event.channels) {
                        if ($('input[value="' + id + '"]:hidden').length) {
                            $scope.showOtherChannels = true;
                        }
                    }
                });
            })
            .error(eventService.handleErrorStatus);

        }

        function setupTagsTextcomplete(response) {
            $('#id_tags').textcomplete([
                {
                    words: response.tags,
                    match: /\b(\w{2,})$/i,
                    search: function (term, callback) {
                        callback($.map(this.words, function (word) {
                            return word.indexOf(term) === 0 ? word : null;
                        }));
                    },
                    index: 1,
                    replace: function (word) {
                        return word + ', ';
                    }
                }
            ]);
        }

        // Run this in a timeout so that we give the template a chance
        // to render first.
        $timeout(function() {
            localProxy.get('/all-tags/', true, true)
            .then(setupTagsTextcomplete, function() {
                console.error.apply(console, arguments);
            }, setupTagsTextcomplete);
        }, 1000);

        $scope.save = function() {
            statusService.set('Saving event', 1);
            // console.log($scope.event);
            // return false;
            $scope.errors = {};
            $scope.hasErrors = false;
            var url = eventUrl.replace('0', eventService.getId());
            // exceptionally change the channels list of a plain list
            $scope.event.channels = encodeChannelsList($scope.event.channels);
            $http.post(url, $scope.event)
            .success(function(response) {
                if (response.errors) {
                    $scope.hasErrors = true;
                    $scope.errors = response.errors;
                    console.warn(response.errors);
                    statusService.set("Form submission error", 10);
                    $scope.event.channels = decodeChannelsList(
                        $scope.event.channels
                    );
                } else {
                    $scope.event = response.event;
                    $scope.event.channels = decodeChannelsList(
                        response.event.channels
                    );
                    statusService.set("Event saved!", 3);
                    if ($scope.event.picture) {
                        $state.go('summary', {id: eventService.getId()});
                    } else {
                        $state.go('picture', {id: eventService.getId()});
                    }
                }
            })
            .error(function() {
                console.error.apply(console, arguments);
                // decode it back
                $scope.event.channels = decodeChannelsList(
                    $scope.event.channels
                );
            });
        };

        $scope.toggleShowOtherChannels = function() {
            $scope.showOtherChannels = ! $scope.showOtherChannels;
        };

    }
])

.controller('PictureController',
    ['$scope', '$stateParams', '$http', '$state', '$interval',
     'eventService', 'statusService',
    function(
        $scope, $stateParams, $http, $state, $interval,
        eventService, statusService
    ) {
        var $appContainer = angular.element('#content');
        $scope.thumbnails = [];
        $scope.picked = null;
        var id = $stateParams.id;

        var eventUrl = $appContainer.data('event-url').replace('0', id);
        var pictureUrl = $appContainer.data('picture-url').replace('0', id);
        var scrapeUrl = $appContainer.data('screencaptures-url').replace('0', id);

        $http.get(eventUrl)
        .success(function(response) {
            $scope.event = response.event;
            if (response.event.status !== 'initiated') {
                $state.go('published', {id: id});
            }
        })
        .error(eventService.handleErrorStatus);

        $scope.durationError = false;
        $scope.picturesError = false;

        $scope.loading = true;
        $scope.stillLoading = false;
        var reFetching = false;
        var displayAvailableScreencaptures = function() {
            $http.get(pictureUrl)
            .success(function(response) {
                // console.log(response);
                if (response && response.thumbnails) {
                    $scope.loading = false;
                    $scope.stillLoading = false;
                    if (response.thumbnails.length >= 10) {
                        $interval.cancel(reloadPromise);
                    }
                    $scope.thumbnails = response.thumbnails;
                } else {
                    // statusService.set('No screen captures available yet.');
                    $scope.stillLoading = true;
                    if (response && !response.fetching && !reFetching) {
                        reFetching = true;
                        $http.post(scrapeUrl)
                        .success(function(response) {
                            if (!response.seconds) {
                                $scope.loading = false;
                                $scope.stillLoading = false;
                                $scope.durationError = true;
                                $interval.cancel(reloadPromise);
                            } else if (!response.no_pictures) {
                                $scope.loading = false;
                                $scope.stillLoading = false;
                                $scope.picturesError = true;
                                $interval.cancel(reloadPromise);
                            } else {
                                console.log(
                                    "Finished screencaps scraping",
                                    response
                                );
                            }
                        })
                        .error(console.error.bind(console));
                    }
                }
            })
            .error(console.error.bind(console));
        };

        displayAvailableScreencaptures(); // first load
        var reloadPromise = $interval(displayAvailableScreencaptures, 3000);

        $scope.pickThumbnail = function(thumbnail) {
            // unpick the other, if there was one
            $scope.thumbnails.forEach(function(thumbnail) {
                thumbnail.picked = false;
            });
            thumbnail.picked = true;
            $http.post(pictureUrl, {picture: thumbnail.id})
            .success(function(response) {
                statusService.set('Chosen picture saved.', 3);
            })
            .error(console.error.bind(console));
            return false;
        };

        $scope.next = function() {
            $state.go('summary', {id: id});
        };
    }
])

.controller('SummaryController',
    ['$scope', '$stateParams', '$http', '$state', '$sce', '$timeout',
     'statusService', 'eventService',
    function(
        $scope, $stateParams, $http, $state, $sce, $timeout,
        statusService, eventService
    ) {
        var $appContainer = angular.element('#content');
        var id = $stateParams.id;
        var url = $appContainer.data('summary-url').replace('0', id);
        var videoUrl = $appContainer.data('video-url').replace('0', id);
        var publishUrl = $appContainer.data('publish-url').replace('0', id);
        $scope.video = {};
        $scope.loading = true;
        $scope.publishing = false;
        $scope.publishingError = false;

        function showIframe() {
            var iframeUrl = $appContainer.data('iframe-url')
                .replace('slug', $scope.event.slug) +
                '?no-warning=1&no-footer=1'
                ;
            $scope.video.iframe_src = $sce.trustAsResourceUrl(iframeUrl);
        }

        function fetchVideo() {
            $http.get(videoUrl)
            .success(function(response) {
                $scope.video = response;
                if (response.finished) {
                    showIframe();
                } else {
                    $timeout(function() {
                        fetchVideo();
                        console.log("Rechecking if video is there now");
                    }, 5 * 1000);
                }
            })
            .error(console.error.bind(console))
            .finally(function() {
                $scope.loadingVideo = false;
            });
        }

        $http.get(url)
        .success(function(response) {
            if (response.event.status !== 'initiated') {
                $state.go('published', {id: id});
            }
            $scope.event = response.event;
            $scope.pictures = response.pictures;
            $scope.loadingVideo = true;
            fetchVideo();
        })
        .error(eventService.handleErrorStatus)
        .finally(function() {
            $scope.loading = false;
        });

        $scope.publish = function() {
            $scope.publishing = true;
            $scope.publishingError = false;
            $http.post(publishUrl)
            .success(function(response) {
                $state.go('published', {id: id});
                $scope.publishing = false;
            })
            .error(function() {
                console.error.apply(console, arguments);
                $scope.publishingError = true;
                $scope.publishing = false;
            });
        };

        $scope.resetPublishingError = function() {
            $scope.publishingError = false;
        };

    }
])

.controller('PublishedController',
    ['$scope', '$stateParams', '$http', 'eventService',
    function($scope, $stateParams, $http, eventService) {
        var $appContainer = angular.element('#content');
        var id = $stateParams.id;
        var summaryUrl = $appContainer.data('summary-url').replace('0', id);
        summaryUrl += '?extended';
        var videoUrl = $appContainer.data('video-url').replace('0', id);
        $scope.video = null;
        $scope.loading = true;

        $http.get(summaryUrl)
        .success(function(response) {
            $scope.event = response.event;
            $scope.event._abs_url = document.location.protocol + '//' +
            document.location.hostname +
            response.event.url;
        })
        .error(eventService.handleErrorStatus)
        .finally(function() {
            $scope.loading = false;
        });

        $http.get(videoUrl)
        .success(function(response) {
            $scope.video = response;
        })
        .error(console.error.bind(console));

    }
])

.controller('NotFoundController',
    ['$scope',
    function($scope) {
        $scope.error = {
            title: "Not Found",
            message: "Page not found.",
        };
    }
])

.controller('NotYoursController',
    ['$scope',
    function($scope) {
        $scope.error = {
            title: "Not Yours",
            message: "The page you tried to access tried to access data " +
                     "about an event that doesn't belong to you.",
        };
    }
])

;

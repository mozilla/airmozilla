/* global $ angular console document RecordRTC */

function preloadImage(url, cb) {
    var img = document.createElement('img');
    if (cb) {
        img.onload = cb;
    }
    img.src = url;
}

var origTitle = document.title;
function setDocumentTitle(title) {
    document.title = title + ' | ' + origTitle;
}

angular.module('new.controllers', ['new.services'])

.filter('filesize', function () {
    return humanFileSize;
})

.filter('formattime', function() {
    return function(seconds) {
        if (!seconds) {
            return '';
        }
        return humanizeDuration(seconds * 1000);
    };
})

.filter('showduration', function() {
    return function(seconds) {
        return moment().add(seconds, 'seconds').fromNow(true);
    };
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
        controller: ['$scope', function($scope) {
            this.message = $scope.message;
            this.on = $scope.on;
            $scope.$watch('on', function (val) {
                this.on = val;
            }.bind(this));
            var size = $scope.size || 'large';
            this.outerClass = 'loading-outer-' + size;
        }]
    };
})

.controller('StartController',
    ['$scope', '$http', '$timeout', '$state',
    function($scope, $http, $timeout, $state) {
        setDocumentTitle('Unfinished Videos');
        var $appContainer = angular.element('#content');
        var yoursUrl = $appContainer.data('yours-url');
        var deleteUrl = $appContainer.data('delete-url');
        var videoUrl = $appContainer.data('video-url');
        var videosUrl = $appContainer.data('videos-url');
        var archiveUrl = $appContainer.data('archive-url');
        var scrapeUrl = $appContainer.data('screencaptures-url');
        var eventUrl = $appContainer.data('event-url');

        $scope.hasYouTubeAPIKey = $appContainer.data('has-youtube-api-key');
        $scope.loading = true;

        $http.get(yoursUrl)
        .success(function(response) {
            $scope.events = response.events;
            var eventIds = [];
            setDocumentTitle('Unfinished Videos (' + $scope.events.length + ')');
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
                event._modifiedFormatted = moment(event.modified)
                    .format('ddd, MMM D, YYYY, h:mma UTCZZ');
                event._nextUrl = nextUrl;

                // assume that we know nothing about the state of its video
                event._video = null;

                if (event.picture) {
                    preloadImage(event.picture.url);
                }

                // build up a list of event IDs we want together
                // query for the state of.
                eventIds.push(event.id);

                if (!event.pictures && !event.picture) {
                    $http.post(scrapeUrl.replace('0', event.id))
                    .success(function(scrapeResponse) {
                        event.pictures = scrapeResponse.no_pictures;
                        $http.get(eventUrl.replace('0', event.id))
                        .success(function(eventResponse) {
                            if (eventResponse.event && eventResponse.event.picture) {
                                event.picture = eventResponse.event.picture;
                            }
                        })
                        .error(console.error.bind(console));
                    });
                }
            });
            if (eventIds.length) {
                $http.post(videosUrl, {ids: eventIds})
                .success(function(response) {
                    $scope.events.forEach(function(event) {
                        if (!event.upload) {
                            return;
                        }
                        if (!response[event.id] || (response[event.id] && !response[event.id].tag)) {
                            // it must have been a straggler what wasn't submitted
                            $http.post(archiveUrl.replace('0', event.id))
                            .success(function() {
                                var url = videoUrl.replace('0', event.id);
                                $http.get(url)
                                .success(function(archiveResponse) {
                                    event._video = archiveResponse;
                                });
                            });
                        } else {
                            event._video = response[event.id];
                        }
                    });
                })
                .error(console.error.bind(console));
            }
        })
        .error(console.error.bind(console))
        .finally(function() {
            // delay it slightly to give it a chance to load all the
            // images and the video information.
            $timeout(function() {
                $scope.loading = false;
            }, 1000);
        });

        $scope.deleteEvent = function(event) {
            event._deleting = true;
            $http.post(deleteUrl.replace('0', event.id))
            .success(function() {
                $scope.events.splice($scope.events.indexOf(event), 1);
            })
            .error(console.error.bind(console));
        };

        // If you're deliberately here, we don't need to keep remembering
        // which Id you last worked on.
        sessionStorage.removeItem('lastNewId');
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

.controller('StatusController',
    ['$scope', 'statusService',
    function($scope, statusService) {
        $scope.status = statusService;
    }]
)

.controller('UploadProblemController',
    ['$scope', 'uploadService',
    function($scope, uploadService) {
        $scope.upload = uploadService;
        $scope.loaded = true;
        $scope.retryUpload = function() {
            uploadService.startAndProcess();
        };
    }]
)

.controller('UploadController',
    ['$scope', '$state', '$interval',
     'statusService', 'eventService', 'uploadService',
    function(
        $scope, $state, $interval,
        statusService, eventService, uploadService
    ) {
        setDocumentTitle('Upload a file');
        $scope.fileError = null;

        var acceptedFiles = [
            'video/webm',
            'video/quicktime',
            'video/mp4',
            'video/x-flv',
            'video/ogg',
            'video/x-msvideo',
            'video/x-ms-wmv',
            'video/x-m4v'
        ];

        $scope.startUpload = function() {

            if (!$scope.dataFile) {
                return;
            }
            $scope.fileError = null;
            var file = $scope.dataFile;

            // commented out temporarily so I don't have to upload movie files every time!!!!!!
            if (acceptedFiles.indexOf(file.type) === -1) {
                $scope.fileError = 'Not a recognized file type (' +
                    file.type + ')';
                return;
            }

            // make sure there's no lingering started event
            sessionStorage.removeItem('lastNewId');
            uploadService.setDataFile(file);
            uploadService.startAndProcess();
            $state.go('preemptiveDetails');

        };

    }
])

.controller('YouTubeController',
    ['$scope', '$state', '$interval', '$sce',
     'statusService', 'eventService', 'youtubeService',
    function(
        $scope, $state, $interval, $sce,
        statusService, eventService, youtubeService
    ) {
        setDocumentTitle('Share a YouTube™ Video');


        $scope.urlError = null;
        $scope.serverError = null;
        $scope.url = '';

        $scope.cancel = function() {
            $scope.info = null;
            $scope.urlError = null;
        };

        $scope.startExtraction = function() {

            if (!$scope.url.trim()) {
                return;
            }
            $scope.urlError = null;
            $scope.serverError = null;

            // console.log($scope.url);
            // make sure there's no lingering started event
            sessionStorage.removeItem('lastNewId');

            $scope.fetching = true;
            youtubeService.extractVideoInfo($scope.url.trim())
            .success(function(response) {
                if (response.error) {
                    $scope.urlError = response.error;
                } else {
                    $scope.embedURL = $sce.trustAsResourceUrl(
                        'https://www.youtube-nocookie.com/embed/' +
                        response.id + '?rel=0&showinfo=0'
                    );
                    $scope.info = response;
                    $scope.info.externalURL = (
                        'https://www.youtube.com/watch?v=' + response.id
                    );

                }
            })
            .error(function() {
                console.error.apply(console, arguments);
                $scope.serverError = true;
            })
            .finally(function() {
                $scope.fetching = false;
            });
        };

        $scope.createEvent = function() {
            $scope.creating = true;
            $scope.serverError = false;
            statusService.set('Fetching details from YouTube', 3);
            youtubeService.createEvent($scope.info)
            .success(function(response) {

                eventService.setId(response.id);
                $state.go('details', {id: response.id});
                statusService.set('Details fetched', 2);
            })
            .error(function() {
                console.error.apply(console, arguments);
                $scope.serverError = true;
            })
            .finally(function() {
                $scope.creating = false;
            });
        };

    }
])

.controller('RecordController',
    ['$scope', '$state', '$timeout', '$interval',
     'statusService', 'eventService', 'uploadService', 'staticService',
    function(
        $scope, $state, $timeout, $interval,
        statusService, eventService, uploadService, staticService
    ) {
        setDocumentTitle('Record a video');
        var $appContainer = angular.element('#content');
        staticService($appContainer.data('recordrtc-url'));
        staticService($appContainer.data('humanizeduration-url'));

        $scope.silhouetteURL = $appContainer.data('silhouette-url');

        preloadImage($scope.silhouetteURL);

        // Whether we're going to try to offer people to record
        // their screen.
        $scope.enableScreenCapture = false;
        if (!$scope.enableScreenCapture) {
            if (JSON.parse(localStorage.getItem('experimental', 'false'))) {
                $scope.enableScreenCapture = true;
            } else {
                console.log(
                    'To enable the Experimental Screencast Feature type ' +
                    'this in and hit Enter:\n\n\t' +
                    "localStorage.setItem('experimental', true);\n\n" +
                    'and then refresh this page.'
                );
            }

        }

        // let's assume that we will enable this feature
        $scope.enableFaceDetection = true;

        var ccvLoaded = false;
        staticService($appContainer.data('ccvjs-url'), function() {
            ccvLoaded = true;
        });
        // The face.js file is huge and it might not have downloaded
        // by the time we need it. So, let's depend on this onload.
        var facejsLoaded = false;
        staticService($appContainer.data('facejs-url'), function() {
            facejsLoaded = true;
        });

        $scope.fileError = null;

        var recorder = null;
        var stream = null;

        $scope.cameraStarted = false;
        $scope.showRecorderVideo = false;
        $scope.showPlaybackVideo = false;
        $scope.showSilhouette = false;
        $scope.showFaceDetection = false;
        $scope.showTips = false;

        $scope.toggleSilhouette = function() {
            $scope.showSilhouette = !$scope.showSilhouette;
            if ($scope.showSilhouette) {
                sessionStorage.removeItem('hide-silhouette');
            } else {
                sessionStorage.setItem('hide-silhouette', true);
            }
        };
        $scope.toggleFaceDetection = function() {
            $scope.showFaceDetection = !$scope.showFaceDetection;
            if ($scope.showFaceDetection) {
                sessionStorage.removeItem('hide-facedetection');
            } else {
                sessionStorage.setItem('hide-facedetection', true);
            }
        };
        $scope.hideFirefoxE10SWarning = function() {
            $scope.showFirefoxE10SWarning = false;
            sessionStorage.setItem('hideFirefoxE10SWarning', 1);
        };
        $scope.toggleTips = function() {
            $scope.showTips = !$scope.showTips;
        };

        function getUserMedia(config) {
            return navigator.mediaDevices.getUserMedia(config);
        }

        var nextFaceMessage = null;
        var faceMessageLocked = null;
        function displayFaceMessage(msg) {
            nextFaceMessage = msg;
            if (faceMessageLocked) {
                // console.log('locked!', msg);
                return;
            }
            var outer = document.querySelector('.face-message-outer');
            if (outer === null) {
                // the message outer hasn't been loaded in the DOM yet
                return;
            }
            var inner = outer.querySelector('.face-message');
            if (msg.length) {
                outer.style.display = 'block';
            } else {
                outer.style.display = 'none';
            }
            inner.textContent = msg;
            faceMessageLocked = true;
            setTimeout(function() {
                faceMessageLocked = false;
                if (nextFaceMessage !== null) {
                    displayFaceMessage(nextFaceMessage);
                    // displayFaceMessage('');
                }
            }, 1000);
        }

        var video;
        var canvas = document.querySelector('.video-outer canvas');
        var context = canvas.getContext('2d');
        var faceFound = false;
        var faceOnceFound = false;
        var faceNotFounds = 0;

        var faceDetectionFrame;
        function faceDetection() {
            // We draw the video stream onto a canvas which is necessary
            // so we can submit that canvas to the ccv library.
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            var faces = ccv.detect_objects(
                {canvas : (ccv.pre(canvas)), cascade: cascade, interval: 2, min_neighbors: 1}
            );
            if (faces.length) {
                // If latest one face was detected, we look at what
                // percentage it takes up for a whole width.
                // The numbers below are quite arbitrary, but were picked
                // by basically temporarly making the otherwise hidden
                // canvas visible and taking a judgement call of what would
                // be good numbers of the percentage.
                if (!faceFound) {
                    displayFaceMessage("Face found!");
                }
                faceFound = faceOnceFound = true;
                faceNotFounds = 0;  // reset

                var face = faces[0];
                var percentage = 100 * face.width / canvas.width;
                if  (percentage < 19.0) {
                    displayFaceMessage('A bit closer please');
                } else if (percentage > 30) {
                    displayFaceMessage('Back a bit please');
                } else {
                    displayFaceMessage('Good face distance');
                }

                // To debug how the face detection looks like,
                // uncomment this and change the canvas's CSS
                // to display:block.
                // context.fillRect(face.x, face.y, face.width, face.height);

            } else {
                if (faceNotFounds == 10 && faceOnceFound) {
                    displayFaceMessage('Face disappeared');
                    faceFound = false;
                }
                faceNotFounds++;
            }
        }

        $scope.startCamera = function() {
            var conf = {
                audio: true,
                video: {
                    width: 1280,
                    height: 720
                }
                // muted: true,
                // controls: false
            };

            $scope.enableSilhouette = true;
            $scope.mirroredViewFinder = true;

            getUserMedia(conf)
            .then(function(_stream) {
                stream = _stream;
                video = document.querySelector('video.recorder');
                video.src = URL.createObjectURL(_stream);
                video.muted = true;//conf.muted;
                video.controls = false;//conf.controls;
                video.play();
                recorder = RecordRTC(_stream, {
                    // Hmm, I wonder what other options we have here
                    type: 'video'
                });
                $scope.$apply(function() {

                    $scope.cameraStarted = true;
                    $scope.showRecorderVideo = true;
                    $timeout(function() {
                        // unless you've explicitly disabled it
                        if (!sessionStorage.getItem('hide-silhouette')) {
                            $scope.showSilhouette = true;
                        }
                        if (facejsLoaded && ccvLoaded) {
                            if (!sessionStorage.getItem('hide-facedetection')) {
                                $scope.showFaceDetection = true;
                            }
                        } else {
                            $scope.enableFaceDetection = false;
                        }

                    }, 500);
                });
                if (facejsLoaded && ccvLoaded) {
                    faceDetectionFrame = setInterval(faceDetection, 200);
                }
            })
            .catch(function(error) {
                // XXX this needs better error handling that is user-friendly
                console.warn('Unable to get the getUserMedia stream');
                console.error(error);
            });

        };

        $scope.showScreenCaptureTip = false;
        $scope.startScreenCapture = function(withAudio, source) {

            source = source || 'screen';
            if (source === 'screen') {
                $scope.showScreenCaptureTip = true;
            }
            withAudio = withAudio || false;
            var conf = {
                video: {
                    mozMediaSource: source,
                    mediaSource: source
                }
            };
            if (withAudio) {
                conf.audio = true;
            }

            $scope.enableSilhouette = false;
            $scope.showSilhouette = false;
            $scope.showFaceDetection = false;
            $scope.enableFaceDetection = false;

            getUserMedia(conf)
            .then(function(_stream) {
                stream = _stream;
                video = document.querySelector('video.recorder');
                video.src = URL.createObjectURL(_stream);
                video.muted = true;
                video.controls = false;
                video.play();
                recorder = RecordRTC(_stream, {
                    // Hmm, I wonder what other options we have here
                    type: 'video'
                });
                $scope.$apply(function() {
                    $scope.cameraStarted = true;
                    $scope.showRecorderVideo = true;
                    $scope.showScreenCaptureTip = false;
                });
            })
            .catch(function(error) {
                // XXX this needs better error handling that is user-friendly
                console.warn('Unable to get the getUserMedia stream for screen');
                console.error('ERROR', error);
                if (error.name && error.name === 'PermissionDeniedError') {
                    $scope.$apply(function() {
                        $scope.showScreenCaptureTip = false;
                        $scope.showFirefoxE10SWarning = false; // just in case
                        $scope.showPermissionDeniedError = true;
                        $scope.currentDomain = document.location.hostname;
                    });

                }
            });
        };

        $scope.startWindowCapture = function(withAudio) {
            withAudio = withAudio || false;
            // this is so similar to screen capture that we'll re-use it
            $scope.startScreenCapture(withAudio, 'window');
        };

        $scope.duration = 0;
        $scope.videoSize = 0;
        var durationPromise;
        function startDurationCounter() {
            $scope.duration = 0;
            durationPromise = $interval(function() {
                $scope.duration++;
            }, 1000);
        }

        function stopDurationCounter() {
            $interval.cancel(durationPromise);
        }

        $scope.startRecording = function() {
            $scope.countdown = 3;
            var countdownPromise = $interval(function() {
                $scope.countdown--;
                if ($scope.countdown < 1) {
                    $interval.cancel(countdownPromise);
                    startDurationCounter();
                    recorder.startRecording();
                    $scope.recording = true;
                    if (faceDetectionFrame !== null) {
                        clearInterval(faceDetectionFrame);
                    }
                }
            }, 1000);
        };

        var videoBlob;

        $scope.stopRecording = function() {
            stopDurationCounter();
            recorder.stopRecording(function(url) {
                $scope.recording = false;
                videoBlob = recorder.getBlob();
                $scope.videoSize = videoBlob.size;
                var video = document.querySelector('video.playback');
                video.src = url;
                video.muted = false;
                video.controls = true;
                video.onended = function() {
                    // Hack necessary because without it, in Firefox, you
                    // can't re-watch the video you just recorded.
                    video.pause();
                    video.src = URL.createObjectURL(recorder.getBlob());
                };
                $scope.$apply(function() {
                    $scope.showRecorderVideo = false;
                    $scope.showPlaybackVideo = true;
                });
                stream.stop();
            });
        };

        $scope.uploadRecording = function() {
            // make sure there's no lingering started event
            sessionStorage.removeItem('lastNewId');

            // $state.go('preemptiveDetails');
            uploadService.setDataFile(videoBlob);
            uploadService.startAndProcess($scope.duration);
            $state.go('preemptiveDetails');
        };

        $scope.resetRecording = function() {
            $scope.cameraStarted = false;
            $scope.recording = false;
            $scope.showRecorderVideo = true;
            $scope.showPlaybackVideo = false;
            $scope.duration = 0;
            $scope.videoSize = 0;
            $scope.startCamera();
        };
    }
])

.controller('DetailsController',
    ['$scope', '$stateParams', '$http', '$state', '$timeout',
     'eventService', 'statusService', 'localProxy',
    function(
        $scope, $stateParams, $http, $state, $timeout,
        eventService, statusService, localProxy
    ) {
        setDocumentTitle('Video details');
        $scope.eventService = eventService;
        var $appContainer = angular.element('#content');
        var eventUrl = $appContainer.data('event-url');
        $scope.event = {};
        $scope.errors = {};
        $scope.hasErrors = false;
        if (typeof $stateParams.id !== 'undefined') {
            eventService.setId(parseInt($stateParams.id, 10));
        } else {
            // we have to pick some defaults
            $scope.event.privacy = 'public';
        }

        $scope.$watch('event.privacy', function(value) {
            if (typeof value !== 'undefined') {
                if (value === 'public') {
                    $('#id_topics').parents('.form-group').show();
                } else {
                    $('#id_topics').parents('.form-group').hide();
                }
            }
        });

        // $scope.loading=true;return;
        if (eventService.getId() === null && !eventService.isUploading()) {
            var lastId = sessionStorage.getItem('lastNewId');
            if (lastId) {
                $state.go('details', {id: lastId});
                sessionStorage.removeItem('lastNewId');
            } else {
                $state.go('start');
            }
        } else if (eventService.getId() === null) {
            // the upload progress is still going on
            $scope.loading = false;
        } else {
            $scope.loading = true;
            $http.get(eventUrl.replace('0', eventService.getId()))
            .success(function(response) {
                if (response.event.status !== 'initiated') {
                    $state.go('published', {id: eventService.getId()});
                }
                $scope.event = response.event;
                if ($scope.event.placeholder_img) {
                    eventService.setPicture($scope.event.placeholder_img);
                } else if ($scope.event.picture) {
                    eventService.setPicture($scope.event.picture);
                }
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
                if (!eventService.getPicture()) {
                    // we need to "force load this"
                    eventService.scrape($scope.event.id);
                    eventService.lookForPicture($scope.event.id);
                }
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
            $scope.errors = {};
            $scope.hasErrors = false;
            // exceptionally change the channels list of a plain list
            $http.post(eventUrl.replace('0', eventService.getId()), $scope.event)
            .success(function(response) {
                if (response.errors) {
                    $scope.hasErrors = true;
                    $scope.errors = response.errors;
                    console.warn(response.errors);
                    statusService.set('Form submission error', 10);
                } else {
                    $scope.event = response.event;
                    statusService.set('Event saved!', 3);
                    if ($scope.event.picture) {
                        $state.go('summary', {id: eventService.getId()});
                    } else {
                        $state.go('picture', {id: eventService.getId()});
                    }
                }
            })
            .error(function() {
                console.error.apply(console, arguments);
            });
        };

        $scope.toggleShowOtherChannels = function() {
            $scope.showOtherChannels = !$scope.showOtherChannels;
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
        setDocumentTitle('Pick a picture');
        var $appContainer = angular.element('#content');
        $scope.thumbnails = [];
        $scope.picked = null;
        var id = $stateParams.id;

        var eventUrl = $appContainer.data('event-url').replace('0', id);
        var pictureUrl = $appContainer.data('picture-url').replace('0', id);
        var scrapeUrl = $appContainer.data('screencaptures-url').replace('0', id);
        var rotateUrl = $appContainer.data('rotate-url').replace('0', id);

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
        var reloadPromise = null;
        var displayAvailableScreencaptures = function() {
            $http.get(pictureUrl)
            .success(function(response) {
                if (response && response.thumbnails) {
                    $scope.loading = false;
                    $scope.stillLoading = false;
                    if (response.thumbnails.length > 1) {
                        if (reloadPromise) {
                            $interval.cancel(reloadPromise);
                        }
                    }
                    $scope.thumbnails = response.thumbnails;
                } else {
                    // statusService.set('No screen captures available yet.');
                    $scope.stillLoading = true;
                    if (response && !response.fetching && !reFetching) {
                        reFetching = true;
                        $http.post(scrapeUrl)
                        .success(function(scrapeResponse) {
                            if (!scrapeResponse.seconds) {
                                $scope.loading = false;
                                $scope.stillLoading = false;
                                $scope.durationError = true;
                                if (reloadPromise) {
                                    $interval.cancel(reloadPromise);
                                }
                            } else if (!scrapeResponse.no_pictures) {
                                $scope.loading = false;
                                $scope.stillLoading = false;
                                $scope.picturesError = true;
                                if (reloadPromise) {
                                    $interval.cancel(reloadPromise);
                                }
                            } else {
                                console.log(
                                    'Finished screencaps scraping',
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
        reloadPromise = $interval(displayAvailableScreencaptures, 3 * 1000);

        $scope.pickThumbnail = function(thumbnail) {
            // unpick the other, if there was one
            $scope.thumbnails.forEach(function(thisThumbnail) {
                thisThumbnail.picked = false;
            });
            thumbnail.picked = true;
            $http.post(pictureUrl, {picture: thumbnail.id})
            .success(function() {
                statusService.set('Chosen picture saved.', 3);
            })
            .error(console.error.bind(console));
            return false;
        };

        $scope.next = function() {
            if ($scope.event.title) {
                $state.go('summary', {id: $scope.event.id});
            } else {
                $state.go('details', {id: $scope.event.id});
            }
        };

        $scope.rotatePictures = function(direction) {
            $scope.rotating = true;
            $http.post(rotateUrl, {direction: direction})
            .finally(function() {
                displayAvailableScreencaptures();
                $scope.rotating = false;
            });
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
        setDocumentTitle('Summary');
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
                '?no-warning=1&no-footer=1';
            $scope.video.iframeSrc = $sce.trustAsResourceUrl(iframeUrl);
        }

        $scope.showDuration = function(seconds) {
            return moment().add(seconds, 'seconds').fromNow(true);
        };

        function fetchVideo() {
            $http.get(videoUrl)
            .success(function(response) {
                $scope.video = response;
                if (response.finished) {
                    showIframe();
                } else {
                    $timeout(function() {
                        fetchVideo();
                        // console.log('Rechecking if video is there now');
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
            if ($scope.event.upload) {
                $scope.loadingVideo = true;
                fetchVideo();
            } else if ($scope.event.youtube_id) {
                $scope.event.youtubeSrc = $sce.trustAsResourceUrl(
                    'https://www.youtube-nocookie.com/embed/' +
                    $scope.event.youtube_id +
                    '?rel=0&showinfo=0'
                );
            }
        })
        .error(eventService.handleErrorStatus)
        .finally(function() {
            $scope.loading = false;
        });

        $scope.publish = function() {
            $scope.publishing = true;
            $scope.publishingError = false;
            $http.post(publishUrl)
            .success(function() {
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
        'use strict';
        setDocumentTitle('Video published');
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
            $scope.event._absURL = document.location.protocol + '//' +
            document.location.hostname +
            response.event.url;
            if (!$scope.event.youtube_id) {
                $http.get(videoUrl)
                .success(function(response) {
                    $scope.video = response;
                })
                .error(eventService.handleErrorStatus);
            }
        })
        .error(eventService.handleErrorStatus)
        .finally(function() {
            $scope.loading = false;
        });

    }
])

.controller('NotFoundController',
    ['$scope',
    function($scope) {
        setDocumentTitle('Page not found');
        $scope.error = {
            title: 'Not Found',
            message: 'Page not found.'
        };
    }
])

.controller('NotYoursController',
    ['$scope',
    function($scope) {
        'use strict';
        setDocumentTitle('Not your video');
        $scope.error = {
            title: 'Not Yours',
            message: 'The page you tried to access tried to access data ' +
                     'about an event that doesn\'t belong to you.'
        };
    }
])


;

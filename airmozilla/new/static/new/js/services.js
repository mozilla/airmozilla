angular.module('new.services', [])

.service('eventService',
    ['$state',
    function($state) {
        var _id = null;
        var service = {};
        service.setId = function(id) {
            _id = id;
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
                console.error("STATUS", status, data);
            }
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

;

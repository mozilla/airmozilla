var app = angular.module('app', ['angularMoment']);

// From http://stackoverflow.com/a/8212878/205832 with modifications
function millisecondsToStr (milliseconds) {
    // TIP: to find current time in milliseconds, use:
    // var  current_time_milliseconds = new Date().getTime();

    function numberEnding (number) {
        return (number === 1) ? '' : 's';
    }

    var temp = Math.floor(milliseconds / 1000);
    var years = Math.floor(temp / 31536000);
    if (years) {
        return years + ' year' + numberEnding(years);
    }
    //TODO: Months! Maybe weeks?
    var days = Math.floor((temp %= 31536000) / 86400);
    if (days) {
        return days + ' day' + numberEnding(days);
    }
    var hours = Math.floor((temp %= 86400) / 3600);
    if (hours) {
        return hours + ' hour' + numberEnding(hours);
    }
    var minutes = Math.floor((temp %= 3600) / 60);
    if (minutes) {
        return minutes + ' minute' + numberEnding(minutes);
    }
    var seconds = temp % 60;
    if (seconds) {
        return seconds + ' second' + numberEnding(seconds);
    }
    if (milliseconds) {
        seconds = milliseconds / 1000;
        return seconds + ' second' + numberEnding(seconds);
    }
    return 'less than a second'; //'just now' //or other string you like;
}


// http://stackoverflow.com/a/1714899/205832
var serializeObject = function(obj) {
    var str = [];
    for(var p in obj)
      if (obj.hasOwnProperty(p)) {
          str.push(encodeURIComponent(p) + "=" + encodeURIComponent(obj[p]));
      }
    return str.join("&");
};

app.controller('CronLoggerController', ['$scope', '$http',
    function($scope, $http) {
        'use strict';

        $scope.expandedView = true;
        $scope.logs = [];
        $scope.count = 0;
        $scope.loading = true;

        function reset() {
            $scope.logs = [];
            $scope.count = 0;
            $scope.loading = true;
        }

        $scope.formatDate = function(date) {
            return moment(date).format('ddd, MMM D, YYYY, h:mma UTCZZ');
        };

        $scope.showDuration = function(seconds) {
            return millisecondsToStr(seconds * 1000);
        };

        function fetchLogs(params) {
            var url = location.pathname + 'data/';
            url += '?' + serializeObject(params);
            return $http.get(url);
        }

        $scope.search_job = null;
        $scope.$watch('search_job', function(new_value, old_value) {
            if (new_value !== old_value) {
                if (new_value !== undefined) {
                    document.location.hash = new_value.value;
                } else {
                    document.location.hash = '';
                }
                reset();
                load();
            }
        });

        function load() {
            var data = {};
            if ($scope.search_job && $scope.search_job.value) {
                data.job = $scope.search_job.value;
            }
            fetchLogs(data)
                .success(function(response) {
                    $scope.logs = response.logs;
                    $scope.count = response.count;
                    $scope.jobs = response.jobs;
                }).error(function(response, status) {
                    console.warn('Failed to fetch cron logs', status);
                }).finally(function() {
                    $scope.loading = false;
                });
        }
        if (document.location.hash) {
            $scope.search_job = {'value': document.location.hash.substring(
                1,
                document.location.hash.length
            )};
        }
        // initial load
        load();

    }]);

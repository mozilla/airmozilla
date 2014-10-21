var app = angular.module('app', ['angularMoment']);

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

        $scope.logs = [];
        $scope.count = 0;
        $scope.loading = true;

        $scope.formatDate = function(date) {
            return moment(date).format('ddd, MMM D, YYYY, h:mma UTCZZ');
        };

        function fetchLogs(params) {
            var url = location.pathname + 'data/';
            url += '?' + serializeObject(params);
            return $http.get(url);
        }

        $scope.search_job = null;
        $scope.$watch('search_job', function(new_value, old_value) {
            if (new_value !== old_value) {
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
        // initial load
        load();

    }]);

angular.module('app', [])

.filter('customNumber', ['$filter',
function($filter) {
    return function(input, fractionSize) {
        if (angular.isNumber(input)) {
            return $filter('number')(input, fractionSize);
        } else {
            return input;
        }
    };
}])

.controller('DashboardController', ['$scope', '$http',
function($scope, $http) {
    'use strict';

    $http.get(location.pathname + 'data/')
    .success(function(response) {
        $scope.groups = response.groups;
    }).error(function() {
        console.log(arguments);
    });
}])

;

var app = angular.module('app', []);

app.filter('showDelta', function() {
    return function(input) {
        if (typeof input === 'undefined') {
            return '';
        }
        if (input > 0) {
            return "+" + input;
        } else if (input < 0) {
            return "" + input;
        } else {
            return "\u00B1" + input;
        }
    };
});

app.controller('DashboardController', ['$scope', '$http',
function($scope, $http) {
    'use strict';

    $http.get(location.pathname + 'data/')
    .success(function(response) {
        $scope.groups = response.groups;
    }).error(function() {
        console.log(arguments);
    });

    $scope.deltaClass = function(delta) {
        if (delta > 0) {
            return 'positive';
        } else if (delta < 0) {
            return 'negative';
        } else {
            return 'zero';
        }
    };

}]);

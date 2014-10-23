var app = angular.module('app', []);

app.controller('DashboardController', ['$scope', '$http',
function($scope, $http) {
    'use strict';

    $http.get(location.pathname + 'data/')
    .success(function(response) {
        $scope.groups = response.groups;
    }).error(function() {
        console.log(arguments);
    });
}]);

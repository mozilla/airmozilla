angular.module('app', [])

.controller('DashboardGraphsController',
['$scope', '$http',
function($scope, $http) {
    'use strict';

    function displayData(data, target, title, legends, description) {
        for (var i = 0; i < data.length; i++) {
            data[i] = MG.convert.date(data[i], 'date');
        }

        MG.data_graphic({
            title: title,
            description: description,
            data: data,
            // width: 800,
            full_width: true,
            height: 250,
            right: 40,
            // missing_is_hidden: true,
            xax_start_at_min: true,
            target: target,
            // show_secondary_x_label: false,
            legend: legends,
            // legend_target: '.legend'
        });
    }

    $scope.loading = true;
    $http.get(location.pathname + 'data/')
    .success(function(response) {
        response.groups.forEach(function(group) {
            displayData(
                group.data,
                '#' + group.type,
                group.title,
                group.legends,
                group.descrption
            );
        });
        $scope.loading = false;
    }).error(function() {
        console.log(arguments);
    });
}])

;

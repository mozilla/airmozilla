var app = angular.module('suggestionsmanagerApp', ['angularMoment']);

function escapeRegExp(string){
    return string.replace(/([.*+?^=!:${}()|\[\]\/\\])/g, "\\$1");
}

// We already have a limitTo filter built-in to angular,
// let's make a startFrom filter
app.filter('startFrom', function() {
    return function(input, start) {
        if (angular.isUndefined(input)) return input;
        start = +start; //parse to int
        return input.slice(start);
    };
});


app.controller('SuggestionsManagerController',
['$scope', '$http',
function SuggestionsManagerController($scope, $http) {
    'use strict';

    $scope.sorting = 'submitted';
    $scope.$watch('sorting', function(value) {
        if (value === 'submitted') {
            $scope.sorting_reverse = true;
        } else {
            $scope.sorting_reverse = false;
        }
    });

    $scope.toggleSortingReverse = function() {
        $scope.sorting_reverse = !$scope.sorting_reverse;
    };

    $scope.setSorting = function(key) {
        if ($scope.sorting == key) {
            $scope.toggleSortingReverse();
        }
        $scope.sorting = key;
    };

    $scope.loading = true;
    function fetchSuggestions(params) {
        var url = location.pathname + 'data/';
        // url += '?' + serializeObject(params);
        return $http.get(url);
    }
    $scope.events = [];
    $scope.currentPage = 0;

    var pageSize = 25;  // default
    $scope.pageSizeOptions = [10, 25, 50];
    // attempt to load a different number from localStorage
    var pageSizeStorageKey = 'pageSize' + window.location.pathname;
    if (window.localStorage) {
        var localpageSize = window.localStorage.getItem(pageSizeStorageKey);
        if (localpageSize) {
            pageSize = +localpageSize;
        }
    }
    $scope.pageSize = pageSize;
    $scope.$watch('pageSize', function(value) {
        if (window.localStorage) {
            window.localStorage.setItem(pageSizeStorageKey, value);
        }
    });

    $scope.numberOfPages = function(items){
        if (typeof items === 'undefined') return 0;
        return Math.ceil(items.length / $scope.pageSize);
    };
    $scope.formatDate = function(date) {
        return moment(date).format('ddd, MMM D, YYYY, h:mma UTCZZ');
    };

    $scope.resetCurrentPage = function() {
        $scope.currentPage = 0;
    };
    $scope.resetFilter = function(key) {
        $scope[key] = '';
    };

    /* Filtering */
    $scope.hasFilter = function() {
        return ($scope.search_title || $scope.search_location || $scope.search_creator || $scope.search_status || $scope.search_old);
    };
    $scope.clearFilter = function() {
        $scope.search_title = '';
        $scope.search_location = '';
        $scope.search_creator = '';
        $scope.search_status = '';
        $scope.search_old = '';
    };

    $scope.search_title = '';
    var search_title_regex = null;
    $scope.$watch('search_title', function(value) {
        search_title_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_location = '';
    var search_location_regex = null;
    $scope.$watch('search_location', function(value) {
        search_location_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_creator = '';
    var search_creator_regex = null;
    $scope.$watch('search_creator', function(value) {
        search_creator_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_status = '';

    $scope.search_old = 'active';
    var search_old_bool = null;
    $scope.$watch('search_old', function(value) {
        search_old_bool = value === 'active';
    });

    $scope.filterBySearch = function(item) {
        // if (!$scope.hasFilter()) return true;

        // gimme a reason NOT to include this

        if ($scope.search_title) {
            if (!search_title_regex.test(item.title)) {
                return false;
            }
        }
        if ($scope.search_location) {
            if (!search_location_regex.test(item.location)) {
                return false;
            }
        }

        if ($scope.search_creator) {
            if (!search_creator_regex.test(item.user.email)) {
                return false;
            }
        }
        if ($scope.search_status) {
            if ($scope.search_status !== item.status) {
                return false;
            }
        }
        if ($scope.search_old) {
            if (search_old_bool === item.old) {
                return false;
            }
        }
        return true;
    };
    /* End filtering */

    $scope.url = function(viewname, item) {
        return $scope.urls[viewname].replace('0', item);
    };

    function loadAll() {
        fetchSuggestions({})
          .success(function(data) {
              $scope.urls = data.urls;
              $scope.events = data.events;
              $scope.count_old = data.events.filter(function(event) {
                  return event.old;
              }).length;
          }).error(function(data, status) {
              console.warn('Failed to fetch ALL', status);
          }).finally(function() {
              $scope.loading = false;
          });
    }
    loadAll();
}]);

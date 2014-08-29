var app = angular.module('tagmanagerApp', []);

// http://stackoverflow.com/a/1714899/205832
var serializeObject = function(obj) {
    var str = [];
    for(var p in obj)
      if (obj.hasOwnProperty(p)) {
          str.push(encodeURIComponent(p) + "=" + encodeURIComponent(obj[p]));
      }
    return str.join("&");
};

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


TagManagerController.$inject = ['$scope', '$http', '$timeout'];

function TagManagerController($scope, $http, $timeout) {
    'use strict';

    $scope.sort_by = 'name';
    $scope.sort_by_desc = false;
    $scope.show_only_repeated = 'no';

    $scope.sortBy = function(key, desc_default) {
        desc_default = desc_default || false;
        if (key !== $scope.sort_by) {
            // changing column to sort by
            $scope.sort_by_desc = desc_default;
        } else {
            // just toggle
            $scope.sort_by_desc = !$scope.sort_by_desc;
        }
        $scope.sort_by = key;
    };

    $scope.loading = true;
    function fetchTags(params) {
        var url = location.pathname + 'data/';
        url += '?' + serializeObject(params);
        return $http.get(url);
    }
    $scope.events = [];
    $scope.currentPage = 0;

    var pageSize = 10;  // default
    // attempt to load a different number from localStorage
    if (window.localStorage) {
        var localpageSize = window.localStorage.getItem('pageSize');
        if (localpageSize) {
            pageSize = +localpageSize;
        }
    }
    $scope.pageSize = pageSize;
    $scope.$watch('pageSize', function(value) {
        if (window.localStorage) {
            window.localStorage.setItem('pageSize', value);
        }
        $scope.currentPage = 0;
    });

    $scope.$watch('currentPage', function(value) {
        if (value) {
            window.location.hash = '#' + (++value);
        }
    });

    $timeout(function() {
        var hash_page_regex = new RegExp(/#(\d+)/);
        if (hash_page_regex.test(window.location.hash)) {
            var page = +window.location.hash.match(hash_page_regex)[1];
            $scope.currentPage = --page;
        }
    }, 100);

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
        return ($scope.search_name || $scope.search_minimum);
    };
    $scope.clearFilter = function() {
        $scope.search_name = '';
        $scope.search_minimum = '';
    };

    $scope.search_minimum = '';

    $scope.search_name = '';
    var search_name_regex = null;
    $scope.$watch('search_name', function(value) {
        search_name_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.filterBySearch = function(item) {
        if (!$scope.hasFilter()) return true;

        // gimme a reason NOT to include this
        if ($scope.search_name) {
            if (!search_name_regex.test(item.name)) {
                return false;
            }
        }
        if ($scope.search_minimum) {
            if (item._usage_count < $scope.search_minimum) {
                return false;
            }
        }
        return true;
    };

    $scope.filterByRepeated = function(item) {
        if ($scope.show_only_repeated === 'yes') {
            return item._repeated;
        }
        return true;
    };
    /* End filtering */

    function loadAll() {
        fetchTags({})
          .success(function(data) {
              $scope.tags = data.tags;
          }).error(function(data, status) {
              console.warn('Failed to fetch ALL tags', status);
          }).finally(function() {
              $scope.loading = false;
          });
    }
    loadAll();
}

var app = angular.module('usermanagerApp', ['angularMoment']);

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


UserManagerController.$inject = ['$scope', '$http'];

function UserManagerController($scope, $http) {
    'use strict';

    $scope.sorting = 'last_login';
    $scope.$watch('sorting', function(value) {
        if (value === 'last_login') {
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
    function fetchUsers(params) {
        var url = location.pathname + 'data/';
        url += '?' + serializeObject(params);
        return $http.get(url);
    }
    $scope.events = [];
    $scope.currentPage = 0;

    var pageSize = 10;  // default
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
        return ($scope.search_email || $scope.search_group || $scope.search_staff || $scope.search_status);
    };
    $scope.clearFilter = function() {
        $scope.search_email = '';
        $scope.search_group = '';
        $scope.search_staff = '';
        $scope.search_status = '';
    };

    $scope.search_email = '';
    var search_email_regex = null;
    $scope.$watch('search_email', function(value) {
        search_email_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_group = '';
    var search_group_regex = null;
    $scope.$watch('search_group', function(value) {
        search_group_regex = new RegExp(escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_staff = '';

    $scope.filterBySearch = function(item) {
        // if (!$scope.hasFilter()) return true;

        // gimme a reason NOT to include this
        if ($scope.search_email) {
            if (!search_email_regex.test(item.email)) {
                return false;
            }
        }
        if ($scope.search_staff) {
            if ($scope.search_staff === 'staff') {
                if (!item.is_staff) {
                    return false;
                }
            } else {
                if (item.is_staff) {
                    return false;
                }
            }
        }
        if ($scope.search_group) {
            if (!item.groups) return false;
            var matched = false;
            if ($scope.search_group === '*') {
                return item.groups.length;
            }
            item.groups.forEach(function(group) {
                if (search_group_regex.test(group)) {
                    matched = true;
                }
            });
            return matched;
        }
        if ($scope.search_status) {
            if ($scope.search_status === 'contributor') {
                if (!item.is_contributor) {
                    return false;
                }
            } else if ($scope.search_status === 'superuser') {
                if (!item.is_superuser) {
                    return false;
                }
            } else if ($scope.search_status === 'inactive') {
                if (!item.is_inactive) {
                    return false;
                }
            }
        }
        return true;
    };
    /* End filtering */

    $scope.url = function(viewname, item) {
        return $scope.urls[viewname].replace('0', item);
    };

    function loadAll() {
        fetchUsers({})
          .success(function(data) {
              $scope.urls = data.urls;
              $scope.users = data.users;
          }).error(function(data, status) {
              console.warn('Failed to fetch ALL', status);
          }).finally(function() {
              $scope.loading = false;
          });
    }
    loadAll();
}

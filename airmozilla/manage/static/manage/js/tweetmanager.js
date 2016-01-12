var app = angular.module('tweetmanagerApp', ['angularMoment']);

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


app.controller('TweetManagerController',
['$scope', '$http', '$timeout',
function TweetManagerController($scope, $http, $timeout) {
    'use strict';

    $scope.sort_by = 'send_date';
    $scope.sort_by_desc = true;

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
    function fetchTweets(params) {
        var url = location.pathname + 'data/';
        url += '?' + serializeObject(params);
        return $http.get(url);
    }
    $scope.tweets = [];
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

    $scope.numberOfPages = function(items) {
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
        return (
            $scope.search_event || $scope.search_text || $scope.search_status
        );
    };
    $scope.clearFilter = function() {
        $scope.search_event = '';
        $scope.search_text = '';
        $scope.search_status = '';
    };

    $scope.search_event = '';
    var search_event_regex = null;
    $scope.$watch('search_event', function(value) {
        search_event_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_text = '';
    var search_text_regex = null;
    $scope.$watch('search_text', function(value) {
        search_text_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    var today = new Date();
    $scope.filterBySearch = function(item) {
        if (!$scope.hasFilter()) return true;

        // gimme a reason NOT to include this
        if ($scope.search_event) {
            if (!search_event_regex.test(item.event.title)) {
                return false;
            }
        }
        if ($scope.search_text) {
            if (!search_text_regex.test(item.text)) {
                return false;
            }
        }
        if ($scope.search_status) {
            if ($scope.search_status === 'future') {
                return moment(item.send_date).diff(today) > 0;
            } else if ($scope.search_status === 'past') {
                return moment(item.send_date).diff(today) < 0;
            } else if ($scope.search_status === 'failed') {
                return !item.tweet_id && item.sent_date;
            } else {
                throw new Error('not implemented ' + $scope.search_status);
            }
        }
        return true;
    };
    /* End filtering */

    $scope.url = function(viewname, item) {
        return $scope.urls[viewname].replace('0', item);
    };

    function loadAll() {
        fetchTweets({})
          .success(function(data) {
              $scope.tweets = data.tweets;
              $scope.urls = data.urls;
          }).error(function(data, status) {
              console.warn('Failed to fetch ALL tweets', status);
          }).finally(function() {
              $scope.loading = false;
          });
    }
    loadAll();
}]);

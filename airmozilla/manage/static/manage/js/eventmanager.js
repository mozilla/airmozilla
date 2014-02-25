var app = angular.module('eventmanagerApp', ['angularMoment']);

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
        start = +start; //parse to int
        return input.slice(start);
    };
});


EventManagerController.$inject = ['$scope', '$http'];

function EventManagerController($scope, $http) {
    'use strict';

    $scope.first_loading = true;
    $scope.second_loading = true;
    function fetchEvents(params) {
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
        return ($scope.search_title ||
                $scope.search_location ||
                $scope.search_cat_chan ||
                $scope.search_archived ||
                $scope.search_status ||
                $scope.search_start_time ||
                $scope.search_privacy);
    };
    $scope.clearFilter = function() {
        $scope.search_title = '';
        $scope.search_location = '';
        $scope.search_archived = false;
        $scope.search_cat_chan = '';
        $scope.search_status = '';
        $scope.search_privacy = '';
        $scope.search_start_time = '';
    };

    $scope.search_title = '';
    var search_title_regexes = [];
    var search_slug_regex = null;
    $scope.$watch('search_title', function(value) {
        search_title_regexes = [];
        angular.forEach(value.trim().split(' '), function(part) {
            search_title_regexes.push(new RegExp('\\b' + escapeRegExp(part), 'i'));
        });
        if (value.trim()) {
            search_slug_regex = new RegExp('^' + escapeRegExp(value.trim()), 'i');
        }
        $scope.currentPage = 0;
    });

    $scope.search_location = '';
    var search_location_regex = null;
    $scope.$watch('search_location', function(value) {
        search_location_regex = new RegExp(escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_cat_chan = '';
    var search_cat_chan_regex = null;
    $scope.$watch('search_cat_chan', function(value) {
        search_cat_chan_regex = new RegExp(escapeRegExp(value), 'i');
        $scope.currentPage = 0;
    });

    $scope.search_status = '';
    $scope.search_privacy = '';
    $scope.search_start_time = '';
    $scope.search_archived = false;

    $scope.$watch('search_status', function() {
        $scope.currentPage = 0;
    });
    $scope.$watch('search_privacy', function() {
        $scope.currentPage = 0;
    });
    $scope.$watch('search_start_time', function() {
        $scope.currentPage = 0;
    });
    $scope.$watch('search_archived', function() {
        $scope.currentPage = 0;
    });

    $scope.filterBySearch = function(event) {
        if (!$scope.hasFilter()) return true;

        // gimme a reason NOT to include this
        if ($scope.search_title) {
            var unmatched = false;
            angular.forEach(search_title_regexes, function(regex) {
                if (!unmatched && !regex.test(event.title)) {
                    unmatched = true;
                }
            });
            if (unmatched && search_slug_regex && search_slug_regex.test(event.slug)) {
                unmatched = false;
            }
            // at least one regex said no
            if (unmatched) return false;
        }
        if ($scope.search_location) {
            if (!search_location_regex.test(event.location)) {
                return false;
            }
        }
        if ($scope.search_cat_chan) {
            // it must match either the category or one of the channels
            var something = false;
            if (search_cat_chan_regex.test(event.category)) {
                something = true;
            } else {
                angular.forEach(event.channels, function(channel) {
                    if (!something && search_cat_chan_regex.test(channel)) {
                        something = true;
                    }
                });
            }
            //if (!something) return false;
            return something;
        }
        if ($scope.search_status && $scope.search_status !== event.status) {
            return false;
        }
        if ($scope.search_privacy && $scope.search_privacy !== event.privacy) {
            return false;
        }
        if ($scope.search_start_time && !in_search_start_time_range(moment(event.start_time_iso))) {
            return false;
        }
        if ($scope.search_archived && !event.archive_time) {
            return false;
        }
        return true;
    };
    var search_start_times = [];
    $scope.$watch('search_start_time', function(value) {
        if (value) {
            value = moment.utc(value);
            search_start_times = [value, value.clone().add('days', 1)];
        }
    });
    function in_search_start_time_range(date) {
        return date > search_start_times[0] && date < search_start_times[1];
    }

    $scope.selectSearchStatus = function(status) {
        $scope.search_status = status;
    };
    $scope.selectSearchPrivacy = function(privacy) {
        $scope.search_privacy = privacy;
    };
    /* End filtering */

    function loadAll() {
        fetchEvents({})
          .success(function(data) {
              $scope.events = data.events;
          }).error(function(data, status) {
              console.warn('Failed to fetch ALL events', status);
          }).finally(function() {
              $scope.second_loading = false;
          });
    }

    function loadSome() {
        fetchEvents({limit: $scope.pageSize})
          .success(function(data) {
              $scope.events = data.events;
              loadAll();
          }).error(function(data, status) {
              console.warn('Failed to fetch events', status);
          }).finally(function() {
              $scope.first_loading = false;
          });
    }
    loadSome();
}

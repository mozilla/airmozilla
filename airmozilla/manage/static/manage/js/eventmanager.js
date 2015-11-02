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


app.controller('EventManagerController',
['$scope', '$http', '$interval',
function EventManagerController($scope, $http, $interval) {
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
    $scope.sorting = 'modified';
    $scope.sorting_reverse = true;
    $scope.reading_from_cache = false;

    $scope.$watch('sorting', function(value) {
        if (value === 'modified') {
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
        return ($scope.search_title ||
                $scope.search_location ||
                $scope.search_cat_chan ||
                $scope.search_archived ||
                $scope.search_status ||
                $scope.search_start_time ||
                $scope.search_privacy ||
                $scope.search_only);
    };
    $scope.clearFilter = function() {
        $scope.search_title = '';
        $scope.search_location = '';
        $scope.search_archived = '';
        $scope.search_cat_chan = '';
        $scope.search_status = '';
        $scope.search_privacy = '';
        $scope.search_start_time = '';
        $scope.search_only = '';
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
    $scope.search_archived = '';
    $scope.search_only = '';

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
    $scope.$watch('search_only', function() {
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
            if (['blank', 'empty', 'pre-recorded'].indexOf($scope.search_location) > -1) {
                // then strangely match those with no location
                if (event.location) {
                    return false;
                }
            } else if (!search_location_regex.test(event.location)) {
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
        if ($scope.search_archived) {
            if ($scope.search_archived === 'archived') {
                if (!event.archive_time) {
                    return false;
                }
            } else {
                if (event.archive_time) {
                    return false;
                }
            }
        }
        if ($scope.search_only) {
            if ($scope.search_only === 'upcoming') {
                return !!event.is_upcoming;
            } else if ($scope.search_only === 'needs_approval') {
                return !!event.needs_approval;
            } else if ($scope.search_only === 'live') {
                return !!event.is_live;
            } else {
                console.warn('Unrecognized option', $scope.search_only);
            }
        }
        return true;
    };
    var search_start_times = [];
    $scope.$watch('search_start_time', function(value) {
        if (value) {
            value = moment.utc(value);
            search_start_times = [value, value.clone().add('days', 1)];
            $scope.sorting = 'start_time_iso';
            $scope.sorting_reverse = true;
        }
    });
    function in_search_start_time_range(date) {
        return date > search_start_times[0];
    }

    $scope.selectSearchStatus = function(status) {
        $scope.search_status = status;
    };
    $scope.selectSearchPrivacy = function(privacy) {
        $scope.search_privacy = privacy;
    };
    $scope.selectSearchOnly = function(only) {
        if (only === $scope.search_only) {
            $scope.search_only = '';
        } else {
            $scope.search_only = only;
        }
    };
    /* End filtering */

    $scope.urls = {};
    $scope.url = function(viewname, item) {
        if (!$scope.urls[viewname]) {
            console.warn('No known URL view by that name', viewname);
        }
        return $scope.urls[viewname].replace('0', item);
    };


    $scope.modified_events = [];

    $scope.replaceModifiedEvents = function() {
        var modified = {};
        $scope.modified_events.forEach(function(event) {
            modified[event.id] = event;
        });
        $scope.events.forEach(function(event, i) {
            if (modified[event.id]) {
                $scope.events[i] = modified[event.id];
                delete modified[event.id];
            }
        });
        // add what's left
        for (var id in modified) {
            $scope.events.push(modified[id]);
        }
        $scope.max_modified = $scope.next_max_modified;
        $scope.modified_events = [];
    };

    function lookForModifiedEvents() {
        /* This function is repeatedly called in an interval timer */
        fetchEvents({since: $scope.max_modified})
        .success(function(response) {
            if (response.max_modified) {
                $scope.modified_events = response.events;
                $scope.next_max_modified = response.max_modified;
            }
        })
        .error(function() {
            console.error.apply(console, arguments);
        });
    }

    $scope.load_error = null;

    function loadAll() {
        fetchEvents({})
          .success(function(data) {
              $scope.load_error = null;
              localStorage.setItem('eventmanager', JSON.stringify(data));
              $scope.events = data.events;
              $scope.reading_from_cache = false;
              $scope.max_modified = data.max_modified;
              // every 10 seconds, look for for changed events
              $interval(lookForModifiedEvents, 10 * 1000);
          }).error(function(data, status) {
              console.log(data, status);
              $scope.load_error = 'Failed to fetch ALL events (' + status + ')';
          }).finally(function() {
              $scope.second_loading = false;
          });
    }

    $scope.retryLoadAll = loadAll;

    function loadSome() {
        fetchEvents({limit: $scope.pageSize})
          .success(function(data) {
              $scope.urls = data.urls;
              $scope.events = data.events;
              loadAll();
          }).error(function(data, status) {
              console.warn('Failed to fetch events', status);
          }).finally(function() {
              $scope.first_loading = false;
          });
    }
    var data = JSON.parse(localStorage.getItem('eventmanager') || '{}');
    if (data && data.urls && data.events) {
        $scope.reading_from_cache = true;
        $scope.first_loading = false;
        $scope.urls = data.urls;
        $scope.events = data.events;
        loadAll();
    } else {
        loadSome();
    }

}]);

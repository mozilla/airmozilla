var app = angular.module('picturegalleryApp', ['angularMoment']);

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


// from https://gist.github.com/yrezgui/5653591
app.filter( 'filesize', function () {
     var units = [
        'bytes',
        'KB',
        'MB',
        'GB',
        'TB',
        'PB'
     ];

     return function( bytes, precision ) {
        if ( isNaN( parseFloat( bytes )) || ! isFinite( bytes ) ) {
            return '?';
        }

        var unit = 0;

        while ( bytes >= 1024 ) {
          bytes /= 1024;
          unit ++;
        }

        return bytes.toFixed( + precision ) + ' ' + units[ unit ];
     };
});

// We already have a limitTo filter built-in to angular,
// let's make a startFrom filter
app.filter('startFrom', function() {
    return function(input, start) {
        if (angular.isUndefined(input)) return input;
        start = +start; //parse to int
        return input.slice(start);
    };
});


app.controller('PictureGalleryController', ['$scope', '$http',
    function($scope, $http) {
        'use strict';

        $scope.loading = true;

        $scope.currentPage = 0;

        $scope.numberOfPages = function(items){
            if (typeof items === 'undefined') return 0;
            return Math.ceil(items.length / $scope.pageSize);
        };

        /* Page size */
        var pageSize = 8;  // default
        $scope.pageSizeOptions = [8, 16, 32];
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
        /* End page size */

        $scope.saveNotes = function(picture) {

            picture._saving = true;
            // a little bit of jQuery hasn't hurt anybody
            var csrf = $('input[name="csrfmiddlewaretoken"]').val();
            var url = $scope.url('manage:picture_edit', picture.id);
            var data = {
                'csrfmiddlewaretoken': csrf,
                'notes': picture.notes
            };
            $http({
                method: 'POST',
                url: url,
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                data: serializeObject(data)
            })
            .success(function() {
                picture._saving = false;
            });
            return false;
        };

        /* Filtering */
        $scope.resetFilter = function(key) {
            $scope[key] = '';
        };

        $scope.hasFilter = function() {
            return ($scope.search_notes || $scope.search_created);
        };
        $scope.clearFilter = function() {
            $scope.search_notes = '';
            $scope.search_created = '';
        };

        $scope.search_notes = '';
        var search_notes_regex = null;
        $scope.$watch('search_notes', function(value) {
            search_notes_regex = new RegExp('\\b' + escapeRegExp(value), 'i');
            $scope.currentPage = 0;
        });

        $scope.search_created = '';
        var search_created_a, search_created_b;
        $scope.$watch('search_created', function(value) {
            //var v = moment(value);
            if (value === 'today') {
                search_created_a = moment().startOf('day');
                search_created_b = null;
            } else if (value === 'yesterday') {
                search_created_b = moment().startOf('day');
                search_created_a = search_created_b.subtract(1, 'days');
            } else if (value === 'this_week') {
                search_created_a = moment().startOf('week');
                search_created_b = null;
            } else if (value === 'older_than_this_week') {
                search_created_a = null;
                search_created_b = moment().startOf('week');
            } else if (value) {
                console.warn("Unrecognized value for search_created", value);
            }
            $scope.currentPage = 0;
        });

        $scope.filterBySearch = function(item) {
            // gimme a reason NOT to include this
            if ($scope.search_notes) {
                if (!search_notes_regex.test(item.notes)) {
                    return false;
                }
            }

            if ($scope.search_created) {
                var created = moment(item.created);
                if (search_created_a && search_created_b) {
                    if (created < search_created_a || created > search_created_b) {
                        return false;
                    }
                } else if (search_created_a) {
                    if (created < search_created_a) {
                        return false;
                    }
                } else if (search_created_b) {
                    if (created > search_created_b) {
                        return false;
                    }
                }
            }
            return true;
        };
        /* End filtering */

        $scope.url = function(viewname, item) {
            if (!$scope.urls[viewname]) {
                console.warn('Invalid viewname', viewname);
            }
            return $scope.urls[viewname].replace('0', item);
        };

        function fetchPictures(params) {
            var url = location.pathname + 'data/';
            url += '?' + serializeObject(params);
            return $http.get(url);
        }

        function load() {
            fetchPictures()
                .success(function(data) {
                    $scope.pictures = data.pictures;
                    $scope.urls = data.urls;
                }).error(function(data, status) {
                    console.warn('Failed to fetch pictures', status);
                }).finally(function() {
                    $scope.loading = false;
                });
        }
        // initial load
        load();

    }]);

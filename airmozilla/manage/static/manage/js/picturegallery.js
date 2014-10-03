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

        // $scope.pictures = [];
        $scope.loading = true;

        $scope.currentPage = 0;

        // var pageSize = 10;  // default
        $scope.pageSize = 6;
        $scope.numberOfPages = function(items){
            if (typeof items === 'undefined') return 0;
            return Math.ceil(items.length / $scope.pageSize);
        };

        $scope.saveNotes = function(picture) {

            console.log(picture);
            picture._saving = true;
            // a little bit of jQuery hasn't hurt anybody
            // var form = $('form[method="post"]')
            var csrf = $('input[name="csrfmiddlewaretoken"]').val();
            var url = $scope.url('manage:picture_edit', picture.id);
            console.log(url)
            var data = {
                'csrfmiddlewaretoken': csrf,
                'notes': picture.notes
            };
            console.log(data)
            $http({
                method: 'POST',
                url: url,
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },

                data: serializeObject(data)
            })
            .success(function() {
                console.log('Notes saved');
                picture._saving = false;
            });
            return false;
        };

        $scope.url = function(viewname, item) {
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

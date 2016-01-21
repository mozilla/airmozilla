angular.module('savedsearches', [])

.run(['$http', function($http) {
    var token = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    if (!token) {
        throw 'No CSRF token';
    }
    $http.defaults.headers.post['X-CSRFToken'] = token;

    // The little pure HTML & CSS blurb on the home page that is
    // always there before any angular kicks in.
    $('div.basic-loading').remove();
}])

.controller('SavedSearchesController',
    ['$scope', '$http', '$timeout',
    function($scope, $http, $timeout) {
        var $appContainer = angular.element('#content');
        var dataURL = $appContainer.data('data-url');
        var deleteURL = $appContainer.data('delete-url');
        var editURL = $appContainer.data('edit-url');
        var sampleURL = editURL + '?sample=true';
        if (!dataURL) {
            throw new Error('no data-url');
        }
        $scope.savedsearches = [];
        $scope.loading = true;
        $scope.failed = false;

        var key = 'savedsearchescounts';
        var rememberedCounts = JSON.parse(sessionStorage.getItem(key) || '{}');
        var rememberCounts = function(savedsearch) {
            rememberedCounts[rememberCountsId(savedsearch)] = savedsearch._count;
            sessionStorage.setItem(key, JSON.stringify(rememberedCounts));
        };
        var rememberCountsId = function(savedsearch) {
            var modified = savedsearch.modified.match(
                /\d\d:\d\d:\d\d/
            )[0];
            return savedsearch.id + modified;
        };

        $scope.deleteSavedSearch = function(savedsearch) {
            $http.post(deleteURL.replace('0', savedsearch.id))
            .success(function() {
                $scope.savedsearches.splice(
                    $scope.savedsearches.indexOf(savedsearch),
                    1
                );
            })
            .error(console.error.bind(console));
        };

        var fetchCounts = function() {
            var working = false;
            $scope.savedsearches.forEach(function(savedsearch) {
                if (!working && savedsearch._count === undefined) {
                    working = true;
                    $http.get(sampleURL.replace('0', savedsearch.id))
                    .success(function(result) {
                        savedsearch._count = result.events;
                        rememberCounts(savedsearch);
                        fetchCounts();
                    })
                    .error(function() {
                        console.error.apply(console, arguments);
                        $timeout(function() {
                            fetchCounts();
                        }, 2000);
                    });
                }
            });
        };

        $scope.urls = {};
        $scope.url = function(viewname, item) {
            if (!$scope.urls[viewname]) {
                console.warn('No known URL view by that name', viewname);
            }
            return $scope.urls[viewname].replace('0', item);
        };

        $http.get(dataURL)
        .success(function(response) {
            $scope.failed = false;
            $scope.savedsearches = response.savedsearches;
            $scope.urls = response.urls;
            $scope.savedsearches.forEach(function(savedsearch) {
                var count = rememberedCounts[rememberCountsId(savedsearch)];
                if (count !== undefined) {
                    savedsearch._count = count;
                }
            });
            fetchCounts();
        })
        .error(function() {
            $scope.failed = true;
        })
        .finally(function() {
            $scope.loading = false;
        });


}])

;

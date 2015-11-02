angular.module('new', [
    'ngSanitize',
    'ngAnimate',
    'angularMoment',
    'ui.router',
    'new.controllers',
    'new.services'
])

.config(['$urlMatcherFactoryProvider', function ($urlMatcherFactoryProvider) {
  $urlMatcherFactoryProvider.strictMode(false);
}])

// .run(['$rootScope', function($rootScope) {
//     $rootScope.$on('$stateChangeStart',function(event, toState, toParams, fromState, fromParams){
//       console.log('$stateChangeStart to '+toState.to+'- fired when the transition begins. toState,toParams : \n',toState, toParams);
//     });
//     $rootScope.$on('$stateChangeError',function(event, toState, toParams, fromState, fromParams, error){
//       console.log('$stateChangeError - fired when an error occurs during transition.');
//       console.log(arguments);
//     });
//     $rootScope.$on('$stateChangeSuccess',function(event, toState, toParams, fromState, fromParams){
//       console.log('$stateChangeSuccess to '+toState.name+' - fired once the state transition is complete.');
//     });
//     // $rootScope.$on('$viewContentLoading',function(event, viewConfig){
//     //   // runs on individual scopes, so putting it in "run" doesn't work.
//     //   console.log('$viewContentLoading - view begins loading - dom not rendered',viewConfig);
//     // });
//     $rootScope.$on('$viewContentLoaded',function(event){
//       console.log('$viewContentLoaded - fired after dom rendered',event);
//     });
//     $rootScope.$on('$stateNotFound',function(event, unfoundState, fromState, fromParams){
//       console.log('$stateNotFound '+unfoundState.to+'  - fired when a state cannot be found by its name.');
//       console.log(unfoundState, fromState, fromParams);
//     });
// }])

.config(['$stateProvider', '$locationProvider', '$urlRouterProvider',
    function ($stateProvider, $locationProvider, $urlRouterProvider) {
    $locationProvider.html5Mode(true);

    $urlRouterProvider.otherwise('/problem/notfound');

    $stateProvider
    .state('start', {
        url: '/',
        templateUrl: 'start.html',
        controller: 'StartController'
    })
    .state('problem', {
        url: '/problem',
        // Important that parent has a template with ui-view which the
        // child states can replace
        template: '<ui-view/>'
    })
    .state('problem.notfound', {
        url: '/notfound',
        // parent: 'problem',
        templateUrl: 'problem.html',
        controller: 'NotFoundController'
    })
    .state('problem.notyours', {
        url: '/notyours',
        templateUrl: 'problem.html',
        controller: 'NotYoursController'
    })
    .state('startUpload', {
        url: '/upload',
        templateUrl: 'upload.html',
        controller: 'UploadController'
    })
    .state('recordVideo', {
        url: '/record',
        templateUrl: 'record.html',
        controller: 'RecordController'
    })
    .state('youtubeVideo', {
        url: '/youtube',
        templateUrl: 'youtube.html',
        controller: 'YouTubeController'
    })
    .state('preemptiveDetails', {
        url: '/details',
        templateUrl: 'details.html',
        controller: 'DetailsController'
    })
    .state('picture', {
        url: '/:id/picture',
        templateUrl: 'picture.html',
        controller: 'PictureController'
    })
    .state('details', {
        url: '/:id/details',
        templateUrl: 'details.html',
        controller: 'DetailsController'
    })
    .state('summary', {
        url: '/:id/summary',
        templateUrl: 'summary.html',
        controller: 'SummaryController'
    })
    .state('published', {
        url: '/:id/published',
        templateUrl: 'published.html',
        controller: 'PublishedController'
    })

    ;

}])

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

;

$(function() {
    var clientID = $('meta[name="auth0-client-id"]').attr('content');
    var domain = $('meta[name="auth0-domain"]').attr('content');
    var callbackURL = $('meta[name="auth0-callback-url"]').attr('content');

    var lock = new Auth0LockPasswordless(clientID, domain);

    $('p.login-lock a').on('click', function(event) {
        event.preventDefault();
        var options = {
            callbackURL: callbackURL,
            connections: ['google-oauth2', 'github'],
        };
        lock.socialOrEmailcode(options);
    });

});

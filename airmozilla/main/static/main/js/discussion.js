$(function() {
    'use strict';

    var submitting = false;
    function _preSave($form) {
        $('.has-error .error-text', $form).remove();
        $('.has-error', $form).removeClass('has-error');
        $('.saving', $form).show();
        submitting = true;
    }

    $('form.event-discussion').submit(function() {
        if (submitting) {
            console.warn('Accidental double-submit');
            return false;
        }
        _preSave($(this));
        return true;
    });

});

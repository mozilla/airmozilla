var queue = [];

function qNext() {
    var next = queue.shift();
    if (next)
      $.ajax(next).success(qNext);
}

function qAjax(options) {
    queue.push(options);
}


function reset_label($element) {
    $element
      .removeClass('label-success')
      .removeClass('label-important')
      .removeClass('label-warning')
      .removeClass('label-info')
      .removeClass('label-inverse')
      .text('Finding out');
}

$(function() {

    $('td .label').each(function() {
        var self = $(this);
        qAjax({
          url: '/manage/vidly/status/',
          data: {id: self.data('id')},
          success: function(response) {
              process_vidly_status_response(response, self);
          }
        });
    });
    qNext();

    $('button[name="refresh"]').click(function() {
        var row = $(this).parents('tr');
        var $label = $('.label', row);
        reset_label($label);
        $.ajax({
          url: '/manage/vidly/status/',
          data: {id: $label.data('id'), refresh: true},
          success: function(response) {
              process_vidly_status_response(response, $label);
          }
        });
        return false;
    });

    $('button[name="info"]').click(function() {
        var row = $(this).parents('tr');
        var $label = $('.label', row);
        $('form.resubmit').hide();
        $.ajax({
          url: '/manage/vidly/info/',
          data: {id: $label.data('id'), refresh: true},
          success: function(response) {
              if (response.ERRORS) {
                  $.each(response.ERRORS, function(i, error) {
                      alert('ERROR: ' + error);
                  });
                  return;
              }
              var table = $('.info table');
              $('tr', table).remove();
              $.each(response.fields, function(i, field) {
                  $('<tr>')
                    .append($('<th>').text(field.key))
                    .append($('<td>').append($('<code>').text(field.value)))
                    .appendTo(table);
              });
              $('.info').show();
          }
        });
        return false;
    });

    $('button[name="resubmit"]').click(function() {
        var row = $(this).parents('tr');
        var $label = $('.label', row);
        var csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]').val();
        $('.info').hide();
        $.ajax({
          url: '/manage/vidly/info/',
          data: {id: $label.data('id'), refresh: true, past_submission_info: true},
          success: function(response) {
              var $form = $('form.resubmit');
              $('input[name="id"]', $form).val($label.data('id'));
              if (response.past_submission) {
                  var past = response.past_submission;
                  if (past.url) {
                      $('input[name="url"]', $form).val(past.url);
                  }
                  if (past.email) {
                      $('input[name="email"]', $form).val(past.email);
                  }
                  if (past.hd) {
                      $('input[name="hd"]', $form).attr('checked', 'checked');
                  }
                  if (past.token_protection) {
                      $('input[name="token_protection"]', $form).attr('checked', 'checked');
                  }
                  $('.past-submission', $form).hide();
              } else {
                  $('.past-submission', $form).show();
              }
              $('form.resubmit').show();
          }
        });
        return false;
    });

    $('button.close-info').click(function() {
        $('.info').fadeOut(200);
        return false;
    });

    $('form.resubmit button.cancel').click(function(e) {
        e.preventDefault();
        $('form.resubmit').hide();
        return false;
    });
});

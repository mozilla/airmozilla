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
      .text('Finding out');
}

function process_response(response, $element) {
    if (response.success) {
        $element.text("Success").addClass('label-success');
    } else if (response.errored) {
        $element.text("Errored").addClass('label-important');
    } else {
        $element.text("Unknown").addClass('label-warning');
    }
}

$(function() {

    $('td .label').each(function() {
        var self = $(this);
        qAjax({
          url: '/manage/vidly/status/',
          data: {id: self.data('id')},
          success: function(response) {
              process_response(response, self);
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
              process_response(response, $label);
          }
        });
        return false;
    });

    $('button[name="info"]').click(function() {
        var row = $(this).parents('tr');
        var $label = $('.label', row);
        $.ajax({
          url: '/manage/vidly/info/',
          data: {id: $label.data('id'), refresh: true},
          success: function(response) {
              var table = $('.info table');
              $('tr', table).remove();
              console.log(response);
              $.each(response.fields, function(i, field) {
                  $('<tr>')
                    .append($('<th>').text(field.key))
                    .append($('<td>').append($('<code>').text(field.value)))
                    .appendTo(table);
                  console.log(table);
              });
              $('.info').show();
              //process_response(response, $label);
          }
        });
        return false;
    });

    $('button.close-info').click(function() {
        $('.info').fadeOut(200);
        return false;
    });
});

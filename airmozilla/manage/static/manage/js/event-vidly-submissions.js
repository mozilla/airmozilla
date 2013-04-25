$(function() {

    $('button[name="info"]').click(function() {
        var row = $(this).parents('tr');
        var id = $(this).val();
        $.ajax({
          url: location.href + 'submission/' + id + '/',
          data: {as_fields: true},
          success: function(response) {
              var table = $('div.info table');
              $('tr', table).remove();
              $.each(response.fields, function(i, field) {
                  $('<tr>')
                    .append($('<th>').text(field.key))
                    .append($('<td>').append($('<code>').text(field.value)))
                    .appendTo(table);
              });
              $('div.info').fadeIn(400);
          }
        });
        return false;
    });

    $('button.close-info').click(function() {
        $('.info').fadeOut(400);
        return false;
    });

});

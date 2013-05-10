
$(function() {

    $('button[name="run"]').click(function(e) {
        e.preventDefault();
        var parent = $(this).closest('tr');
        var data = {url: $('input[name="url"]', parent).val()};
        var url = location.href + 'run/';
        $.getJSON(url, data, function(response) {
            if (response.error) {
                $('.run-error', parent).text(response.error);
                $('input[name="result"]', parent).val('');
            } else {
                $('.run-error', parent).text('');
                $('input[name="result"]', parent).val(response.result);
            }
        });
    });

    $('button[name="remove-transform"]').click(function(e) {
        e.preventDefault();
        var parent = $(this).closest('tr');
        var matcher_parent = parent.parents('tr.matcher');
        var data = {};
        data.csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]').val();
        var url = location.href + matcher_parent.data('matcher-id') + '/' +
          parent.data('transform-id') + '/remove/';
        $.post(url, data, function(response) {
            parent.remove();
        });
    });

    $('button[name="save-transform"]').click(function(e) {
        e.preventDefault();
        var parent = $(this).closest('tr');
        var matcher_parent = parent.parents('tr.matcher');
        var find = $('input[name="find"]', parent);
        var replace_with = $('input[name="replace_with"]', parent);
        var data = {find: find.val(), replace_with: replace_with.val()};
        data.csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]').val();
        var url = location.href + matcher_parent.data('matcher-id') + '/' +
          parent.data('transform-id') + '/edit/';
        $.post(url, data, function(response) {
            alert("Saved");
        });
    });

    $('button[name="add-transform"]').click(function(e) {
        e.preventDefault();
        var parent = $(this).closest('tr');
        if (parent.length != 1) throw "not 1";
        var find = $('input[name="find"]', parent);
        var replace_with = $('input[name="replace_with"]', parent);
        if (!find.val()) {
            alert("No 'Replace' value");
            return;
        }
        if (!replace_with.val()) {
            alert("No 'With' value");
            return;
        }
        var matcher_parent = parent.parents('tr.matcher');
        var url = location.href + matcher_parent.data('matcher-id') + '/add/';
        var data = {find: find.val(), replace_with: replace_with.val()};
        data.csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]').val();
        $.post(url, data, function(response) {
            find.val('');
            replace_with.val('');
            var copy = parent.clone();
            $('input[name="find"]', copy).val(response.transform.find);
            $('input[name="replace_with"]', copy).val(response.transform.replace_with);
            var button = $('button', copy)
              .addClass('btn-danger')
              .attr('name', 'remove-transform')
              .html('<i class="icon-trash"></i> Remove');
            $('i', button)
              .removeClass('icon-plus')
              .addClass('icon-trash');

            var tbody = $('tbody', matcher_parent);
            copy.data('transform-id', response.transform.id);
            tbody.append(copy);

        });
    });


});

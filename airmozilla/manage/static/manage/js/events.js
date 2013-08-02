var Autocomplete = (function() {

    function fetcher(query, process) {
        var data = {q: query, max: 10};
        $.getJSON('/manage/events-autocomplete/', data, function(response) {
            process(response);
        });
    }

    function updater(item) {
        var form = $('form.form-search');
        $('#id_title').val(item);
        form.submit();
        return item;
    }

    function sorter(items) {
        // because the items are already sorted server-side
        // we just keep the list as is
        return items;
    }

    return {
       setup: function() {
           $('#id_title').typeahead({
               source: fetcher,
               minLength: 2,
               items: 10,
               sorter: sorter,
               updater: updater
           });
       }
    };
})();


$(function() {
    Autocomplete.setup();
    $('button.cancel').click(function() {
        location.href = location.pathname;
    });
});

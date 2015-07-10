$(document).ready(function () {
  PopcornEditor.listen(PopcornEditor.events.loaded, function () {
    $.get($('#editor').data('url'), {
        slug: $('#editor').data('slug')
    })
    .done(function (response) {
      if(response.data) {
        PopcornEditor.loadInfo(response.data);
      } else {
        PopcornEditor.loadInfo(PopcornEditor.createTemplate(response.metadata));
      }
    })
    .fail(function() {
      console.warn("Unable to load popcorn data :(");
      console.error.apply(console, arguments);
    });
  })
  // Initialize the editor with the div id and path to Popcorn Editor.
  PopcornEditor.init('editor', '/static/popcorn/PopcornEditor/editor.html');
});

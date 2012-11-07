$(function() {

  var title = null;
  if ($('h1:visible').size()) {
    if ($('h1:visible').size() == 1) {
      title = $('h1:visible').text();
    }
  } else if ($('h2:visible').size()) {
    if ($('h2:visible').size() == 1) {
      title = $('h2:visible').text();
    }
  }
  if (title) {
    document.title = title + ' - ' + document.title;
  }


});

/*global $:true */


$(function() {
  'use strict';

  var $counter = $('.char-counter');
  $('textarea').on('keyup', function() {
    var $element = $(this);
    var len = $.trim($element.val()).length;
    var max = $element.data('maxlength');
    if ((max - len) < 0) {
      $counter.addClass('over');
    } else {
      $counter.removeClass('over');
    }
    $counter.text(max - len);
  }).trigger('keyup');

  $('button[name="cancel"]').click(function() {
    if ($('input[name="event_edit_url"]').length) {
      location.href = $('input[name="event_edit_url"]').val();
      return false;
    } else {
      return true;
    }
  });

  $('a.include-event-tags').click(function() {
    var tags = $(this).data('tags');
    // first we need to deduce if they're already there
    var count = 0;
    var $textarea = $('textarea');
    var text = $textarea.val();
    $.each(tags, function(i, tag) {
      var searchfor = '#' + tag.replace(/ /g, '');
      if (text.match(searchfor)) {
        count++;
      }
    });
    if (count) {
      // remove them all
      $.each(tags, function(i, tag) {
        var searchfor = '#' + tag.replace(/ /g, '');
        text = text.replace(searchfor, '');
      });
    } else {
      // add them all
      text = $.trim(text);
      $.each(tags, function(i, tag) {
        text += ' #' + tag.replace(/ /g, '');
      });
    }
    $textarea.val($.trim(text));
    $textarea.trigger('keyup');
    return false;
  });

  // Datetime picker (jQuery UI)
  $('#id_send_date').datetimepicker({
    stepHour: 1,
    stepMinute: 15,
    dateFormat: 'yy-mm-dd',
    timeFormat: 'HH:mm'
  });


});

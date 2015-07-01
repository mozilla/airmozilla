$(document).ready(function() {

var URL = window.location.pathname + 'related-content'

    $.get(URL, function(response) {
    // Action to be added if necessary
        $.post(function(response) {
        // Action to be added if necessary
           $('.entry-title').html(data);
       }
      });
   }
  });
  
      
});

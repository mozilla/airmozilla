$(function() {
    $('p.help-block').each(function() {
        var $controls = $(this).parents('.form-group');
        if ($('input[type="checkbox"]', $controls).length) {
            return;
        }
        $(this).hide();
        $('textarea,input', $controls)
          .attr('title', $(this).text())
          .addClass('tooltip');
    });
    $('.tooltip').tooltipster({
       position: 'top'
    });

});

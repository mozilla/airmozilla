$(function() {
    $('p.help-block').each(function() {
        $(this).hide();
        var $controls = $(this).parents('.control-group');
        $('textarea,input', $controls)
          .attr('title', $(this).text())
          .addClass('tooltip');
    });
    $('.tooltip').tooltipster({
       position: 'top'
    });
});

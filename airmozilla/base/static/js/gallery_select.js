/**
 * Selecting a picture from a gallery.
 */
$(function() {
    "use strict";
    // Intial title setting and selection of a picture
    var selected_pic_id_field = $("#id_picture");
    $('.picture_gallery .picture').each(function() {
        if(selected_pic_id_field.val() === $(this).attr('data-picture-id')) {
            selected_pic_id_field.val($(this).attr('data-picture-id'));
            $(this).addClass('selected');
            $(this).attr('title', $(this).data('title-when-selected'));
        } else {
            $(this).attr('title', $(this).data('title-when-not-selected'));
        }
    });
    $('.picture_gallery').on('click', '.picture', function() {
        var selected_pic_id_field = $(this).siblings("#id_picture");
        $('.picture.selected')
            .removeClass('selected')
            .attr('title', $(this).data('title-when-not-selected'));
        // If the clicked picture is the already selected picture.
        if(selected_pic_id_field.val() === $(this).attr('data-picture-id')) {
            selected_pic_id_field.val('');
        } else {
            selected_pic_id_field.val($(this).attr('data-picture-id'));
            $(this).addClass('selected');
            $(this).attr('title', $(this).data('title-when-selected'));
        }
    });
    $('.picture_gallery').on('scroll', function() {
        $(this).addClass('larger').off('scroll');
    });
});

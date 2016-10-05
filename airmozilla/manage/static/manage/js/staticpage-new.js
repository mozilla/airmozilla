$(function() {
    'use strict';

    var defaults = {
        javascript: {
            '#id_url': '/change-me.js',
            '#id_title': "Won't matter but good for taking notes",
            '#id_content': "console.log('Hi! I\\'m some JavaScript code');",
            '#id_template_name': 'staticpages/blank.html',
            '#id_headers': 'Content-Type: application/javascript',
        },
        json: {
            '#id_url': '/change-me.json',
            '#id_title': "Won't matter but good for taking notes",
            '#id_content': JSON.stringify({foo: ['one', 'two']}, undefined, 4),
            '#id_template_name': 'staticpages/blank.html',
            '#id_headers': 'Content-Type: application/json',
        },
        xml: {
            '#id_url': '/change-me.xml',
            '#id_title': "Won't matter but good for taking notes",
            '#id_content': "<header>\n<content>\nHi!\n</content>\n</header>",
            '#id_template_name': 'staticpages/blank.html',
            '#id_headers': 'Content-Type: application/xml',
        },
        html: {
            '#id_url': '/some/page',
            '#id_title': 'Sample Title',
            '#id_content': '<p>Here goes the <i>HTML</i></p>',
            '#id_template_name': '',
            '#id_headers': '',
        },
    };

    $('.alert button').on('click', function(event) {
        event.preventDefault();
        $.each(defaults[this.name], function(selector, text) {
            $(selector).val(text);
        });
    });

});

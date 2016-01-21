#
# CSS
#

PIPELINE_CSS = {
    'manage_base': {
        'source_filenames': (
            'manage/css/bootstrap.min.css',
            'manage/css/manage.css',
        ),
        'output_filename': 'css/manage-base.min.css',
    },
    'calendar': {
        'source_filenames': (
            'main/fullcalendar/fullcalendar.min.css',
            'main/css/calendar.css',
        ),
        'output_filename': 'css/calendar.min.css',
    },
    'calendar_print': {
        'source_filenames': (
            'main/fullcalendar/fullcalendar.print.css',
        ),
        'output_filename': 'css/calendar-print.min.css',
        'extra_context': {
            'media': 'print'
        }
    },
    'discussion': {
        'source_filenames': (
            'main/css/discussion.css',
        ),
        'output_filename': 'css/discussion.min.css',
    },
    'edit_chapters': {
        'source_filenames': (
            'main/css/edit-chapters.css',
        ),
        'output_filename': 'css/edit-chapters.min.css',
    },
    'gallery_select': {
        'source_filenames': (
            'css/gallery_select.css',
        ),
        'output_filename': 'css/gallery-select.min.css',
    },
    'select2': {
        'source_filenames': (
            'select2/select2.min.css',
        ),
        'output_filename': 'css/select2.min.css',
    },
    'main_event_edit': {
        'source_filenames': (
            'main/css/edit.css',
        ),
        'output_filename': 'css/main-event-edit.min.css',
    },
    'event': {
        'source_filenames': (
            'comments/css/comments.css',
            'surveys/css/survey.css',
            'main/css/event.css',
        ),
        'output_filename': 'css/event.min.css',
    },
    'main_base': {
        'source_filenames': (
            'main/css/onemozilla.css',
            'starred/css/star_event.css',
            'main/css/fonts.css',
            'main/css/main.css',
            'main/css/tabzilla.css',
            'main/autocompeter/autocompeter.min.css',
            'main/css/autocompeter.css',
            'browserid/persona-buttons.css',
        ),
        'output_filename': 'css/main-base.min.css',
    },
    'too_few_tags': {
        'source_filenames': (
            'main/css/too-few-tags.css',
        ),
        'output_filename': 'css/too-few-tags.min.css',
    },
    'metricsgraphics': {
        'source_filenames': (
            'manage/metricsgraphics/metricsgraphics.css',
        ),
        'output_filename': 'css/metricsgraphics.min.css',
    },
    'dashboard': {
        'source_filenames': (
            'manage/css/dashboard.css',
        ),
        'output_filename': 'css/dashboard.min.css',
    },
    'event_edit': {
        'source_filenames': (
            'manage/css/event-edit.css',
        ),
        'output_filename': 'css/event-edit.min.css',
    },
    'eventmanager': {
        'source_filenames': (
            'manage/css/datepicker.css',
            'manage/css/events.css',
        ),
        'output_filename': 'css/eventmanager.min.css',
    },
    'select2_bootstrap': {
        'source_filenames': (
            'select2/select2-bootstrap.css',
        ),
        'output_filename': 'css/select2-bootstrap.min.css',
    },
    'survey': {
        'source_filenames': (
            'manage/css/survey.css',
        ),
        'output_filename': 'css/survey.min.css',
    },
    'picture_gallery': {
        'source_filenames': (
            'manage/css/picture-gallery.css',
        ),
        'output_filename': 'css/picture-gallery.min.css',
    },
    'new': {
        'source_filenames': (
            'new/jquery-textcomplete/jquery.textcomplete.css',
            'new/css/new.css',
        ),
        'output_filename': 'css/new.min.css',
    },
    'popcorn_editor': {
        'source_filenames': (
            'popcorn/css/editor.css',
        ),
        'output_filename': 'css/popcorn-editor.min.css',
    },
    'suggest_start': {
        'source_filenames': (
            'suggest/css/start.css',
        ),
        'output_filename': 'css/suggest-start.min.css',
    },
    'suggest_base': {
        'source_filenames': (
            'tooltipster/css/tooltipster.css',
            'suggest/css/suggest.css',
        ),
        'output_filename': 'css/suggest-base.min.css',
    },
    'upload': {
        'source_filenames': (
            'uploads/css/upload.css',
        ),
        'output_filename': 'css/upload.min.css',
    },
    'event_upload': {
        'source_filenames': (
            'manage/css/event-upload.css',
        ),
        'output_filename': 'css/event-upload.min.css',
    },
    'popcorn_status': {
        'source_filenames': (
            'popcorn/css/status.css',
        ),
        'output_filename': 'css/popcorn-status.min.css',
    },
    'search': {
        'source_filenames': (
            'search/css/search.css',
        ),
        'output_filename': 'css/search.min.css',
    },
    'suggest_summary': {
        'source_filenames': (
            'suggest/css/summary.css',
        ),
        'output_filename': 'css/suggest-summary.min.css',
    },
    'select2_overrides': {
        'source_filenames': (
            'main/css/select2-overrides.css',
        ),
        'output_filename': 'css/select2-overrides.min.css',
    },
    'savesearch': {
        'source_filenames': (
            'search/css/savesearch.css',
        ),
        'output_filename': 'css/savesearch.min.css',
    },
    'savedsearches': {
        'source_filenames': (
            'search/css/savedsearches.css',
        ),
        'output_filename': 'css/savedsearches.min.css',
    },
}

#
# JavaScript
#

PIPELINE_JS = {
    'base': {
        'source_filenames': (
            'js/libs/jquery-1.11.1.min.js',
            'js/libs/jquery.timeago.js',
            'js/libs/moment.js',
            'js/base.js',
        ),
        'output_filename': 'js/base.min.js',
    },
    'manage_base': {
        'source_filenames': (
            'manage/js/manage.js',
            'manage/js/confirm-delete.js',
            'manage/js/form-errors.js',
        ),
        'output_filename': 'js/manage-base.min.js',
    },
    'calendar': {
        'source_filenames': (
            'main/fullcalendar/fullcalendar.min.js',
            'main/jstz/jstz-1.0.4.min.js',
            'main/js/calendar.js',
        ),
        'output_filename': 'js/calendar.min.js',
    },
    'discussion': {
        'source_filenames': (
            'main/js/discussion.js',
        ),
        'output_filename': 'js/discussion.min.js',
    },
    'edit_chapters': {
        'source_filenames': (
            'main/js/edit-chapters.js',
        ),
        'output_filename': 'js/edit-chapters.min.js',
    },
    'gallery_select': {
        'source_filenames': (
            'js/gallery_select.js',
        ),
        'output_filename': 'js/gallery-select.min.js',
    },
    'main_event_edit': {
        'source_filenames': (
            'main/js/edit.js',
        ),
        'output_filename': 'js/main-event-edit.min.js',
    },
    'event_video': {
        'source_filenames': (
            'main/js/event_video.js',
        ),
        'output_filename': 'js/event-video.min.js',
    },
    'event': {
        'source_filenames': (
            'main/js/embed.js',
            'main/js/download.js',
            'main/js/tearout.js',
            'main/js/playbackrate.js',
            'main/js/startat.js',
            'main/js/eventstatus.js',
            'main/js/chapters.js',
            'comments/js/comments.js',
            'surveys/js/survey.js',
            'main/js/livehits.js',
            'main/js/related-content.js',
            'main/js/share.js',
        ),
        'output_filename': 'js/event.min.js',
    },
    'browserid': {
        'source_filenames': (
            'js/libs/include.js',
            'browserid/api.js',
            'browserid/browserid.js',
        ),
        'output_filename': 'js/browserid.min.js',
    },
    'autocompeter': {
        'source_filenames': (
            'main/js/autocompeter.js',
        ),
        'output_filename': 'js/autocompeter.min.js',
    },
    'main_base': {
        'source_filenames': (
            'js/libs/layzr.min.js',
            'js/layzr-images.js',
            'starred/js/star_event.js',
            'main/js/nav.js',
            'main/js/thumbnailhover.js',
        ),
        'output_filename': 'js/main-base.min.js',
    },
    'too_few_tags': {
        'source_filenames': (
            'main/js/too-few-tags.js',
        ),
        'output_filename': 'js/too-few-tags.min.js',
    },
    'manage_autocompeter': {
        'source_filenames': (
            'manage/js/autocompeter.js',
        ),
        'output_filename': 'js/manage-autocompeter.min.js',
    },
    'channel_html_edit': {
        'source_filenames': (
            'manage/js/channel-html-edit.js',
        ),
        'output_filename': 'js/channel-html-edit.min.js',
    },
    'cronlogger': {
        'source_filenames': (
            'manage/js/cronlogger.js',
        ),
        'output_filename': 'js/cronlogger.min.js',
    },
    'dashboard_graphs': {
        'source_filenames': (
            'manage/metricsgraphics/metricsgraphics.js',
            'manage/js/dashboard_graphs.js',
        ),
        'output_filename': 'js/dashboard-graphs.min.js',
    },
    'dashboard': {
        'source_filenames': (
            'manage/js/dashboard.js',
        ),
        'output_filename': 'js/dashboard.min.js',
    },
    'durations': {
        'source_filenames': (
            'manage/js/durations.js',
        ),
        'output_filename': 'js/durations.min.js',
    },
    'edit_event_tweet': {
        'source_filenames': (
            'manage/js/jquery-ui-1.10.1.custom.min.js',
            'manage/js/event-tweets.js',
        ),
        'output_filename': 'js/edit-event-tweet.min.js',
    },
    'event_archive': {
        'source_filenames': (
            'manage/js/event-archive.js',
        ),
        'output_filename': 'js/event-archive.min.js',
    },
    'event_assignment': {
        'source_filenames': (
            'manage/js/event-assignment.js',
        ),
        'output_filename': 'js/event-assignment.min.js',
    },
    'discussion_configuration': {
        'source_filenames': (
            'manage/js/discussion-configuration.js',
        ),
        'output_filename': 'js/discussion-configuration.min.js',
    },
    'event_edit': {
        'source_filenames': (
            'manage/js/event-edit.js',
        ),
        'output_filename': 'js/event-edit.min.js',
    },
    'jquery_ui_timepicker': {
        'source_filenames': (
            'manage/js/jquery-ui-timepicker-addon.js',
        ),
        'output_filename': 'js/jquery-ui-timepicker.min.js',
    },
    'event_request': {
        'source_filenames': (
            'manage/js/event-request.js',
        ),
        'output_filename': 'js/event-request.min.js',
    },
    'uploads': {
        'source_filenames': (
            'uploads/js/upload.js',
        ),
        'output_filename': 'js/uploads.min.js',
    },
    'manage_event_upload': {
        'source_filenames': (
            'manage/js/event-upload.js',
        ),
        'output_filename': 'js/manage-event-upload.min.js',
    },
    'event_vidly_submissions': {
        'source_filenames': (
            'manage/js/event-vidly-submissions.js',
        ),
        'output_filename': 'js/event-vidly-submissions.min.js',
    },
    'eventmanager': {
        'source_filenames': (
            'manage/js/bootstrap-datepicker.js',
            'manage/js/events.js',
            'manage/js/eventmanager.js',
        ),
        'output_filename': 'js/eventmanager.min.js',
    },
    'locations': {
        'source_filenames': (
            'manage/js/locations.js',
        ),
        'output_filename': 'js/locations.min.js',
    },
    'survey_edit': {
        'source_filenames': (
            'manage/js/survey-edit.js',
        ),
        'output_filename': 'js/survey-edit.min.js',
    },
    'user_edit': {
        'source_filenames': (
            'manage/js/user-edit.js',
        ),
        'output_filename': 'js/user-edit.min.js',
    },
    'picture_add': {
        'source_filenames': (
            'manage/js/picture-add.js',
        ),
        'output_filename': 'js/picture-add.min.js',
    },
    'picture_gallery': {
        'source_filenames': (
            'manage/js/picturegallery.js',
        ),
        'output_filename': 'js/picture-gallery.min.js',
    },
    'related_content_testing': {
        'source_filenames': (
            'manage/js/related-content-testing.js',
        ),
        'output_filename': 'js/related-content-testing.min.js',
    },
    'staticpage_edit': {
        'source_filenames': (
            'manage/js/staticpage-edit.js',
        ),
        'output_filename': 'js/staticpage-edit.min.js',
    },
    'suggestions': {
        'source_filenames': (
            'manage/js/jquery-ui-1.10.1.highlight.min.js',
            'manage/js/suggestions.js',
        ),
        'output_filename': 'js/suggestions.min.js',
    },
    'tagmanager': {
        'source_filenames': (
            'manage/js/tagmanager.js',
        ),
        'output_filename': 'js/tagmanager.min.js',
    },
    'tweetmanager': {
        'source_filenames': (
            'manage/js/tweetmanager.js',
        ),
        'output_filename': 'js/tweetmanager.min.js',
    },
    'url_transforms': {
        'source_filenames': (
            'manage/js/url-transforms.js',
        ),
        'output_filename': 'js/url-transforms.min.js',
    },
    'usermanager': {
        'source_filenames': (
            'manage/js/usermanager.js',
        ),
        'output_filename': 'js/usermanager.min.js',
    },
    'vidly_media_timings': {
        'source_filenames': (
            'manage/js/vidly-media-timings.js',
        ),
        'output_filename': 'js/vidly-media-timings.min.js',
    },
    'vidly_media': {
        'source_filenames': (
            'manage/js/vidly-media.js',
        ),
        'output_filename': 'js/vidly-media.min.js',
    },
    'new_vendor': {
        'source_filenames': (
            'angular/angular.min.js',
            'angular/angular-sanitize.min.js',
            'angular/angular-animate.min.js',
            'angular/angular-ui-router.min.js',
            'angular/angular-moment.min.js',
        ),
        'output_filename': 'js/new-vendor.min.js',
    },
    's3upload': {
        'source_filenames': (
            'uploads/js/s3upload.js',
        ),
        'output_filename': 'js/s3upload.min.js',
    },
    'new': {
        'source_filenames': (
            'new/js/app.js',
            'new/js/services.js',
            'new/js/controllers.js',
        ),
        'output_filename': 'js/new.min.js',
    },
    'popcorn_editor': {
        'source_filenames': (
            'popcorn/js/editor.js',
        ),
        'output_filename': 'js/popcorn-editor.min.js',
    },
    'suggest_details': {
        'source_filenames': (
            'suggest/js/details.js',
        ),
        'output_filename': 'js/suggest-details.min.js',
    },
    'suggest_discussion': {
        'source_filenames': (
            'suggest/js/discussion.js',
        ),
        'output_filename': 'js/suggest-discussion.min.js',
    },
    'suggest_start': {
        'source_filenames': (
            'suggest/js/start.js',
        ),
        'output_filename': 'js/suggest-start.min.js',
    },
    'suggest_base': {
        'source_filenames': (
            'tooltipster/js/jquery.tooltipster.min.js',
            'suggest/js/suggest.js',
        ),
        'output_filename': 'js/suggest-base.min.js',
    },
    'savesearch': {
        'source_filenames': (
            'search/js/savesearch.js',
        ),
        'output_filename': 'js/savesearch.min.js',
    },
    'savedsearches': {
        'source_filenames': (
            'search/js/savedsearches.js',
        ),
        'output_filename': 'js/savedsearches.min.js',
    },
}

# This is sanity checks, primarily for developers. It checks that
# you haven't haven't accidentally make a string a tuple with an
# excess comma, no underscores in the bundle name and that the
# bundle file extension is either .js or .css.
# We also check, but only warn, if a file is re-used in a different bundle.
# That's because you might want to consider not including that file in the
# bundle and instead break it out so it can be re-used on its own.
_used = {}
for config in PIPELINE_JS, PIPELINE_CSS:  # NOQA
    _trouble = set()
    for k, v in config.items():
        assert isinstance(k, basestring), k
        out = v['output_filename']
        assert isinstance(v['source_filenames'], tuple), v
        assert isinstance(out, basestring), v
        assert '_' not in out
        assert out.endswith('.min.css') or out.endswith('.min.js')
        for asset_file in v['source_filenames']:
            if asset_file in _used:
                print '{:<52} in {:<20} already in {}'.format(
                    asset_file,
                    k,
                    _used[asset_file]
                )
                _trouble.add(asset_file)
            _used[asset_file] = k

    for asset_file in _trouble:
        print "REPEATED", asset_file
        found_in = []
        sets = []
        for k, v in config.items():
            if asset_file in v['source_filenames']:
                found_in.append(k)
                sets.append(set(list(v['source_filenames'])))
        print "FOUND IN", found_in
        print "ALWAYS TOGETHER WITH", set.intersection(*sets)
        print
        break

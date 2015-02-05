$(function() {
    var container = $('#calendar');
    var startsOnMonday = $('#startsOnMonday');
    var storage = localStorage.getItem('startsOnMonday');
    if (storage === null) {
        // this is a hack to try to determine if week starts on Sunday or Monday
        // right now if user is in America's TZ the week would start on Sunday
        // if user is in another TZ It would start on Monday
        var tz = jstz.determine().name();
        if (!tz.match('^America/')) {
            startsOnMonday.prop('checked', true);
        }
    } else {
        if (storage == 1) {
            startsOnMonday.prop('checked', true);
        }
    }
    var initCalendar = function() {
        container.fullCalendar({
            events: {
                url: container.data('events-url'),
                cache: true
            },
            timezone: 'local',
            weekends: true,
            firstDay: startsOnMonday.prop('checked')? 1 : 0,
            allDaySlot: false,
            defaultTimedEventDuration: '01:00:00',
            timeFormat: 'h:mm a',
            header: {
                left: 'prev,next today',
                center: 'title',
                right: 'month,agendaWeek,agendaDay'
            }
        });
    };
    startsOnMonday.on('change', function(){
        localStorage.setItem('startsOnMonday', startsOnMonday.prop('checked')? 1 : 0);
        container.fullCalendar('destroy');
        initCalendar();
    });
    initCalendar();
});

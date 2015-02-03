$(function() {
    var weekends, firstDay = 0;
    var x = new Date();
    var currentTimeZoneOffsetInHours = x.getTimezoneOffset() / 60;
    if (currentTimeZoneOffsetInHours <= -7) {
        // sufficiently far east that some Friday events might actually
        // start on a Saturday
        weekends = true;
        firstDay = 1;  // far-east people prefer Monday
    } else {
        weekends = false;
    }
    var container = $('#calendar');
    container.fullCalendar({
        events: {
            url: container.data('events-url'),
            cache: true
        },
        timezone: 'local',
        weekends: weekends,
        firstDay: firstDay,
        allDaySlot: false,
        defaultTimedEventDuration: '01:00:00',
        timeFormat: 'h:mm a',
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        }
    });
});

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
        events: container.data('events-url'),
        cache: true,
        weekends: weekends,
        firstDay: firstDay,
        allDaySlot: false,
        defaultEventMinutes: 60,
        ignoreTimezone: false,
        timeFormat: {
            'agenda': 'H:mm',
            '': 'H:mm'
        },
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        }
    });
});

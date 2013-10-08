$(function() {
    var container = $('#calendar');
    container.fullCalendar({
        events: container.data('events-url'),
        cache: true,
        weekends: false, // will hide Saturdays and Sundays
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

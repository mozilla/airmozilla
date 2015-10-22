$(function() {
    $('.share').click(function(event) {
        event.preventDefault();
        window.open(this.href, 'share-popup', 'width=580,height=350');
    });
});

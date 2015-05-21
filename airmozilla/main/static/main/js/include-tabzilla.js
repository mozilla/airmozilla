$(function() {
    var link = document.createElement('link');
    link.rel = "stylesheet";
    link.href = "//mozorg.cdn.mozilla.net/media/css/tabzilla-min.css";
    document.head.appendChild(link);

    var script = document.createElement('script');
    script.src = "//mozorg.cdn.mozilla.net/en-US/tabzilla/tabzilla.js";
    document.head.appendChild(script);
});

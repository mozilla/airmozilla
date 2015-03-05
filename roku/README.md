Based on the Roku SDK Videoplayer sample app.


How to install in dev mode
--------------------------

First you need to figure out what your IP address is of the Roku
device. You can do that by going to the Settings -> Network and look
at your Wired or Wi-Fi and see what the IP address is.

Next you need to enable debug mode on your Roku device. You can do
that by pressing:

    Home 3x, Up 2x, Right, Left, Right, Left, Right

on the remote. There you'll be asked to pick password. Remember that.

Now, when you have the IP address:

    export ROKU_DEV_TARGET=XXX.XXX.XXX.XXX
    make install


How to debug
------------

Once you know the IP address you can simply connect to it with telnet:

    telnet XXX.XXX.XXX.XXX 8085

How to debug the XML feeds
--------------------------

In `source/categoryFeed.brs` the URL to the remove server is
hardcoded. This must be `air.mozilla.org` when deploying the app for
Roke App Store submission.

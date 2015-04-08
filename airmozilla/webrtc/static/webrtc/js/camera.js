/* Copied from https://github.com/mozilla/peekaboo/blob/master/peekaboo/sheet/static/sheet/js/photobooth.js */
var Camera = (function() {

  var video;
  var canvas;
  var context;
  var imageFilter;

  // Alias the vendor prefixed variants of getUserMedia so we can access them
  // via navigator.getUserMedia
  navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia || navigator.msGetUserMedia;

  // Alias the vendor prefixed variants of the URL object so that we can access them
  // via window.URL
  window.URL = window.URL || window.webkitURL || window.mozURL || window.msURL;

  // Alias the vendor prefixed variants of requestAnimationFrame so that we can access
  // them via window.requestAnimationFrame fallback to setTimeout at 60hz if not supported.
  window.requestAnimationFrame = (function() {
    return window.requestAnimationFrame  ||
      window.webkitRequestAnimationFrame ||
      window.mozRequestAnimationFrame    ||
      window.oRequestAnimationFrame      ||
      window.msRequestAnimationFrame     ||
      function (callback) {
        window.setTimeout(callback, 1000 / 60);
      };
  })();

  function showStatus(s) {
    console.log('STATUS:', s);
    //document.querySelector("#status").innerHTML = s;
  }

  // This function will be called if a webcam is available and the user has
  // granted access for the web application to use it.
  function successCallback(stream, width) {
    // Firefox has a special property that you can use to associate the stream with the
    // video object.  Other browsers require you to use createObjectURL.
    if (video.mozSrcObject !== undefined) {
      video.mozSrcObject = stream;
    }
    else {
      video.src = (window.URL && window.URL.createObjectURL(stream)) || stream;
    }
    video.play();

    // Show the DOM elements that contain the rest of the UI
    //document.querySelector("#videodivs").style.display = "inline";
    showStatus("You should be seeing video from your camera.");

    console.log(video.height, video.videoHeight);
    var height = video.height / (video.width / width);
    console.log('width/height', width, '/', height);
    if (width && height) {
        video.setAttribute('width', width);
        video.setAttribute('height', height);
        canvas.setAttribute('width', width);
        canvas.setAttribute('height', height);
    }

    // capture the first frame of video and start the animation loop that
    // continuously update the video to the screen
    update();
  }

  // This function will be called if there is no webcam available or the user has
  // denied access for the web application to use it.
  function failureCallback() {
    $('.error span').text("No camera is available or you have denied access.");
    $('.error').hide().fadeIn(400);
  }

  // filter that brightens an image by adding a fixed value
  // to each color component
  // a javascript closure is used to parameterize the filter
  // with the delta value
  var brightness = function(delta) {
    return function (pixels, args) {
      var d = pixels.data;
      for (var i = 0; i < d.length; i += 4) {
        d[i] += delta;     // red
        d[i + 1] += delta; // green
        d[i + 2] += delta; // blue
      }
      return pixels;
    };
  };

  function processImage() {
    // console.log('processImage', canvas.width, canvas.height);
    if (canvas.width > 0 && canvas.height > 0) {
      if (imageFilter) {
        context.putImageData(imageFilter.apply(null,
         [context.getImageData(0, 0, canvas.width, canvas.height)]), 0, 0);
      }
    }
  }

  function processVideoFrame() {
    // We have to check for the video dimensions here.
    // Dimensions will be zero until they can be determined from
    // the stream.
    if (context && video.videoWidth > 0 && video.videoHeight > 0) {
      // Resize the canvas to match the current video dimensions
      if (canvas.width != video.videoWidth)
        canvas.width = video.videoWidth;
      if (canvas.height != video.videoHeight)
        canvas.height = video.videoHeight;

    //   console.log('processVideoFrame', canvas.width, canvas.height);
      // Copy the current video frame by drawing it onto the
      // canvas's context
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      processImage(canvas);
    }
  }

  var frameNumber = 0;
  var startTime = null;

  function update() {

    processVideoFrame();

    frameNumber++;
    // console.log(frameNumber);
    // console.log($('.debugging-fps'));
    if (startTime == null) {
      startTime = (new Date).getTime(); // in milliseconds
    }
    // Every 60 frames calculate our actual framerate and display it
    if (frameNumber >= 60) {
      var currentTime = (new Date).getTime();            // in milliseconds
      var deltaTime = (currentTime - startTime) / 1000.0;  // in seconds
      $('.debugging-fps').text(Math.floor(frameNumber/deltaTime) + " fps");
      startTime = currentTime;
      frameNumber = 0;
    }
    requestAnimationFrame(update);
  }

  return {
      setup: function(width, callback) {
       callback = callback || null;

       imageFilter = null;
       //setFilter(null);

       // Get the DOM object that matches the first video tag on the page
       video = document.querySelector('video');
       console.log('video size:', video.width, video.height);

       canvas = document.querySelector("canvas");
       console.log('canvas size:', canvas.width, canvas.height);
       context = canvas.getContext("2d");

       showStatus("Waiting for you to grant access to the camera...");

    //    video.addEventListener('canplay', function(e) {
    //        console.log(video.height, video.videoHeight);
    //        var height = video.height / (video.width / width);
    //        console.log('width/height', width, '/', height);
    //        video.setAttribute('width', width);
    //        video.setAttribute('height', height);
    //        canvas.setAttribute('width', width);
    //        canvas.setAttribute('height', height);
    //    }, false);

       // We can retrieve the video dimensions from the video object once we have
       // registered for and received the loadeddata event
       video.addEventListener('loadeddata', function(e) {
         console.log('loadeddata Video dimensions: ' + video.width + ' x ' + video.height);
       }, false);

       video.addEventListener('playing', function(e) {
         console.log('play Video dimensions: ' + video.width + ' x ' + video.height);
       }, false);

       if (!navigator.getUserMedia) {
         throw 'The navigator.getUserMedia() method not supported in this browser.';
       }

       // Ask the user for access to the camera
    //    navigator.getUserMedia({video: true}, successCallback, failureCallback);
    //    var conf = {
    //        video: {
    //            mandatory: {
    //             //    minWidth: 640,
    //                width: 640,
    //             //    minHeight: 360
    //                height: 360
    //            }
    //        }
    //    };
       conf = {
           video: { width: 1280, height: 720 }
       };
       navigator.getUserMedia(conf, function(stream) {
           successCallback(stream, width);
           callback();
       }, failureCallback);
    //    if (callback) callback();

     },
     getCanvas: function() {
       return canvas;
     },
     setFilter: function(f) {
       imageFilter = f;
     }
  };

})();

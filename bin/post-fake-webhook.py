#!/usr/bin/env python
"""

This is a rough tool to mock the event of Vid.ly firing the webhook.
When we, using the new uploader, send a URL to vid.ly for transcoding
we also give them a URL to ping (with the necessary XML) for when they're
done.
"""

import requests

BASE_URL = 'http://localhost:8000'

SAMPLE_MEDIA_RESULT_SUCCESS = """
<?xml version="1.0"?>
<Response>
    <Result>
        <Task>
            <UserID>1559</UserID>
            <MediaShortLink>{tag}</MediaShortLink>
            <SourceFile>{file_url}</SourceFile>
            <BatchID>661728</BatchID>
            <Status>Finished</Status>
            <Private>false</Private>
            <PrivateCDN>false</PrivateCDN>
            <Created>2015-02-23 15:58:27</Created>
            <Updated>2015-02-23 16:11:53</Updated>
            <UserEmail>airmozilla@mozilla.com</UserEmail>
            <MediaInfo>
                <bitrate>11136k</bitrate>
                <duration>9.84</duration>
                <audio_bitrate>64.0k</audio_bitrate>
                <audio_duration>9.838</audio_duration>
                <video_duration>9.84</video_duration>
                <video_codec>h264 (High)</video_codec>
                <size>1920x1080</size>
                <video_bitrate>11066k</video_bitrate>
                <audio_codec>aac</audio_codec>
                <audio_sample_rate>44100</audio_sample_rate>
                <audio_channels>1</audio_channels>
                <filesize>13697959</filesize>
                <frame_rate>29.98</frame_rate>
                <format>mpeg-4</format>
            </MediaInfo>
            <Formats>
            <Format>
                <FormatName>mp4</FormatName>
                <Location>http://cf.cdn.vid.ly/c9v8gx/mp4.mp4</Location>
                <FileSize>1063533</FileSize>
                <Status>Finished</Status>
                </Format>
            </Formats>
        </Task>
    </Result>
</Response>
"""


def run(webhook_url, file_url, tag):
    print (file_url, tag)
    url = BASE_URL + webhook_url
    xml_string = SAMPLE_MEDIA_RESULT_SUCCESS.format(
        file_url=file_url,
        tag=tag,
    )
    response = requests.post(
        url,
        data={'xml': xml_string.strip()}
    )
    print response


def main(args):
    try:
        webhook_url, file_url, tag = args
        run(webhook_url, file_url, tag)
    except ValueError:
        print (
            "USAGE: %s /new/vidly/webhook/ http://fileurl.com/file.mp4 "
            "abc123"
        ) % __file__
        return 1
    return 0

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    sys.exit(main(args))

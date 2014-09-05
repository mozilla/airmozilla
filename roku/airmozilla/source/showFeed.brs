' This Source Code Form is subject to the terms of the Mozilla Public
' License, v. 2.0. If a copy of the MPL was not distributed with this file,
' You can obtain one at http://mozilla.org/MPL/2.0/.

'******************************************************
'** Set up the show feed connection object
'** This feed provides the detailed list of shows for
'** each subcategory (categoryLeaf) in the category
'** category feed. Given a category leaf node for the
'** desired show list, we'll hit the url and get the
'** results.
'******************************************************

Function InitShowFeedConnection(category As Object) As Object

    if validateParam(category, "roAssociativeArray", "initShowFeedConnection") = false return invalid

    conn = CreateObject("roAssociativeArray")
    conn.UrlShowFeed  = category.feed

    conn.Timer = CreateObject("roTimespan")

    conn.LoadShowFeed    = load_show_feed
    conn.ParseShowFeed   = parse_show_feed
    conn.InitFeedItem    = init_show_feed_item

    print "created feed connection for " + conn.UrlShowFeed
    return conn

End Function


'******************************************************
'Initialize a new feed object
'******************************************************
Function newShowFeed() As Object

    o = CreateObject("roArray", 100, true)
    return o

End Function


'***********************************************************
' Initialize a ShowFeedItem. This sets the default values
' for everything.  The data in the actual feed is sometimes
' sparse, so these will be the default values unless they
' are overridden while parsing the actual game data
'***********************************************************
Function init_show_feed_item() As Object
    o = CreateObject("roAssociativeArray")

    o.ContentId        = ""
    o.Title            = ""
    o.ContentType      = ""
    o.ContentQuality   = ""
    o.Synopsis         = ""
    o.Genre            = ""
    o.Runtime          = ""
    o.StreamQualities  = CreateObject("roArray", 5, true)
    o.StreamBitrates   = CreateObject("roArray", 5, true)
    o.StreamUrls       = CreateObject("roArray", 5, true)

    return o
End Function


'*************************************************************
'** Grab and load a show detail feed. The url we are fetching
'** is specified as part of the category provided during
'** initialization. This feed provides a list of all shows
'** with details for the given category feed.
'*********************************************************
Function load_show_feed(conn As Object) As Dynamic

    if validateParam(conn, "roAssociativeArray", "load_show_feed") = false return invalid

    print "url: " + conn.UrlShowFeed

    if conn.UrlShowFeed.Left(5) = "https" then
        https = CreateObject("roUrlTransfer")
        https.SetUrl(conn.UrlShowFeed)
        https.SetCertificatesFile("common:/certs/ca-bundle.crt")
        https.AddHeader("X-Roku-Reserved-Dev-Id", "")
        https.InitClientCertificates()

        m.Timer.Mark()
        rsp = https.GetToString()

    else
        http = NewHttp(conn.UrlShowFeed)

        m.Timer.Mark()
        rsp = http.GetToStringWithRetry()

    endif

    print "Request Time: " + itostr(m.Timer.TotalMilliseconds())

    feed = newShowFeed()
    xml=CreateObject("roXMLElement")
    'if not xml.Parse(rsp) then  'the http way
    'if not xml.Parse(rsps) then  'the http way
    if not xml.Parse(rsp) then
        print "Can't parse feed"
        return feed
    endif

    if xml.GetName() <> "feed" then
        print "no feed tag found"
        return feed
    endif

    if islist(xml.GetBody()) = false then
        print "no feed body found"
        return feed
    endif

    m.Timer.Mark()
    m.ParseShowFeed(xml, feed)
    print "Show Feed Parse Took : " + itostr(m.Timer.TotalMilliseconds())

    return feed

End Function


'**************************************************************************
'**************************************************************************
Function parse_show_feed(xml As Object, feed As Object) As Void

    showCount = 0
    showList = xml.GetChildElements()

    for each curShow in showList

        'for now, don't process meta info about the feed size
        if curShow.GetName() = "resultLength" or curShow.GetName() = "endIndex" then
            goto skipitem
        endif

        item = init_show_feed_item()

        'fetch all values from the xml for the current show
        item.hdImg            = validstr(curShow@hdImg)
        item.sdImg            = validstr(curShow@sdImg)
        item.ContentId        = validstr(curShow.contentId.GetText())
        item.Title            = validstr(curShow.title.GetText())
        item.Description      = validstr(curShow.description.GetText())
        item.ContentType      = validstr(curShow.contentType.GetText())
        item.ContentQuality   = validstr(curShow.contentQuality.GetText())
        item.Synopsis         = validstr(curShow.synopsis.GetText())
        item.Genre            = validstr(curShow.genres.GetText())
        item.Runtime          = validstr(curShow.runtime.GetText())
        item.HDBifUrl         = validstr(curShow.hdBifUrl.GetText())
        item.SDBifUrl         = validstr(curShow.sdBifUrl.GetText())
        item.StreamFormat = validstr(curShow.streamFormat.GetText())
        if item.StreamFormat = "" then  'set default streamFormat to mp4 if doesn't exist in xml
            item.StreamFormat = "mp4"
        endif

        'map xml attributes into screen specific variables
        item.ShortDescriptionLine1 = item.Title
        item.ShortDescriptionLine2 = item.Description
        item.HDPosterUrl           = item.hdImg
        item.SDPosterUrl           = item.sdImg

        item.Length = strtoi(item.Runtime)
        item.Categories = CreateObject("roArray", 5, true)
        item.Categories.Push(item.Genre)
        item.Actors = CreateObject("roArray", 5, true)
        item.Actors.Push(item.Genre)
        item.Description = item.Synopsis

        'Set Default screen values for items not in feed
        item.HDBranded = false
        item.IsHD = false
        item.StarRating = "90"
        item.ContentType = "episode"

        'media may be at multiple bitrates, so parse an build arrays
        for idx = 0 to 4
            e = curShow.media[idx]
            if e  <> invalid then
                item.StreamBitrates.Push(strtoi(validstr(e.streamBitrate.GetText())))
                item.StreamQualities.Push(validstr(e.streamQuality.GetText()))
                item.StreamUrls.Push(validstr(e.streamUrl.GetText()))
            endif
        next idx

        showCount = showCount + 1
        feed.Push(item)

        skipitem:

    next

End Function

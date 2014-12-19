' This Source Code Form is subject to the terms of the Mozilla Public
' License, v. 2.0. If a copy of the MPL was not distributed with this file,
' You can obtain one at http://mozilla.org/MPL/2.0/.

'******************************************************
'** Perform any startup/initialization stuff prior to
'** initially showing the screen.
'******************************************************
Function preShowPosterScreen(breadA=invalid, breadB=invalid) As Object

    if validateParam(breadA, "roString", "preShowPosterScreen", true) = false return -1
    if validateParam(breadB, "roString", "preShowPosterScreen", true) = false return -1

    port=CreateObject("roMessagePort")
    screen = CreateObject("roPosterScreen")
    screen.SetMessagePort(port)
    if breadA<>invalid and breadB<>invalid then
        screen.SetBreadcrumbText(breadA, breadB)
    end if

    screen.SetListStyle("arced-16x9")
    return screen

End Function


'******************************************************
'** Display the home screen and wait for events from
'** the screen. The screen will show retreiving while
'** we fetch and parse the feeds for the game posters
'******************************************************
Function showPosterScreen(screen As Object, category As Object) As Integer

    if validateParam(screen, "roPosterScreen", "showPosterScreen") = false return -1
    if validateParam(category, "roAssociativeArray", "showPosterScreen") = false return -1

    m.curCategory = 0
    m.curShow     = 0
    temp=getcategorylist(category)


    if temp.count() > 1 then
    	screen.SetListNames(temp)
    	?temp.count();" categories"
    	else
    	?"only ";temp.count();" category"
    end if
    screen.SetContentList(getShowsForCategoryItem(category, m.curCategory))
    screen.Show()

    while true
        msg = wait(0, screen.GetMessagePort())
        if type(msg) = "roPosterScreenEvent" then
            print "showPosterScreen | msg = "; msg.GetMessage() " | index = "; msg.GetIndex()
            if msg.isListFocused() then
                m.curCategory = msg.GetIndex()
                m.curShow = 0
                screen.setcontentlist([])
                screen.SetFocusedListItem(m.curShow)
                screen.showmessage("Retrieving")
                screen.SetContentList(getShowsForCategoryItem(category, m.curCategory))
                screen.clearmessage()
		print "list focused | current category = "; m.curCategory
            else if msg.isListItemSelected() then
                m.curShow = msg.GetIndex()
                print "list item selected | current show = "; m.curShow
                m.curShow = displayShowDetailScreen(category, m.curShow)
                screen.SetFocusedListItem(m.curShow)
                print "list item updated  | new show = "; m.curShow
            else if msg.isScreenClosed() then
                return -1
            end if
        end If
    end while


End Function

'**********************************************************
'** When a poster on the home screen is selected, we call
'** this function passing an associative array with the
'** data for the selected show.  This data should be
'** sufficient for the show detail (springboard) to display
'**********************************************************
Function displayShowDetailScreen(category as Object, showIndex as Integer) As Integer

    if validateParam(category, "roAssociativeArray", "displayShowDetailScreen") = false return -1

    shows = getShowsForCategoryItem(category, m.curCategory)
    screen = preShowDetailScreen(category.Title, category.kids[m.curCategory].Title)
    showIndex = showDetailScreen(screen, shows, showIndex)

    return showIndex
End Function


'**************************************************************
'** Given an roAssociativeArray representing a category node
'** from the category feed tree, return an roArray containing
'** the names of all of the sub categories in the list.
'***************************************************************
Function getCategoryList(topCategory As Object) As Object

    if validateParam(topCategory, "roAssociativeArray", "getCategoryList") = false return -1

    if type(topCategory) <> "roAssociativeArray" then
        print "incorrect type passed to getCategoryList"
        return -1
    endif

    categoryList = CreateObject("roArray", 100, true)
    for each subCategory in topCategory.Kids
        categoryList.Push(subcategory.Title)
    next
    return categoryList

End Function

'********************************************************************
'** Return the list of shows corresponding the currently selected
'** category in the filter banner.  As the user highlights a
'** category on the top of the poster screen, the list of posters
'** displayed should be refreshed to corrrespond to the highlighted
'** item.  This function returns the list of shows for that category
'********************************************************************
Function getShowsForCategoryItem(category As Object, item As Integer) As Object

    if validateParam(category, "roAssociativeArray", "getCategoryList") = false return invalid

    conn = InitShowFeedConnection(category.kids[item])
    showList = conn.LoadShowFeed(conn)
    return showList

End Function

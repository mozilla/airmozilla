' This Source Code Form is subject to the terms of the Mozilla Public
' License, v. 2.0. If a copy of the MPL was not distributed with this file,
' You can obtain one at http://mozilla.org/MPL/2.0/.

'******************************************************
'Get our device version
'******************************************************

Function GetDeviceVersion()
    return CreateObject("roDeviceInfo").GetVersion()
End Function

'******************************************************
'Get our serial number
'******************************************************

Function GetDeviceESN()
    return CreateObject("roDeviceInfo").GetDeviceUniqueId()
End Function

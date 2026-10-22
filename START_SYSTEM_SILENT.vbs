Set WshShell = CreateObject("WScript.Shell")

' 1. Start 24/7 Omni Harvester in Background (0 = Completely Hidden)
WshShell.Run "cmd /c python omni_lead_harvester_24_7.py", 0, False

' 2. Start Webview Dashboard Server in Background (0 = Completely Hidden)
WshShell.Run "cmd /c python dashboard_server.py", 0, False

' 3. Wait 1 second then open default browser to dashboard
WScript.Sleep 1500
WshShell.Run "http://127.0.0.1:5000"

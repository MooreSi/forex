' FOREX Trader — Silent Launcher (Windows)
' Double-click this file to start the app without a console window.
'
' First-time setup: falls back to Setup & Start FOREX.bat (console needed).
' Subsequent launches: runs pythonw.exe directly; browser opens automatically.

Option Explicit

Dim WshShell, fso, scriptDir, markerFile, venvPythonW

Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

scriptDir   = fso.GetParentFolderName(WScript.ScriptFullName) & "\"
markerFile  = scriptDir & ".venv\req_hash.txt"
venvPythonW = scriptDir & ".venv\Scripts\pythonw.exe"

' ── Already running? Open the browser and exit. ──────────────────────────────
Dim oExec, sOut
Set oExec = WshShell.Exec("cmd /c netstat -an 2>nul")
sOut = oExec.StdOut.ReadAll()
If InStr(sOut, ":8888 ") > 0 And InStr(sOut, "LISTENING") > 0 Then
    WshShell.Run "http://localhost:8888"
    WScript.Quit
End If

' ── First run or venv missing: show setup console. ───────────────────────────
If Not fso.FileExists(markerFile) Or Not fso.FileExists(venvPythonW) Then
    WshShell.Run "cmd /c """ & scriptDir & "Setup & Start FOREX.bat""", 1, False
    WScript.Quit
End If

' ── Normal run: launch silently via pythonw (no console window). ─────────────
' bWaitOnReturn = True keeps this wscript.exe alive while Python runs.
' The restart loop handles exit code 42 (licence activation, update applied).
Dim exitCode
exitCode = WshShell.Run("""" & venvPythonW & """ """ & scriptDir & "run.py""", 0, True)
Do While exitCode = 42
    exitCode = WshShell.Run( _
        """" & venvPythonW & """ """ & scriptDir & "run.py"" --no-browser", 0, True)
Loop

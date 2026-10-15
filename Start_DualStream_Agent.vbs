Option Explicit

Dim shell, fso, folder, pythonw, agent, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

folder = "C:\Users\Public\DualStream_Cloudflare"
pythonw = "C:\Users\ayman\AppData\Local\Programs\Python\Python314\pythonw.exe"
agent = fso.BuildPath(folder, "DualStream_Local_Agent.py")

If Not fso.FileExists(pythonw) Then
    MsgBox "Python was not found:" & vbCrLf & pythonw, vbCritical, "DualStream Agent"
    WScript.Quit 1
End If

If Not fso.FileExists(agent) Then
    MsgBox "Agent script was not found:" & vbCrLf & agent, vbCritical, "DualStream Agent"
    WScript.Quit 1
End If

shell.CurrentDirectory = folder
command = """" & pythonw & """ """ & agent & """"
shell.Run command, 0, False

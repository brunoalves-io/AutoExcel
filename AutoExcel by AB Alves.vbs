Option Explicit
Dim fso, shell, base, exePath, installer
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = fso.BuildPath(base, "AutoExcel by AB Alves.exe")
installer = fso.BuildPath(base, "INICIAR_APP.bat")

If fso.FileExists(exePath) Then
    shell.Run Chr(34) & exePath & Chr(34), 1, False
Else
    shell.Run Chr(34) & installer & Chr(34), 1, False
End If

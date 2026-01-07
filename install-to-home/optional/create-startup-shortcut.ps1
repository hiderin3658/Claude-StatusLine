$WshShell = New-Object -ComObject WScript.Shell
$StartupPath = [Environment]::GetFolderPath('Startup')
$Shortcut = $WshShell.CreateShortcut("$StartupPath\claude-paste.lnk")
$Shortcut.TargetPath = "C:\Users\濱田英樹\Documents\dev\Claude-StatusLine\claude-paste.ahk"
$Shortcut.Save()
Write-Host "Startup shortcut created at: $StartupPath\claude-paste.lnk"

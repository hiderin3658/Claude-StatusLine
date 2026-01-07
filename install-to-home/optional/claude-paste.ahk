#Requires AutoHotkey v2.0
; claude-paste.ahk
; AutoHotkey v2 用スクリプト

; Ctrl+Shift+V で画像を自動貼り付け
^+v::
{
    ; クリップボードから画像を保存するPowerShellコマンド
    psScript := "
    (
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $img = [System.Windows.Forms.Clipboard]::GetImage()
    if ($img) {
        $timestamp = Get-Date -Format 'yyyyMMddHHmmss'
        $path = Join-Path $env:TEMP "claude_$timestamp.png"
        $img.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
        Set-Clipboard -Value $path
    }
    )"

    RunWait('powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "' . psScript . '"', , "Hide")

    Sleep(300)
    Send("^v")
}

; Ctrl+Alt+C でClaude Codeを起動
^!c::
{
    Run("wt.exe -w 0 claude")
}

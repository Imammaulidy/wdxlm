Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d ""C:\Users\KAGE\Desktop\PROJECT BOT IMAM\SCRIPT ADB WD XLM BITGET"" && pm2 resurrect && pm2 start core\ecosystem.config.js", 0, False

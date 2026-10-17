import os
import subprocess

from paths import CORE_DIR, PROJECT_ROOT, VBS_CORE_PATH

startup_dir = os.path.expanduser('~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup')

vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d ""{PROJECT_ROOT}"" && pm2 resurrect && pm2 start Core\\ecosystem.config.js", 0, False
'''

vbs_core_path = VBS_CORE_PATH
with open(vbs_core_path, 'w', encoding='utf-8') as f:
    f.write(vbs_content)

vbs_startup_path = os.path.join(startup_dir, 'autostart_bitget_dashboard.vbs')
with open(vbs_startup_path, 'w', encoding='utf-8') as f:
    f.write(vbs_content)

print('[+] Skrip VBS dibuat di folder core      :', vbs_core_path)
print('[+] Skrip VBS terpasang di Windows Startup:', vbs_startup_path)

# Register Scheduled Task in Windows Task Scheduler (opsional)
try:
    tr_val = 'wscript.exe "' + vbs_core_path + '"'
    cmd = ['schtasks', '/create', '/tn', 'BitgetDashboardAutoStart', '/tr', tr_val, '/sc', 'ONLOGON', '/f']
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print('[+] Windows Task Scheduler (ONLOGON)      : Berhasil terdaftar!')
    else:
        print('[i] Windows Task Scheduler                : Dilewati (perlu hak Admin).')
        print('[+] Jalur Windows Startup Folder          : AKTIF & SIAP (Berjalan otomatis tanpa Admin).')
except Exception:
    print('[i] Windows Task Scheduler status         : Dilewati.')

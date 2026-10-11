const path = require('path');
const fs = require('fs');
const os = require('os');

// Root folder project
const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

// Deteksi Python interpreter yang valid secara dinamis
let pythonPath = 'python';
if (isWin) {
  const globalPython = 'C:\\Users\\KAGE\\AppData\\Local\\Programs\\Python\\Python311\\python.exe';
  const venvPythonw = path.resolve(rootDir, '.venv', 'Scripts', 'pythonw.exe');
  const venvPython = path.resolve(rootDir, '.venv', 'Scripts', 'python.exe');
  
  if (fs.existsSync(venvPythonw)) {
    pythonPath = venvPythonw;
  } else if (fs.existsSync(venvPython)) {
    pythonPath = venvPython;
  } else if (fs.existsSync(globalPython)) {
    pythonPath = globalPython;
  } else {
    pythonPath = 'python';
  }
} else {
  const venvPython = path.resolve(rootDir, '.venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) {
    pythonPath = venvPython;
  } else {
    pythonPath = 'python';
  }
}

module.exports = {
  apps: [
    {
      name: 'bitget-server',
      script: 'core/server.py',
      cwd: rootDir,
      interpreter: pythonPath,
      windowsHide: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '800M',
      restart_delay: 2000,
      max_restarts: 1000,
      min_uptime: '5s',
      kill_timeout: 4000,
      env: {
        PYTHONUNBUFFERED: '1',
        FLASK_ENV: 'production'
      }
    }
  ]
};

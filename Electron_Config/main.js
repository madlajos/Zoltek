const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let pyProc = null;

app.commandLine.appendSwitch('high-dpi-support', 'true');
app.commandLine.appendSwitch('force-device-scale-factor', '1');

// Helper function to get the correct path for the backend executable.
function getBackendPath() {
  const basePath = app.isPackaged ? process.resourcesPath : __dirname;
  return path.join(basePath, 'GUI_backend.exe');
}

ipcMain.handle('dialog:selectFolder', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  return canceled ? '' : filePaths[0] || '';
});

function createWindow() {
  const win = new BrowserWindow({
    show: false, // hide initially to avoid flicker
    fullscreen: false, // NOT fullscreen (F11 mode)
    frame: true, // true = window borders (set false if you want borderless)
    // Updated: use the icon from the assets folder inside the app directory.
    icon: path.join(__dirname, 'app', 'assets', 'favicon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
    }
  });

  win.removeMenu();

  win.maximize();  // This makes the window start maximized

  win.once('ready-to-show', () => {
    win.show(); // Only show after content is ready
  });

  // Load Angular's index.html from the app folder.
  win.loadFile(path.join(__dirname, 'app', 'index.html'));

  // Optionally open DevTools for debugging.
  // win.webContents.openDevTools();
}

app.whenReady().then(() => {
  const backendPath = getBackendPath();
  console.log("Backend executable path:", backendPath);
  pyProc = spawn(backendPath, [], { stdio: 'ignore' });

  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (pyProc) {
    pyProc.kill();
    pyProc = null;
  }
  if (process.platform !== 'darwin') app.quit();
});

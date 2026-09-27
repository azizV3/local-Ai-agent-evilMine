import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: "Autonomous Agent Workspace",
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  
  //icp handler for folder selection



  // Load your local running Vite dev server
  mainWindow.loadURL('http://localhost:5173');
}
  ipcMain.handle('dialog:select-directory', async () => {
  const defaultProjectsPath = path.resolve(app.getAppPath(),'..', '..', 'projects');
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    defaultPath: defaultProjectsPath,
    title: 'Select Project Target Workspace'
  });
  
  if (result.canceled) {
    return null;
  } else {
    return result.filePaths[0]; 
  }
  });

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
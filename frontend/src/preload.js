//preloads the file path securely using contextBridge to hand React a safe button (window.electronAPI.openFolderPicker())
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openFolderPicker: () => ipcRenderer.invoke('dialog:select-directory')
});

// Fires an IPC Invoke event and ipcMain.handle() intercepts it
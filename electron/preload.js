/**
 * SAGE.ai Desktop — Preload Script
 * Exposes a safe bridge between the renderer and Electron main process.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sageAPI', {
  // Navigation listener (keyboard shortcuts from main process)
  onNavigate: (callback) => ipcRenderer.on('navigate', (_, key) => callback(key)),

  // File-save dialog (Export page)
  saveFile: (content, defaultName) =>
    ipcRenderer.invoke('save-file', { content, defaultName }),
});

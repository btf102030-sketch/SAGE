/**
 * SAGE.ai Desktop — Electron Main Process
 * =========================================
 * Creates the main BrowserWindow, registers global keyboard shortcuts,
 * and exposes IPC handlers for the renderer pages.
 */

const { app, BrowserWindow, globalShortcut, ipcMain, dialog } = require('electron');
const path = require('path');
const fs   = require('fs');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    title: 'SAGE.ai — System Analysis & Guidance Engine',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    backgroundColor: '#1e1e2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Register keyboard shortcuts
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.control && !input.shift && !input.alt) {
      const key = input.key.toLowerCase();
      if (['q', 'i', 'e', 't', 'p'].includes(key)) {
        mainWindow.webContents.send('navigate', key);
        event.preventDefault();
      }
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// IPC: Save file dialog (used by Export page)
ipcMain.handle('save-file', async (event, { content, defaultName }) => {
  const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
    title: 'Export SAGE Answer',
    defaultPath: defaultName || 'sage_export.txt',
    filters: [{ name: 'Text Files', extensions: ['txt'] }],
  });
  if (canceled || !filePath) return { success: false };
  fs.writeFileSync(filePath, content, 'utf-8');
  return { success: true, filePath };
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

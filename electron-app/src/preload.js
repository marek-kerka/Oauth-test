const { contextBridge, ipcRenderer } = require('electron');

// Expose safe API to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Send chat message
  sendMessage: (message) => ipcRenderer.invoke('send-message', message),

  // Get auth status
  getAuthStatus: () => ipcRenderer.invoke('get-auth-status'),

  // Start login
  startLogin: () => ipcRenderer.invoke('start-login'),

  // Logout
  logout: () => ipcRenderer.invoke('logout'),

  // Listen to auth status updates
  onAuthStatus: (callback) => {
    ipcRenderer.on('auth-status', (event, data) => callback(data));
  }
});

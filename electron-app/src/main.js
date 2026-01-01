const { app, BrowserWindow, shell, ipcMain } = require('electron');
const Store = require('electron-store');
const path = require('path');

// Config
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8000';
const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || 'http://localhost:8001';
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'dev-encryption-key-change-in-production';

// Secure storage for refresh token
const store = new Store({
  encryptionKey: ENCRYPTION_KEY,
  name: 'oauth-tokens'
});

// Global state
let mainWindow;
let accessToken = null;
let tokenExpiry = null;

// Register custom protocol (myapp://)
app.setAsDefaultProtocolClient('myapp');

// macOS: Handle open-url event
app.on('open-url', (event, url) => {
  event.preventDefault();
  console.log('[macOS] Received URL:', url);

  if (url.startsWith('myapp://auth/callback')) {
    handleAuthCallback(url);
  }
});

// Windows/Linux: Handle second-instance (for custom URL)
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  console.log('Another instance is running, quitting...');
  app.quit();
} else {
  app.on('second-instance', (event, commandLine) => {
    console.log('[Windows/Linux] Second instance, commandLine:', commandLine);

    // Find myapp:// URL in command line arguments
    const url = commandLine.find(arg => arg.startsWith('myapp://'));

    if (url) {
      handleAuthCallback(url);
    }

    // Focus on main window
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// App ready
app.whenReady().then(() => {
  createWindow();
  initAuth();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Create main window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'OAuth Chat App'
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Open DevTools in development
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }
}

// Initialize authentication
async function initAuth() {
  console.log('Initializing auth...');

  // Check for existing refresh token
  const savedRefreshToken = store.get('refresh_token');

  if (savedRefreshToken) {
    console.log('Found saved refresh token, refreshing access token...');
    await refreshAccessToken(savedRefreshToken);
  } else {
    console.log('No refresh token found, need to authenticate');
    // Wait a bit for window to load before opening browser
    setTimeout(() => {
      startAuth();
    }, 1000);
  }
}

// Start authentication flow (open browser)
function startAuth() {
  console.log('Starting auth flow - opening browser...');

  // In production, this would be behind Google OAuth proxy
  // For dev, we simulate proxy by adding X-User-Email header manually in curl
  const authUrl = `${AUTH_SERVICE_URL}/auth/login`;

  console.log(`Opening URL: ${authUrl}`);
  console.log('Note: For testing without proxy, use curl with X-User-Email header');

  shell.openExternal(authUrl);

  // Notify renderer
  if (mainWindow) {
    mainWindow.webContents.send('auth-status', {
      status: 'waiting',
      message: 'Čekání na autorizaci v prohlížeči...'
    });
  }
}

// Handle auth callback from browser
function handleAuthCallback(url) {
  console.log('Processing auth callback:', url);

  try {
    // Parse URL: myapp://auth/callback?access_token=xxx&refresh_token=yyy&expires_in=1800
    const urlObj = new URL(url);
    const params = urlObj.searchParams;

    const newAccessToken = params.get('access_token');
    const newRefreshToken = params.get('refresh_token');
    const expiresIn = params.get('expires_in');

    if (!newAccessToken || !newRefreshToken) {
      console.error('Invalid callback - missing tokens');
      notifyRenderer('error', 'Chyba při autorizaci - chybí tokeny');
      return;
    }

    // Save tokens
    accessToken = newAccessToken;
    store.set('refresh_token', newRefreshToken);

    // Calculate expiry
    if (expiresIn) {
      tokenExpiry = Date.now() + (parseInt(expiresIn) * 1000);
    }

    console.log('✓ Tokens saved successfully');

    // Notify renderer
    notifyRenderer('success', 'Autorizace úspěšná! Můžete začít chatovat.');

  } catch (error) {
    console.error('Error processing callback:', error);
    notifyRenderer('error', `Chyba: ${error.message}`);
  }
}

// Refresh access token
async function refreshAccessToken(refreshToken) {
  console.log('Refreshing access token...');

  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (response.ok) {
      const data = await response.json();
      accessToken = data.access_token;
      tokenExpiry = Date.now() + (data.expires_in * 1000);

      console.log('✓ Access token refreshed');
      notifyRenderer('success', 'Přihlášen');

      return true;
    } else {
      console.error('Refresh failed:', response.status);
      // Refresh token invalid - need re-auth
      store.delete('refresh_token');
      accessToken = null;
      tokenExpiry = null;

      notifyRenderer('error', 'Session vypršela. Přihlaste se znovu.');
      startAuth();

      return false;
    }
  } catch (error) {
    console.error('Refresh error:', error);
    notifyRenderer('error', `Chyba při refresh: ${error.message}`);
    startAuth();
    return false;
  }
}

// Call LLM API
async function callLLMAPI(message, conversationId = null) {
  console.log('Calling LLM API:', message);

  // Check token expiry
  if (tokenExpiry && Date.now() > tokenExpiry) {
    console.log('Token expired, refreshing...');
    const refreshToken = store.get('refresh_token');
    if (refreshToken) {
      const success = await refreshAccessToken(refreshToken);
      if (!success) {
        throw new Error('Failed to refresh token');
      }
    } else {
      throw new Error('No refresh token available');
    }
  }

  if (!accessToken) {
    throw new Error('No access token available');
  }

  try {
    const response = await fetch(`${LLM_SERVICE_URL}/llm/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        message: message,
        conversation_id: conversationId
      })
    });

    // Handle token expiration
    if (response.status === 401) {
      const error = await response.json();

      if (error.error === 'token_expired') {
        console.log('Token expired during API call, refreshing...');

        const refreshToken = store.get('refresh_token');
        if (refreshToken) {
          const success = await refreshAccessToken(refreshToken);
          if (success) {
            // Retry API call
            return await callLLMAPI(message, conversationId);
          }
        }
      }

      throw new Error(error.message || 'Unauthorized');
    }

    if (!response.ok) {
      throw new Error(`API call failed: ${response.status}`);
    }

    const data = await response.json();
    console.log('✓ LLM response received');
    return data;

  } catch (error) {
    console.error('LLM API error:', error);
    throw error;
  }
}

// Notify renderer process
function notifyRenderer(status, message) {
  if (mainWindow) {
    mainWindow.webContents.send('auth-status', { status, message });
  }
}

// IPC Handlers
ipcMain.handle('send-message', async (event, message) => {
  try {
    const response = await callLLMAPI(message);
    return { success: true, data: response };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-auth-status', async () => {
  const hasRefreshToken = !!store.get('refresh_token');
  const hasAccessToken = !!accessToken;

  return {
    authenticated: hasRefreshToken && hasAccessToken,
    hasRefreshToken,
    hasAccessToken
  };
});

ipcMain.handle('start-login', async () => {
  startAuth();
  return { success: true };
});

ipcMain.handle('logout', async () => {
  // Revoke refresh token on server
  const refreshToken = store.get('refresh_token');
  if (refreshToken) {
    try {
      await fetch(`${AUTH_SERVICE_URL}/auth/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    } catch (error) {
      console.error('Error revoking token:', error);
    }
  }

  // Clear local tokens
  store.delete('refresh_token');
  accessToken = null;
  tokenExpiry = null;

  notifyRenderer('info', 'Odhlášen');

  return { success: true };
});

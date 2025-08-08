const { contextBridge, ipcRenderer } = require("electron");

// Expose AIris-specific API to the renderer process
contextBridge.exposeInMainWorld("airisAPI", {
  // Query operations
  sendQuery: (query, webSearchEnabled) =>
    ipcRenderer.invoke("send-query", {
      query,
      webSearchEnabled,
    }),

  // File operations
  uploadFile: (fileData, fileName) =>
    ipcRenderer.invoke("upload-file", fileData, fileName),
  selectFile: () => ipcRenderer.invoke("select-file"),
  openFile: (fileName) => ipcRenderer.invoke("open-file", fileName),
  deleteFile: (fileName) => ipcRenderer.invoke("delete-file", fileName),

  // Health and monitoring
  checkHealth: () => ipcRenderer.invoke("check-health"),
  getMetrics: () => ipcRenderer.invoke("get-metrics"),

  // Development tools
  openDevTools: () => ipcRenderer.invoke("open-dev-tools"),

  // App info
  getAppInfo: () => ipcRenderer.invoke("get-app-info"),

  // Utility functions
  platform: process.platform,

  // Event listeners for updates and notifications
  onUpdateAvailable: (callback) => ipcRenderer.on("update-available", callback),
  onUpdateDownloaded: (callback) =>
    ipcRenderer.on("update-downloaded", callback),
  onConnectionStatus: (callback) =>
    ipcRenderer.on("connection-status", callback),

  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});

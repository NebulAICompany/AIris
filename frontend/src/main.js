const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const logger = require("./logger");

// Use undici for modern fetch support
const { fetch, FormData, File } = require("undici");

// Enable live reload for development
if (process.argv.includes("--dev")) {
  try {
    require("electron-reload")(__dirname, {
      electron: path.join(__dirname, "..", "node_modules", ".bin", "electron"),
      hardResetMethod: "exit",
    });
  } catch {}
}

class AIrisApp {
  constructor() {
    this.mainWindow = null;
    this.init();
  }

  init() {
    logger.info("Initializing AIris Desktop Application");

    // Handle app ready
    app.whenReady().then(() => {
      logger.info("App is ready, creating window");
      this.createWindow();
      this.setupIPC();
    });

    // Handle all windows closed
    app.on("window-all-closed", () => {
      logger.info("All windows closed");
      if (process.platform !== "darwin") {
        logger.info("Quitting application");
        app.quit();
      }
    });

    // Handle activate (macOS)
    app.on("activate", () => {
      logger.debug("App activated");
      if (BrowserWindow.getAllWindows().length === 0) {
        logger.info("No windows open, creating new window");
        this.createWindow();
      }
    });
  }

  createWindow() {
    logger.info("Creating main window");

    this.mainWindow = new BrowserWindow({
      width: 1400,
      height: 900,
      minWidth: 1000,
      minHeight: 700,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: path.join(__dirname, "preload.js"),
      },
      icon: path.join(__dirname, "..", "assets", "icon.png"),
      titleBarStyle: "default",
      show: false,
    });

    // Load the main HTML file
    logger.debug("Loading main HTML file");
    this.mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

    // Show window when ready to prevent visual flash
    this.mainWindow.once("ready-to-show", () => {
      logger.info("Main window ready to show");
      this.mainWindow.show();
    });

    // Filter out annoying DevTools console messages
    this.mainWindow.webContents.on(
      "console-message",
      (event, level, message, line, sourceId) => {
        // Suppress specific autofill-related DevTools errors
        if (
          message.includes("Request Autofill.enable failed") ||
          message.includes("Request Autofill.setAddresses failed") ||
          message.includes("'Autofill.enable' wasn't found") ||
          message.includes("'Autofill.setAddresses' wasn't found")
        ) {
          event.preventDefault();
          return;
        }
      }
    );

    // Open DevTools in development
    if (process.argv.includes("--dev")) {
      logger.debug("Opening DevTools for development");
      this.mainWindow.webContents.openDevTools();
    }

    // Handle window closed
    this.mainWindow.on("closed", () => {
      logger.info("Main window closed");
      this.mainWindow = null;
    });
  }

  setupIPC() {
    // Clear any existing handlers to prevent duplicates
    ipcMain.removeAllListeners("select-file");
    ipcMain.removeAllListeners("read-file");
    ipcMain.removeAllListeners("open-file");
    ipcMain.removeAllListeners("get-metrics");
    ipcMain.removeAllListeners("delete-file");
    ipcMain.removeAllListeners("get-app-info");
    ipcMain.removeAllListeners("send-query");
    ipcMain.removeAllListeners("upload-file");
    ipcMain.removeAllListeners("check-health");
    ipcMain.removeAllListeners("open-dev-tools");

    // Handle file selection dialog
    ipcMain.handle("select-file", async () => {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ["openFile"],
        filters: [
          {
            name: "Documents",
            extensions: ["pdf", "docx", "xlsx", "txt", "png", "jpg", "jpeg"],
          },
          { name: "PDF Files", extensions: ["pdf"] },
          { name: "Word Documents", extensions: ["docx"] },
          { name: "Excel Files", extensions: ["xlsx"] },
          { name: "Images", extensions: ["png", "jpg", "jpeg"] },
          { name: "All Files", extensions: ["*"] },
        ],
      });

      return result;
    });

    // Handle file reading
    ipcMain.handle("read-file", async (event, filePath) => {
      try {
        const stats = fs.statSync(filePath);
        const fileBuffer = fs.readFileSync(filePath);

        return {
          success: true,
          fileName: path.basename(filePath),
          size: stats.size,
          buffer: fileBuffer,
          mimeType: this.getMimeType(filePath),
        };
      } catch (error) {
        return {
          success: false,
          error: error.message,
        };
      }
    });

    // Handle file opening
    ipcMain.handle("open-file", async (event, fileName) => {
      try {
        const { shell } = require("electron");
        const path = require("path");

        // Construct the file path
        const uploadsDir = path.join(
          __dirname,
          "..",
          "..",
          "backend",
          "database",
          "uploads"
        );
        const filePath = path.join(uploadsDir, fileName);

        // Check if file exists
        if (!fs.existsSync(filePath)) {
          return {
            success: false,
            error: "File not found",
          };
        }

        // Open file with default application
        const result = await shell.openPath(filePath);

        if (result) {
          // If result is not empty, there was an error
          return {
            success: false,
            error: result,
          };
        }

        return {
          success: true,
        };
      } catch (error) {
        return {
          success: false,
          error: error.message,
        };
      }
    });

    // Handle metrics requests
    ipcMain.handle("get-metrics", async () => {
      try {
        const response = await fetch("http://localhost:8000/api/metrics");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const metrics = await response.json();
        return metrics;
      } catch (error) {
        logger.warn(`Failed to fetch metrics: ${error.message}`, "IPC");
        // Return fallback metrics
        return {
          totalQueries: 0,
          totalDocuments: 0,
          avgResponseTime: "N/A",
          systemHealth: "Disconnected",
          vectorStoreStatus: "Unknown",
          lastUpdated: new Date().toISOString(),
          recentActivity: [],
        };
      }
    });

    // Handle file deletion
    ipcMain.handle("delete-file", async (event, fileName) => {
      logger.info(`Delete file request received: ${fileName}`, "IPC");

      try {
        const url = `http://localhost:8000/api/files/${encodeURIComponent(
          fileName
        )}`;
        logger.debug(`Sending DELETE request to: ${url}`, "IPC");

        const response = await fetch(url, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        });

        logger.debug(
          `Response status: ${response.status}, ok: ${response.ok}`,
          "IPC"
        );

        if (!response.ok) {
          const errorData = await response
            .json()
            .catch(() => ({ detail: "Unknown error" }));
          logger.error(
            `Delete request failed: ${JSON.stringify(errorData)}`,
            "IPC"
          );
          return {
            success: false,
            error: errorData.detail || `HTTP error! status: ${response.status}`,
          };
        }

        const result = await response.json();
        logger.info(`File deleted successfully: ${fileName}`, "IPC");
        return {
          success: true,
          data: result,
        };
      } catch (error) {
        logger.error(`Failed to delete file: ${error.message}`, "IPC");
        logger.debug(`Error details: ${error.stack}`, "IPC");
        return {
          success: false,
          error: error.message,
        };
      }
    });

    // Handle app info requests
    ipcMain.handle("get-app-info", () => {
      return {
        name: app.getName(),
        version: app.getVersion(),
        platform: process.platform,
        arch: process.arch,
      };
    });

    // Handle query requests

    ipcMain.handle(
      "send-query",
      async (
        event,
        {
          query,
          webSearchEnabled = false,
          wolframEnabled = false,
        }
      ) => {
        try {
          logger.info(
            `Sending query: ${query.substring(0, 100)}...`,
            "IPC",
            "Web search enabled:",
            webSearchEnabled,
            "Wolfram enabled:",
            wolframEnabled,
            "RAG Fusion enabled:",
            false
          );
          const response = await fetch("http://localhost:8000/api/query", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json",
            },
            body: JSON.stringify({
              query,
              webSearchEnabled,
              wolframEnabled,
            }),
          });

          logger.debug(`Query response status: ${response.status}`, "IPC");

          if (!response.ok) {
            const errorText = await response.text();
            logger.error(`API Error Response: ${errorText}`, "IPC");
            throw new Error(
              `HTTP error! status: ${response.status}, message: ${errorText}`
            );
          }

          const result = await response.json();
          logger.info("Query processed successfully", "IPC");
          return result;
        } catch (error) {
          logger.error(`Query error: ${error.message}`, "IPC");
          throw new Error(`Failed to send query: ${error.message}`);
        }
      }
    ); // Handle file upload requests

    ipcMain.handle("upload-file", async (event, fileData, fileName) => {
      try {
        logger.info(`Starting file upload: ${fileName}`, "IPC");

        const formData = new FormData();

        // Create a Blob from the file data (Blob is available in Node.js with fetch)
        const uint8Array = new Uint8Array(fileData);
        const blob = new Blob([uint8Array], {
          type: this.getMimeType(fileName),
        });

        formData.append("file", blob, fileName);

        logger.debug("Sending upload request to backend", "IPC");
        const response = await fetch("http://localhost:8000/api/upload", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          logger.error(
            `Upload failed: HTTP ${response.status}: ${errorText}`,
            "IPC"
          );
          throw new Error(
            `HTTP error! status: ${response.status}, message: ${errorText}`
          );
        }

        logger.info(`File uploaded successfully: ${fileName}`, "IPC");
        return await response.json();
      } catch (error) {
        logger.error(`Upload error: ${error.message}`, "IPC");
        throw new Error(`Failed to upload file: ${error.message}`);
      }
    });

    // Handle health check requests
    ipcMain.handle("check-health", async () => {
      try {
        const response = await fetch("http://localhost:8000/", {
          method: "GET",
        });

        return {
          status: response.ok ? "healthy" : "unhealthy",
          statusCode: response.status,
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        throw new Error(`Health check failed: ${error.message}`);
      }
    });

    // Handle dev tools requests
    ipcMain.handle("open-dev-tools", () => {
      if (this.mainWindow && this.mainWindow.webContents) {
        this.mainWindow.webContents.openDevTools();
      }
    });
  }

  getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      ".pdf": "application/pdf",
      ".docx":
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ".xlsx":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      ".txt": "text/plain",
      ".png": "image/png",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
    };
    return mimeTypes[ext] || "application/octet-stream";
  }
}

// Create the app instance
new AIrisApp();

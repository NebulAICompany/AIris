const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");

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
    // Handle app ready
    app.whenReady().then(() => {
      this.createWindow();
      this.setupIPC();
    });

    // Handle all windows closed
    app.on("window-all-closed", () => {
      if (process.platform !== "darwin") {
        app.quit();
      }
    });

    // Handle activate (macOS)
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createWindow();
      }
    });
  }

  createWindow() {
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
    this.mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

    // Show window when ready to prevent visual flash
    this.mainWindow.once("ready-to-show", () => {
      this.mainWindow.show();
    });

    // Open DevTools in development
    if (process.argv.includes("--dev")) {
      this.mainWindow.webContents.openDevTools();
    }

    // Handle window closed
    this.mainWindow.on("closed", () => {
      this.mainWindow = null;
    });
  }

  setupIPC() {
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
        const uploadsDir = path.join(__dirname, "..", "..", "aiiris_backend", "uploads");
        const filePath = path.join(uploadsDir, fileName);
        
        // Check if file exists
        if (!fs.existsSync(filePath)) {
          return {
            success: false,
            error: "File not found"
          };
        }
        
        // Open file with default application
        const result = await shell.openPath(filePath);
        
        if (result) {
          // If result is not empty, there was an error
          return {
            success: false,
            error: result
          };
        }
        
        return {
          success: true
        };
      } catch (error) {
        return {
          success: false,
          error: error.message
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
        console.error("Failed to fetch metrics:", error);
        // Return fallback metrics
        return {
          totalQueries: 0,
          totalDocuments: 0,
          avgResponseTime: "N/A",
          systemHealth: "Disconnected",
          vectorStoreStatus: "Unknown",
          lastUpdated: new Date().toISOString(),
          recentActivity: []
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
    }); // Handle query requests
    ipcMain.handle("send-query", async (event, query) => {
      try {
        console.log("Sending query:", query);
        const response = await fetch("http://localhost:8000/api/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ query }),
        });

        console.log("Response status:", response.status);

        if (!response.ok) {
          const errorText = await response.text();
          console.error("API Error Response:", errorText);
          throw new Error(
            `HTTP error! status: ${response.status}, message: ${errorText}`
          );
        }

        const result = await response.json();
        console.log("Query result:", result);
        return result;
      } catch (error) {
        console.error("Query error:", error);
        throw new Error(`Failed to send query: ${error.message}`);
      }
    }); // Handle file upload requests
    ipcMain.handle("upload-file", async (event, fileData, fileName) => {
      try {
        const formData = new FormData();

        // Create a Blob from the file data (Blob is available in Node.js with fetch)
        const uint8Array = new Uint8Array(fileData);
        const blob = new Blob([uint8Array], {
          type: this.getMimeType(fileName),
        });

        formData.append("file", blob, fileName);

        const response = await fetch("http://localhost:8000/api/upload", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(
            `HTTP error! status: ${response.status}, message: ${errorText}`
          );
        }

        return await response.json();
      } catch (error) {
        console.error("Upload error:", error);
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

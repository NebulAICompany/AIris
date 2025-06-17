/**
 * Main Application Entry Point for AIris Electron App
 * Initializes and coordinates all application components
 */

class AIrisApp {
  constructor() {
    this.uiComponents = null;
    this.isInitialized = false;
    this.backendConnected = false;

    this.init();
  }

  async init() {
    try {
      logger.info("Initializing AIris App...", 'APP');

      // Wait for DOM to be ready
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => this.start());
      } else {
        await this.start();
      }
    } catch (error) {
      logger.error(`Failed to initialize app: ${error.message}`, 'APP');
      this.showErrorScreen(error);
    }
  }

  async start() {
    try {
      // Show loading screen
      this.showLoadingScreen();

      // Check backend connection
      await this.checkBackendConnection();

      // Initialize UI components
      this.uiComponents = new UIComponents();
      window.uiComponents = this.uiComponents; // Global access for HTML event handlers

      // Setup global error handling
      this.setupErrorHandling();

      // Setup app-level shortcuts
      this.setupKeyboardShortcuts();

      // Hide loading screen and show app
      this.hideLoadingScreen();

      this.isInitialized = true;
      logger.info("AIris App initialized successfully", 'APP');

      // Show connection status
      this.updateConnectionStatus(this.backendConnected);
    } catch (error) {
      logger.error(`Failed to start app: ${error.message}`, 'APP');
      this.showErrorScreen(error);
    }
  }

  async checkBackendConnection() {
    try {
      console.log("Checking backend connection...");

      // Try to connect to the backend
      const health = await window.airisAPI.checkHealth();
      this.backendConnected = true;

      console.log("Backend connection successful:", health);
    } catch (error) {
      console.warn("Backend connection failed:", error);
      this.backendConnected = false;

      // Show warning but don't block the app
      this.showConnectionWarning();
    }
  }

  showLoadingScreen() {
    const loadingScreen = document.createElement("div");
    loadingScreen.id = "loading-screen";
    loadingScreen.className = "loading-screen";

    loadingScreen.innerHTML = `
            <div class="loading-content">
                <div class="loading-logo">
                    <i class="fas fa-brain"></i>
                </div>
                <h2>AIris</h2>
                <p>Initializing AI Financial Assistant...</p>
                <div class="loading-spinner">
                    <div class="spinner"></div>
                </div>
            </div>
        `;

    document.body.appendChild(loadingScreen);
  }

  hideLoadingScreen() {
    const loadingScreen = document.getElementById("loading-screen");
    if (loadingScreen) {
      loadingScreen.classList.add("fade-out");
      setTimeout(() => {
        loadingScreen.remove();
      }, 500);
    }
  }

  showErrorScreen(error) {
    const errorScreen = document.createElement("div");
    errorScreen.id = "error-screen";
    errorScreen.className = "error-screen";

    errorScreen.innerHTML = `
            <div class="error-content">
                <div class="error-icon">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <h2>Application Error</h2>
                <p>Sorry, something went wrong while starting the application.</p>
                <div class="error-details">
                    <strong>Error:</strong> ${Utils.escapeHtml(error.message)}
                </div>
                <div class="error-actions">
                    <button onclick="location.reload()" class="btn btn-primary">
                        <i class="fas fa-redo"></i> Reload Application
                    </button>
                    <button onclick="window.airisAPI.openDevTools()" class="btn btn-secondary">
                        <i class="fas fa-bug"></i> Open Developer Tools
                    </button>
                </div>
            </div>
        `;

    document.body.appendChild(errorScreen);

    // Hide loading screen if visible
    this.hideLoadingScreen();
  }

  showConnectionWarning() {
    const warning = document.createElement("div");
    warning.className = "connection-warning";
    warning.innerHTML = `
            <div class="warning-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Backend connection failed. Some features may not work properly.</span>
                <button onclick="this.parentElement.parentElement.remove()" class="close-btn">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

    document.body.appendChild(warning);

    // Auto-hide after 10 seconds
    setTimeout(() => {
      if (warning.parentElement) {
        warning.remove();
      }
    }, 10000);
  }

  updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById("connection-status");
    if (statusIndicator) {
      statusIndicator.className = `connection-status ${
        connected ? "connected" : "disconnected"
      }`;
      statusIndicator.innerHTML = connected
        ? '<i class="fas fa-circle"></i> Connected'
        : '<i class="fas fa-circle"></i> Disconnected';
    }
  }

  setupErrorHandling() {
    // Global error handler
    window.addEventListener("error", (event) => {
      console.error("Global error:", event.error);
      this.handleError(event.error);
    });

    // Promise rejection handler
    window.addEventListener("unhandledrejection", (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      this.handleError(event.reason);
    });
  }

  handleError(error) {
    // Don't show multiple error notifications
    if (this.errorShown) return;

    this.errorShown = true;

    // Show user-friendly error message
    if (this.uiComponents) {
      this.uiComponents.showNotification(
        "An unexpected error occurred. Please try again.",
        "error"
      );
    }

    // Reset error flag after a delay
    setTimeout(() => {
      this.errorShown = false;
    }, 5000);
  }

  setupKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Ctrl/Cmd + K: Focus search/chat input
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        const chatInput = document.getElementById("chat-input");
        if (chatInput && this.uiComponents.currentTab === "chat") {
          chatInput.focus();
        }
      }

      // Ctrl/Cmd + U: Switch to upload tab
      if ((e.ctrlKey || e.metaKey) && e.key === "u") {
        e.preventDefault();
        this.uiComponents.switchTab("upload");
      }

      // Ctrl/Cmd + 1-5: Switch between tabs
      if ((e.ctrlKey || e.metaKey) && e.key >= "1" && e.key <= "5") {
        e.preventDefault();
        const tabs = ["chat", "upload", "files", "analytics", "settings"];
        const tabIndex = parseInt(e.key) - 1;
        if (tabs[tabIndex]) {
          this.uiComponents.switchTab(tabs[tabIndex]);
        }
      }

      // Ctrl/Cmd + Shift + D: Toggle dark mode
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "D") {
        e.preventDefault();
        this.uiComponents.toggleTheme();
      }

      // Ctrl/Cmd + Shift + K: Clear chat
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "K") {
        e.preventDefault();
        if (this.uiComponents.currentTab === "chat") {
          this.uiComponents.clearChat();
        }
      }

      // F12: Toggle developer tools
      if (e.key === "F12") {
        e.preventDefault();
        window.airisAPI.openDevTools();
      }
    });
  }

  // Public API for external access
  getConnectionStatus() {
    return this.backendConnected;
  }

  async reconnectBackend() {
    try {
      await this.checkBackendConnection();
      this.updateConnectionStatus(this.backendConnected);

      if (this.backendConnected && this.uiComponents) {
        this.uiComponents.showNotification(
          "Backend connection restored!",
          "success"
        );
      }

      return this.backendConnected;
    } catch (error) {
      console.error("Reconnection failed:", error);
      return false;
    }
  }

  // Lifecycle methods
  onBeforeUnload() {
    // Save any pending data
    if (this.uiComponents) {
      // Save current chat history to local storage
      const chatHistory = this.uiComponents.chatHistory;
      if (chatHistory.length > 0) {
        localStorage.setItem("airis-chat-history", JSON.stringify(chatHistory));
      }
    }
  }

  onWindowFocus() {
    // Check backend connection when window regains focus
    if (this.isInitialized) {
      this.checkBackendConnection().then(() => {
        this.updateConnectionStatus(this.backendConnected);
      });
    }
  }

  // Development helpers
  getDebugInfo() {
    return {
      isInitialized: this.isInitialized,
      backendConnected: this.backendConnected,
      currentTab: this.uiComponents?.currentTab,
      chatHistory: this.uiComponents?.chatHistory?.length || 0,
      uploadedFiles: this.uiComponents?.uploadedFiles?.length || 0,
      theme: this.uiComponents?.isDarkMode ? "dark" : "light",
    };
  }
}

// Window lifecycle handlers
window.addEventListener("beforeunload", () => {
  if (window.airisApp) {
    window.airisApp.onBeforeUnload();
  }
});

window.addEventListener("focus", () => {
  if (window.airisApp) {
    window.airisApp.onWindowFocus();
  }
});

// Initialize the application
window.airisApp = new AIrisApp();

// Global access for debugging
window.getDebugInfo = () =>
  window.airisApp?.getDebugInfo() || "App not initialized";
window.reconnectBackend = () => window.airisApp?.reconnectBackend();

console.log("AIris App script loaded successfully");

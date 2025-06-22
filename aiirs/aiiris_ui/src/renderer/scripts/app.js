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
      logger.info("Initializing AIris App...", "APP");

      // Wait for DOM to be ready
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => this.start());
      } else {
        await this.start();
      }
    } catch (error) {
      logger.error(`Failed to initialize app: ${error.message}`, "APP");
      this.showErrorScreen(error);
    }
  }

  async start() {
    try {
      // Show loading screen
      this.showLoadingScreen();

      // Initialize language service first
      if (window.languageService) {
        // Set initial language and update page texts
        window.languageService.updatePageTexts();
        logger.info("Language service initialized", "APP");
      }

      // Check backend connection
      await this.checkBackendConnection();

      // Initialize UI components
      this.uiComponents = new UIComponents();
      window.uiComponents = this.uiComponents; // Global access for HTML event handlers

      // Load chat sessions
      await this.uiComponents.loadChatSessions();

      // Fix any existing metadata formatting after loading
      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        if (this.uiComponents) {
          this.uiComponents.fixExistingMetadataFormatting();

          // Apply additional formatting passes to catch any delayed renders
          setTimeout(() => {
            if (this.uiComponents) {
              this.uiComponents.fixExistingMetadataFormatting();
            }
          }, 200);

          setTimeout(() => {
            if (this.uiComponents) {
              this.uiComponents.fixExistingMetadataFormatting();
            }
          }, 500);
        }
      });

      // Initialize currency service
      logger.info("Initializing currency service...", "APP");
      this.currencyService = new CurrencyService();
      window.currencyService = this.currencyService; // Global access
      await this.currencyService.start();

      // Setup global error handling
      this.setupErrorHandling();

      // Setup app-level shortcuts
      this.setupKeyboardShortcuts();

      // Initialize currency service
      this.initializeCurrencyService();

      // Hide loading screen and show app
      this.hideLoadingScreen();

      this.isInitialized = true;
      logger.info("AIris App initialized successfully", "APP");

      // Show connection status
      this.updateConnectionStatus(this.backendConnected);
    } catch (error) {
      logger.error(`Failed to start app: ${error.message}`, "APP");
      this.showErrorScreen(error);
    }
  }

  async checkBackendConnection(retries = 3) {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        logger.info(
          `Checking backend connection... (attempt ${attempt}/${retries})`,
          "APP"
        );

        // Try to connect to the backend with a shorter timeout for connection check
        const health = await window.apiService.healthCheck();
        this.backendConnected = true;

        logger.info("Backend connection successful", "APP");
        return;
      } catch (error) {
        logger.warn(
          `Backend connection attempt ${attempt} failed: ${error.message}`,
          "APP"
        );

        if (attempt < retries) {
          // Wait before retrying (exponential backoff)
          const waitTime = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
          logger.info(`Retrying connection in ${waitTime}ms...`, "APP");
          await new Promise((resolve) => setTimeout(resolve, waitTime));
        }
      }
    }

    // All attempts failed
    this.backendConnected = false;
    logger.error("Backend connection failed after all retries", "APP");

    // Show warning but don't block the app
    this.showConnectionWarning();
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
                    <button onclick="window.apiService.openDevTools()" class="btn btn-secondary">
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
    // Remove any existing warning
    const existingWarning = document.querySelector(".connection-warning");
    if (existingWarning) {
      existingWarning.remove();
    }

    const warning = document.createElement("div");
    warning.className = "connection-warning";
    warning.innerHTML = `
            <div class="warning-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Backend bağlantısı başarısız. AI özelliklerini kullanmak için backend'in çalıştığından emin olun.</span>
                <div class="warning-actions">
                    <button onclick="window.airisApp.reconnectBackend()" class="retry-btn">
                        <i class="fas fa-redo"></i> Tekrar Dene
                    </button>
                    <button onclick="this.closest('.connection-warning').remove()" class="close-btn">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;

    document.body.appendChild(warning);

    // Auto-hide after 15 seconds
    setTimeout(() => {
      if (warning.parentElement) {
        warning.remove();
      }
    }, 15000);
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
      logger.error(`Global error: ${event.error?.message}`, "APP");
      this.handleError(event.error);
    });

    // Promise rejection handler
    window.addEventListener("unhandledrejection", (event) => {
      logger.error(`Unhandled promise rejection: ${event.reason}`, "APP");
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
        window.apiService.openDevTools();
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
      logger.error(`Reconnection failed: ${error.message}`, "APP");
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

    // Stop currency service
    if (this.currencyService) {
      this.currencyService.stop();
      logger.info("Currency service stopped", "APP");
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

  initializeCurrencyService() {
    logger.info("Initializing currency service", "APP");

    // Start the currency service with update callback
    window.currencyService.start((data) => {
      this.updateCurrencyDisplay(data);
    });

    // Handle app cleanup
    window.addEventListener("beforeunload", () => {
      window.currencyService.stop();
    });
  }

  updateCurrencyDisplay(data) {
    try {
      const { currencies, gold, lastUpdate, isStale } = data;

      if (currencies) {
        // Update USD/TRY
        const usdTryElement = document.getElementById("usd-try");
        if (usdTryElement) {
          usdTryElement.textContent = window.currencyService.formatNumber(
            currencies.usdTry,
            2
          );
        }

        // Update EUR/TRY
        const eurTryElement = document.getElementById("eur-try");
        if (eurTryElement) {
          eurTryElement.textContent = window.currencyService.formatNumber(
            currencies.eurTry,
            2
          );
        }

        // Update USD/EUR
        const usdEurElement = document.getElementById("usd-eur");
        if (usdEurElement) {
          usdEurElement.textContent = window.currencyService.formatNumber(
            currencies.usdEur,
            4
          );
        }
      }

      if (gold) {
        // Update Gold price
        const goldElement = document.getElementById("gold-price");
        if (goldElement) {
          goldElement.textContent = `$${window.currencyService.formatNumber(
            gold.price,
            0
          )}`;
        }
      }

      // Update status indicator
      const statusElement = document.getElementById("currency-status");
      if (statusElement) {
        const statusIcon = statusElement.querySelector("i");
        const statusText = statusElement.querySelector(".status-text");

        if (isStale) {
          statusElement.className = "currency-status stale";
          statusText.textContent = "Cached";
        } else {
          statusElement.className = "currency-status live";
          statusText.textContent = "Live";
        }
      }

      logger.debug("Currency display updated", "APP");
    } catch (error) {
      logger.error(
        `Failed to update currency display: ${error.message}`,
        "APP"
      );

      // Show error state
      const statusElement = document.getElementById("currency-status");
      if (statusElement) {
        statusElement.className = "currency-status error";
        const statusText = statusElement.querySelector(".status-text");
        if (statusText) {
          statusText.textContent = "Error";
        }
      }
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
      currencyService: window.currencyService?.getCurrentData() || null,
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

logger.info("AIris App script loaded successfully", "APP");

/**
 * Main Application Entry Point for AIris Electron App
 * Initializes and coordinates all application components
 */

class AIrisApp {
  constructor() {
    this.uiComponents = null;
    this.isInitialized = false;
    this.backendConnected = false;
    this.currentTheme = "light";

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
      // Load themes first before showing loading screen
      this.loadTheme();

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

      // Render market EOD tiles on news tab
      this.renderMarketTiles();

      // Setup chart period selector
      this.setupChartPeriodSelector();

      // Show connection status
      this.updateConnectionStatus(this.backendConnected);
    } catch (error) {
      logger.error(`Failed to start app: ${error.message}`, "APP");
      this.showErrorScreen(error);
    }
  }

  async renderMarketTiles(days = 7) {
    try {
      const api = new APIService();
      let response = await api.getMarketEod("TUPRS.IS", days);
      let data = response.data?.data || [];

      const container = document.querySelector("#market-eod");
      if (!container) return;

      let latest = data?.[0];
      // If no cached data yet, force refresh once
      if (!latest) {
        try {
          await api.refreshMarketEod();
          response = await api.getMarketEod("TUPRS.IS", days);
          data = response.data?.data || [];
          latest = data?.[0];
        } catch {}
      }

      if (!latest) {
        container.innerHTML = `
          <div class="market-grid">
            <div class="market-tile">
              <div class="market-title">TUPRS.IS</div>
              <div class="market-sub">No data yet. Click refresh above.</div>
            </div>
          </div>`;
        return;
      }

      // Create mini chart SVG
      const chartSvg = this.createMiniChart(data);
      
      // Calculate change from first data point (oldest) to latest
      const firstDataPoint = data[data.length - 1]; // Last in array is oldest
      const change = latest.close - firstDataPoint.close;
      const changePercent = ((change / firstDataPoint.close) * 100);
      const isPositive = change >= 0;
      const changeColor = isPositive ? '#10b981' : '#ef4444';
      const changeSymbol = isPositive ? '↑' : '↓';

      // Create 8 market tiles
      const tiles = [];
      for (let i = 0; i < 8; i++) {
        const isFirstTile = i === 0;
        tiles.push(`
          <div class="market-tile" data-tile-index="${i}">
            <div class="market-tile-header">
              <div class="market-title">${isFirstTile ? 'TUPRS.IS' : 'STOCK' + (i + 1)}</div>
              <div class="market-change-indicator" style="background-color: ${isFirstTile ? changeColor + '20' : '#e7e7e920'}; color: ${isFirstTile ? changeColor : '#667085'};">
                <span class="change-symbol">${isFirstTile ? changeSymbol : '--'}</span>
                <span class="change-percent">${isFirstTile ? '%' + Math.abs(changePercent).toFixed(2) : '--'}</span>
              </div>
            </div>
            <div class="market-change-absolute" style="color: ${isFirstTile ? changeColor : '#667085'};">
              ${isFirstTile ? (isPositive ? '+' : '') + change.toFixed(2) : '--'}
            </div>
            <div class="market-chart-container">
              <div class="market-chart">${isFirstTile ? chartSvg : ''}</div>
            </div>
            <div class="market-price">${isFirstTile ? latest.close?.toLocaleString("tr-TR") + ' TRY' : '--'}</div>
          </div>
        `);
      }

      container.innerHTML = `
        <div class="market-grid">
          ${tiles.join('')}
        </div>
      `;
    } catch (e) {
      console.error("Market tiles render error", e);
    }
  }

  createMiniChart(data) {
    if (!data || data.length < 2) return '';

    // Sort data by date (oldest first for chart)
    const sortedData = [...data].reverse();
    const prices = sortedData.map(d => d.close);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;
    
    // Chart dimensions - responsive width, fixed height
    const width = 200; // This will be overridden by CSS
    const height = 12;
    const padding = 2;
    
    // Create smooth curve using quadratic bezier curves
    const points = sortedData.map((d, i) => {
      const x = padding + (i / (sortedData.length - 1)) * (width - 2 * padding);
      const y = padding + ((maxPrice - d.close) / priceRange) * (height - 2 * padding);
      return { x, y };
    });
    
    // Create smooth path with curves
    let pathData = `M ${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const next = points[i + 1];
      
      if (next) {
        // Use quadratic bezier for smooth curves
        const cp1x = prev.x + (curr.x - prev.x) / 2;
        const cp1y = prev.y;
        const cp2x = curr.x - (next.x - curr.x) / 2;
        const cp2y = curr.y;
        pathData += ` Q ${cp1x},${cp1y} ${curr.x},${curr.y}`;
      } else {
        // Last point - simple line
        pathData += ` L ${curr.x},${curr.y}`;
      }
    }
    
    // Determine color based on trend
    const firstPrice = prices[0];
    const lastPrice = prices[prices.length - 1];
    const isPositive = lastPrice >= firstPrice;
    const color = isPositive ? '#10b981' : '#ef4444';
    
    return `
      <svg viewBox="0 0 200 12" preserveAspectRatio="none" style="display: block; width: 100%; height: 100%;">
        <path d="${pathData}" stroke="${color}" stroke-width="1" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
  }

  setupChartPeriodSelector() {
    const selector = document.getElementById('chart-days');
    if (selector) {
      selector.addEventListener('change', (e) => {
        const days = parseInt(e.target.value);
        this.renderMarketTiles(days);
      });
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
                    <img src="assets/logo.png" alt="AIris Logo" class="loading-logo-image">
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

      // Show the main app content now that loading is complete
      const appContainer = document.getElementById("app");
      if (appContainer) {
        appContainer.style.display = "flex";
      }

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

      // Ctrl/Cmd + 1-4: Switch between tabs
      if ((e.ctrlKey || e.metaKey) && e.key >= "1" && e.key <= "4") {
        e.preventDefault();
        const tabs = ["chat", "upload", "files", "settings"];
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
        this.uiComponents.showNotification("Connection restored!", "success");
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

  // Theme management
  loadTheme() {
    const savedTheme = localStorage.getItem("airis-theme") || "light";
    this.currentTheme = savedTheme;
    this.applyTheme();
  }

  applyTheme() {
    // Remove all theme classes
    document.body.classList.remove("dark-theme", "nebula-theme");

    // Apply current theme class
    if (this.currentTheme === "dark") {
      document.body.classList.add("dark-theme");
    } else if (this.currentTheme === "nebula") {
      document.body.classList.add("nebula-theme");
    }

    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      if (this.currentTheme === "light") {
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        themeToggle.setAttribute("title", "Switch to Dark Theme");
      } else if (this.currentTheme === "dark") {
        themeToggle.innerHTML =
          '<i class="fas fa-cloud-moon" style="background: linear-gradient(45deg, #8B5CF6, #EC4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"></i>';
        themeToggle.setAttribute("title", "Switch to Nebula Theme");
      } else if (this.currentTheme === "nebula") {
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        themeToggle.setAttribute("title", "Switch to Light Theme");
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
      theme: this.currentTheme,
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

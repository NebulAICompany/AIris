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

      // Hide loading screen and show app
      this.hideLoadingScreen();

      this.isInitialized = true;
      logger.info("AIris App initialized successfully", "APP");

      // Render market EOD tiles on news tab
      this.renderMarketTiles(30);

    } catch (error) {
      logger.error(`Failed to start app: ${error.message}`, "APP");
      this.showErrorScreen(error);
    }
  }

  async renderMarketTiles(days = 30) {
    try {
      const api = new APIService();
      const symbols = [
        "AEFES.IS", "AKBNK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "CIMSA.IS", 
        "EKGYO.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", 
        "ISCTR.IS", "KCHOL.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", "PETKM.IS", 
        "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TAVHL.IS", "TCELL.IS", 
        "THYAO.IS", "TOASO.IS", "TTKOM.IS", "TUPRS.IS", "ULKER.IS", "YKBNK.IS"
      ];
      const indexSymbols = ["XU030.IS", "XU100.IS"];
      const allSymbols = [...indexSymbols, ...symbols];
      const symbolsString = allSymbols.join(",");

      const container = document.querySelector("#market-eod");
      if (!container) return;

      // Check if we have data for any symbol, if not refresh all at once
      let hasAnyData = false;
      for (const symbol of allSymbols) {
        try {
          const response = await api.getMarketEod(symbol, days);
          if (response.data?.data && response.data.data.length > 0) {
            hasAnyData = true;
            break;
          }
        } catch {}
      }

      // If no data exists, refresh all symbols at once
      if (!hasAnyData) {
        try {
          await api.refreshMarketEod(symbolsString, days);
        } catch (error) {
          console.error("Error refreshing market data:", error);
        }
      }

      // Get the most changed quotes using the new function (excluding indexes)
      let topPerformers = [];
      try {
        const response = await api.getMostChangedQuotes(symbols, days, 8);
        topPerformers = response.data?.data || [];
      } catch (error) {
        console.error("Error fetching most changed quotes:", error);
      }

      // Create tiles array starting with index tiles
      const tiles = [];
      
      // First, create the 2 permanent index tiles
      for (let i = 0; i < 2; i++) {
        const indexSymbol = indexSymbols[i];
        try {
          const response = await api.getMarketEod(indexSymbol, days);
          const data = response.data?.data || [];
          
          if (data.length > 0) {
            const latest = data[0];
            const chartSvg = this.createMiniChart(data);
            
            // Calculate change from first data point (oldest) to latest
            const firstDataPoint = data[data.length - 1]; // Last in array is oldest
            const change = latest.close - firstDataPoint.close;
            const changePercent = firstDataPoint.close !== 0 ? ((change / firstDataPoint.close) * 100) : 0;
            const isPositive = change >= 0;
            const changeColor = isPositive ? "#10b981" : "#ef4444";
            const changeSymbol = isPositive ? "↑" : "↓";

            tiles.push(`
              <div class="market-tile" data-tile-index="${i}">
                <div class="market-tile-header">
                  <div class="market-title">${indexSymbol}</div>
                  <div class="market-change-indicator" style="background-color: ${changeColor + "20"}; color: ${changeColor};">
                    <span class="change-symbol">${changeSymbol}</span>
                    <span class="change-percent">%${Math.abs(changePercent).toFixed(2)}</span>
                  </div>
                </div>
                <div class="market-change-absolute" style="color: ${changeColor};">
                  ${(isPositive ? "+" : "") + change.toFixed(2)}
                </div>
                <div class="market-chart-container">
                  <div class="market-chart">${chartSvg}</div>
                </div>
                <div class="market-price">${latest.close?.toLocaleString("tr-TR")} TRY</div>
              </div>
            `);
          } else {
            // No data for this index
            tiles.push(`
              <div class="market-tile" data-tile-index="${i}">
                <div class="market-tile-header">
                  <div class="market-title">${indexSymbol}</div>
                  <div class="market-change-indicator" style="background-color: #e7e7e920; color: #667085;">
                    <span class="change-symbol">--</span>
                    <span class="change-percent">--</span>
                  </div>
                </div>
                <div class="market-change-absolute" style="color: #667085;">
                  --
                </div>
                <div class="market-chart-container">
                  <div class="market-chart"></div>
                </div>
                <div class="market-price">--</div>
              </div>
            `);
          }
        } catch (error) {
          console.error(`Error fetching data for ${indexSymbol}:`, error);
          // Fallback for index with error
          tiles.push(`
            <div class="market-tile" data-tile-index="${i}">
              <div class="market-tile-header">
                <div class="market-title">${indexSymbol}</div>
                <div class="market-change-indicator" style="background-color: #e7e7e920; color: #667085;">
                  <span class="change-symbol">--</span>
                  <span class="change-percent">--</span>
                </div>
              </div>
              <div class="market-change-absolute" style="color: #667085;">
                --
              </div>
              <div class="market-chart-container">
                <div class="market-chart"></div>
              </div>
              <div class="market-price">--</div>
            </div>
          `);
        }
      }
      
      // Then, create the 8 most changed stock tiles
      for (let i = 0; i < 8; i++) {
        const tileIndex = i + 2; // Start from index 2 (after the 2 index tiles)
        if (i < topPerformers.length) {
          const performer = topPerformers[i];
          const symbol = performer.symbol;
          const data = performer.data;
          const changePercent = performer.change_percent;
          const latest = data?.[0];

          if (latest && data.length > 0) {
            // Create mini chart SVG for this stock
            const chartSvg = this.createMiniChart(data);
            
            // Calculate absolute change from first data point (oldest) to latest
            const firstDataPoint = data[data.length - 1]; // Last in array is oldest
            const change = latest.close - firstDataPoint.close;
            const isPositive = change >= 0;
            const changeColor = isPositive ? "#10b981" : "#ef4444";
            const changeSymbol = isPositive ? "↑" : "↓";

            tiles.push(`
              <div class="market-tile" data-tile-index="${tileIndex}">
                <div class="market-tile-header">
                  <div class="market-title">${symbol}</div>
                  <div class="market-change-indicator" style="background-color: ${changeColor + "20"}; color: ${changeColor};">
                    <span class="change-symbol">${changeSymbol}</span>
                    <span class="change-percent">%${Math.abs(changePercent).toFixed(2)}</span>
                  </div>
                </div>
                <div class="market-change-absolute" style="color: ${changeColor};">
                  ${(isPositive ? "+" : "") + change.toFixed(2)}
                </div>
                <div class="market-chart-container">
                  <div class="market-chart">${chartSvg}</div>
                </div>
                <div class="market-price">${latest.close?.toLocaleString("tr-TR")} TRY</div>
              </div>
            `);
          } else {
            // No data for this stock
            tiles.push(`
              <div class="market-tile" data-tile-index="${tileIndex}">
                <div class="market-tile-header">
                  <div class="market-title">${symbol}</div>
                  <div class="market-change-indicator" style="background-color: #e7e7e920; color: #667085;">
                    <span class="change-symbol">--</span>
                    <span class="change-percent">--</span>
                  </div>
                </div>
                <div class="market-change-absolute" style="color: #667085;">
                  --
                </div>
                <div class="market-chart-container">
                  <div class="market-chart"></div>
                </div>
                <div class="market-price">--</div>
              </div>
            `);
          }
        } else {
          // Fallback for missing performers
          tiles.push(`
            <div class="market-tile" data-tile-index="${tileIndex}">
              <div class="market-tile-header">
                <div class="market-title">--</div>
                <div class="market-change-indicator" style="background-color: #e7e7e920; color: #667085;">
                  <span class="change-symbol">--</span>
                  <span class="change-percent">--</span>
                </div>
              </div>
              <div class="market-change-absolute" style="color: #667085;">
                --
              </div>
              <div class="market-chart-container">
                <div class="market-chart"></div>
              </div>
              <div class="market-price">--</div>
            </div>
          `);
        }
      }

      container.innerHTML = `
        <div class="market-grid">
          ${tiles.join("")}
        </div>
      `;

      // Add event listener for refresh button
      this.setupMarketRefreshButton();
    } catch (e) {
      console.error("Market tiles render error", e);
    }
  }

  setupMarketRefreshButton() {
    const refreshBtn = document.getElementById("refresh-market-data");
    if (refreshBtn) {
      refreshBtn.onclick = async () => {
        const symbols = [
          "AEFES.IS", "AKBNK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "CIMSA.IS", 
          "EKGYO.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", 
          "ISCTR.IS", "KCHOL.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", "PETKM.IS", 
          "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TAVHL.IS", "TCELL.IS", 
          "THYAO.IS", "TOASO.IS", "TTKOM.IS", "TUPRS.IS", "ULKER.IS", "YKBNK.IS"
        ];
        const indexSymbols = ["XU030.IS", "XU100.IS"];
        const allSymbols = [...indexSymbols, ...symbols];
        const symbolsString = allSymbols.join(",");
        
        // Add loading state
        refreshBtn.classList.add("loading");
        refreshBtn.disabled = true;
        
        try {
          const api = new APIService();
          await api.refreshMarketEod(symbolsString, 30);
          
          // Re-render the market tiles with fresh data
          await this.renderMarketTiles(30);
        } catch (error) {
          console.error("Error refreshing market data:", error);
        } finally {
          // Remove loading state
          refreshBtn.classList.remove("loading");
          refreshBtn.disabled = false;
        }
      };
    }
  }


  createMiniChart(data) {
    if (!data || data.length < 2) return "";

    // Sort data by date (oldest first for chart)
    const sortedData = [...data].reverse();
    const prices = sortedData.map((d) => d.close);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;

    // Chart dimensions - responsive width, fixed height
    const width = 200; // This will be overridden by CSS
    const height = 40;
    const padding = 2;

    // Create smooth curve using quadratic bezier curves
    const points = sortedData.map((d, i) => {
      const x = padding + (i / (sortedData.length - 1)) * (width - 2 * padding);
      const y =
        padding + ((maxPrice - d.close) / priceRange) * (height - 2 * padding);
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
    const color = isPositive ? "#10b981" : "#ef4444";

    return `
      <svg viewBox="0 0 200 40" preserveAspectRatio="none" style="display: block; width: 100%; height: 100%;">
        <path d="${pathData}" stroke="${color}" stroke-width="1" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
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
      this.checkBackendConnection();
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

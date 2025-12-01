/**
 * Currency Exchange Service
 * Handles real-time currency data fetching and caching
 * Updated with working APIs as of June 2025
 * 
 * FREE GOLD API SETUP:
 * 2. API Ninjas - Sign up at https://www.api-ninjas.com/ for FREE API key  

 * Replace 'YOUR_FREE_API_KEY' with your actual API keys below.
 */
class CurrencyService {
  constructor() {
    // Updated API endpoints with working services
    this.apiEndpoints = [
      {
        name: "frankfurter.app",
        baseUrl: "https://api.frankfurter.app",
        enabled: true,
        type: "frankfurter",
      },
      {
        name: "exchangerate-api.com",
        baseUrl: "https://api.exchangerate-api.com/v4",
        enabled: true,
        type: "exchangerate-api",
      },
      {
        name: "currencyapi.net",
        baseUrl: "https://api.currencyapi.com/v3",
        enabled: true,
        type: "currencyapi",
      },
    ];

    // Gold price APIs
    this.goldApiEndpoints = [
      {
        name: "GoldAPI Main",
        baseUrl: "https://www.goldapi.io/api",
        enabled: true,
        type: "goldapi",
        apiKey: "***REMOVED***", // Sign up at https://www.api-ninjas.com/
      },
    ];

    this.cache = {
      data: null,
      timestamp: null,
      cacheValidMs: 60000, // 1 minute cache
    };

    this.goldCache = {
      data: null,
      timestamp: null,
      cacheValidMs: 21600000, // 6 hours cache for gold
    };

    this.isRunning = false;
    this.updateInterval = null;
    this.displayInterval = null;
    this.retryCount = 0;
    this.maxRetries = 3;

    // Fallback exchange rates (realistic simulation)
    this.fallbackRates = {
      USD_TRY: 27.85,
      EUR_TRY: 30.42,
      USD_EUR: 0.915,
      goldPrice: 4217.5,
    };

    this.dailyCycleOffset = 0;

    // Conversion constants
    this.OUNCE_TO_GRAM = 31.1034768; // 1 troy ounce = 31.1034768 grams (for gold)

    this.initializeDailyCycle();
  }

  initializeDailyCycle() {
    // Create daily variations based on current date
    const today = new Date();
    const dayOfYear = Math.floor(
      (today - new Date(today.getFullYear(), 0, 0)) / 86400000
    );
    this.dailyCycleOffset = dayOfYear % 100; // Use day of year for consistent daily patterns
  }

  async start() {
    if (this.isRunning) {
      logger.warn("Currency service already running", "CURRENCY");
      return;
    }

    this.isRunning = true;
    logger.info("Starting currency service...", "CURRENCY");

    // Initial fetch
    await this.fetchCurrencyData();

    // Update display immediately after first fetch
    this.updateDisplay();

    // Set up intervals
    this.updateInterval = setInterval(() => {
      this.fetchCurrencyData();
    }, 60000); // Update data every minute

    this.displayInterval = setInterval(() => {
      this.updateDisplay();
    }, 5000); // Update display every 5 seconds

    logger.info("Currency service started successfully", "CURRENCY");
  }

  stop() {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;

    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }

    if (this.displayInterval) {
      clearInterval(this.displayInterval);
      this.displayInterval = null;
    }

    logger.info("Currency service stopped", "CURRENCY");
  }

  async fetchCurrencyData() {
    try {
      // Try each API endpoint
      for (const endpoint of this.apiEndpoints) {
        if (!endpoint.enabled) continue;

        try {
          const data = await this.fetchFromEndpoint(endpoint);
          if (data) {
            this.cache.data = data;
            this.cache.timestamp = Date.now();
            this.retryCount = 0;

            // Re-enable any disabled endpoints on success
            this.enableAllEndpoints();

            logger.info(
              `Currency data fetched successfully from ${endpoint.name}`,
              "CURRENCY"
            );
            return data;
          }
        } catch (error) {
          logger.warn(
            `${endpoint.name} API failed: ${error.message}`,
            "CURRENCY"
          );
          this.disableEndpointTemporarily(endpoint);
          continue;
        }
      }

      // If all APIs failed, throw error
      throw new Error("All currency APIs failed");
    } catch (error) {
      logger.error(
        `Failed to fetch currency data: ${error.message}`,
        "CURRENCY"
      );
      this.retryCount++;

      if (this.retryCount >= this.maxRetries) {
        logger.warn("Max retries reached, using fallback rates", "CURRENCY");
        this.useFallbackRates();
      }
    }
  }

  async fetchFromEndpoint(endpoint) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    try {
      let response;

      switch (endpoint.type) {
        case "frankfurter":
          response = await fetch(
            `${endpoint.baseUrl}/latest?from=USD&to=TRY,EUR`,
            {
              signal: controller.signal,
              headers: {
                Accept: "application/json",
                "Cache-Control": "no-cache",
              },
            }
          );
          break;

        case "exchangerate-api":
          response = await fetch(`${endpoint.baseUrl}/latest/USD`, {
            signal: controller.signal,
            headers: {
              Accept: "application/json",
              "Cache-Control": "no-cache",
            },
          });
          break;

        case "currencyapi":
          // This API might require API key, so it's a fallback
          response = await fetch(
            `${endpoint.baseUrl}/latest?apikey=YOUR_API_KEY&currencies=TRY,EUR&base_currency=USD`,
            {
              signal: controller.signal,
              headers: {
                Accept: "application/json",
                "Cache-Control": "no-cache",
              },
            }
          );
          break;

        default:
          throw new Error(`Unknown endpoint type: ${endpoint.type}`);
      }

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return this.normalizeData(data, endpoint.type);
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        throw new Error("Request timeout");
      }
      throw error;
    }
  }

  normalizeData(data, type) {
    try {
      switch (type) {
        case "frankfurter":
          return {
            USD_TRY: data.rates.TRY,
            EUR_TRY: data.rates.TRY / data.rates.EUR,
            USD_EUR: data.rates.EUR,
            timestamp: new Date(data.date).getTime(),
            isOffline: false,
          };

        case "exchangerate-api":
          return {
            USD_TRY: data.rates.TRY,
            EUR_TRY: data.rates.TRY / data.rates.EUR,
            USD_EUR: data.rates.EUR,
            timestamp: new Date(data.date).getTime(),
            isOffline: false,
          };

        case "currencyapi":
          return {
            USD_TRY: data.data.TRY.value,
            EUR_TRY: data.data.TRY.value / data.data.EUR.value,
            USD_EUR: data.data.EUR.value,
            timestamp: Date.now(),
            isOffline: false,
          };

        default:
          throw new Error(`Unknown data type: ${type}`);
      }
    } catch (error) {
      throw new Error(`Failed to normalize data: ${error.message}`);
    }
  }

  disableEndpointTemporarily(endpoint) {
    endpoint.enabled = false;

    // Re-enable after 5 minutes
    setTimeout(() => {
      endpoint.enabled = true;
      logger.info(`Re-enabled ${endpoint.name} endpoint`, "CURRENCY");
    }, 300000);
  }

  enableAllEndpoints() {
    this.apiEndpoints.forEach((endpoint) => {
      endpoint.enabled = true;
    });
  }

  useFallbackRates() {
    // Generate realistic-looking variations
    const now = new Date();
    const hourOfDay = now.getHours();
    const minuteOfHour = now.getMinutes();

    // Create daily and hourly patterns
    const dailyVariation =
      Math.sin((this.dailyCycleOffset / 100) * 2 * Math.PI) * 0.02;
    const hourlyVariation = Math.sin((hourOfDay / 24) * 2 * Math.PI) * 0.01;
    const randomVariation = (Math.random() - 0.5) * 0.005;

    const totalVariation = dailyVariation + hourlyVariation + randomVariation;

    this.cache.data = {
      USD_TRY: this.fallbackRates.USD_TRY * (1 + totalVariation),
      EUR_TRY: this.fallbackRates.EUR_TRY * (1 + totalVariation * 0.8),
      USD_EUR: this.fallbackRates.USD_EUR * (1 + totalVariation * 0.3),
      timestamp: Date.now(),
      isOffline: true,
    };

    this.cache.timestamp = Date.now();

    logger.warn("Using fallback exchange rates (offline mode)", "CURRENCY");
  }

  async fetchGoldPrice() {
    try {
      // Try each gold API endpoint
      for (const endpoint of this.goldApiEndpoints) {
        if (!endpoint.enabled) continue;

        try {
          const data = await this.fetchGoldFromEndpoint(endpoint);
          if (data) {
            this.goldCache.data = data;
            this.goldCache.timestamp = Date.now();

            logger.info(
              `Gold price fetched successfully from ${endpoint.name}`,
              "CURRENCY"
            );
            return data;
          }
        } catch (error) {
          logger.warn(
            `${endpoint.name} gold API failed: ${error.message}`,
            "CURRENCY"
          );
          this.disableGoldEndpointTemporarily(endpoint);
          continue;
        }
      }

      // If all APIs failed, use simulation
      throw new Error("All gold APIs failed");
    } catch (error) {
      logger.error(`Failed to fetch gold data: ${error.message}`, "CURRENCY");
      this.useSimulatedGoldPrice();
    }
  }

  async fetchGoldFromEndpoint(endpoint) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    try {
      const url = `${endpoint.baseUrl}/XAU/USD`; 
      const headers = {
        Accept: "application/json",
        "Cache-Control": "no-cache",
        "X-Access-Token": endpoint.apiKey,
        "Content-Type": "application/json",
      };

      const response = await fetch(url, {
        signal: controller.signal,
        headers,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return this.normalizeGoldData(data);
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        throw new Error("Request timeout");
      }
      throw error;
    }
  }

  normalizeGoldData(data) {
  try {
    const toNumber = (v) =>
      v === null || v === undefined || v === "" ? null : Number(v);

    const gramUsd = toNumber(data.price_gram_24k);      // USD/gram (24k)
    const ounceUsd =
      toNumber(data.price) ||                         // USD/ounce
      toNumber(data.ask) ||
      (gramUsd ? gramUsd * this.OUNCE_TO_GRAM : null);

    if (!ounceUsd) {
      throw new Error("GoldAPI response missing price");
    }

    return {
      price: ounceUsd,             // <-- ons USD fiyatı
      ounceUsd: ounceUsd,
      gramUsd: gramUsd ?? (ounceUsd / this.OUNCE_TO_GRAM),
      open_price: toNumber(data.open_price),
      low_price: toNumber(data.low_price),
      high_price: toNumber(data.high_price),
      timestamp: data.timestamp || Date.now(),
      currency: data.currency || "USD",
      source: "goldapi",
      isOffline: false,
    };
  } catch (error) {
    throw new Error(`Failed to normalize gold data: ${error.message}`);
  }
}


  disableGoldEndpointTemporarily(endpoint) {
    endpoint.enabled = false;

    // Re-enable after 5 minutes
    setTimeout(() => {
      endpoint.enabled = true;
      logger.info(`Re-enabled ${endpoint.name} gold endpoint`, "CURRENCY");
    }, 300000);
  }

  useSimulatedGoldPrice() {
    // Fallback to simulated gold price with realistic variations
    const now = new Date();
    const hourOfDay = now.getHours();

    // Gold market patterns (higher volatility during US trading hours)
    const marketHoursMultiplier = hourOfDay >= 9 && hourOfDay <= 16 ? 1.5 : 1.0;
    const dailyVariation =
      Math.sin((this.dailyCycleOffset / 100) * 2 * Math.PI) *
      0.015 *
      marketHoursMultiplier;
    const randomVariation =
      (Math.random() - 0.5) * 0.01 * marketHoursMultiplier;

    const goldPrice =
      this.fallbackRates.goldPrice * (1 + dailyVariation + randomVariation);

    this.goldCache.data = {
      price: goldPrice,
      ounceUsd: goldPrice,
      gramUsd: goldPrice / this.OUNCE_TO_GRAM,
      currency: "USD",
      unit: "oz",
      timestamp: Date.now(),
      isOffline: true,
      source: "simulated",
    };

    this.goldCache.timestamp = Date.now();

    logger.warn("Using fallback gold price (offline mode)", "CURRENCY");
  }

  async getData() {
    // Check if cache is valid
    if (
      this.cache.data &&
      this.cache.timestamp &&
      Date.now() - this.cache.timestamp < this.cache.cacheValidMs
    ) {
      return this.cache.data;
    }

    // If no valid cache, try to fetch new data
    if (!this.cache.data) {
      await this.fetchCurrencyData();
    }

    return this.cache.data;
  }

  async getGoldData() {
    // Check if gold cache is valid
    if (
      this.goldCache.data &&
      this.goldCache.timestamp &&
      Date.now() - this.goldCache.timestamp < this.goldCache.cacheValidMs
    ) {
      return this.goldCache.data;
    }

    // If no valid cache, fetch new data
    await this.fetchGoldPrice();
    return this.goldCache.data;
  }

  /**
   * Calculate gold price in TRY per gram
   * @param {Object} currencyData - Currency exchange rates
   * @param {Object} goldData - Gold price data in USD per ounce
   * @returns {Object} Gold price in TRY per gram
   */
  calculateGoldPriceInTRYPerGram(currencyData, goldData) {
    if (!currencyData || !goldData || !currencyData.USD_TRY) {
      return {
        price: null,
        currency: "TRY",
        unit: "g",
        timestamp: Date.now(),
        isOffline: currencyData?.isOffline || goldData?.isOffline || false,
      };
    }

    const ouncePrice =
      goldData.price ??
      goldData.ounceUsd ??
      (goldData.gramUsd ? goldData.gramUsd * this.OUNCE_TO_GRAM : null);

    if (!ouncePrice) {
      return {
        price: null,
        currency: "TRY",
        unit: "g",
        timestamp: Date.now(),
        isOffline: currencyData?.isOffline || goldData?.isOffline || false,
      };
    }

    // Convert USD per ounce to TRY per gram
    // Formula: (USD/oz) * (TRY/USD) / (g/oz) = TRY/g
    const priceInTRYPerGram =
      (ouncePrice * currencyData.USD_TRY) / this.OUNCE_TO_GRAM;

    return {
      price: priceInTRYPerGram,
      currency: "TRY",
      unit: "g",
      timestamp: Date.now(),
      isOffline: currencyData.isOffline || goldData.isOffline,
    };
  }

  updateDisplay() {
    const currencyTicker = document.getElementById("currency-ticker");
    if (!currencyTicker) return;

    Promise.all([this.getData(), this.getGoldData()])
      .then(([currencyData, goldData]) => {
        if (!currencyData) return;

        const isOffline = currencyData.isOffline || goldData?.isOffline;
        const status = isOffline
          ? window.languageService?.get("offline") || "Offline"
          : window.languageService?.get("live") || "Live";
        const statusClass = isOffline ? "status-offline" : "status-live";

        // Calculate gold price in TRY per gram
        const goldTRYPerGram = this.calculateGoldPriceInTRYPerGram(
          currencyData,
          goldData
        );

        // Update individual currency values instead of replacing entire HTML
        const usdTryElement = document.getElementById("usd-try");
        const eurTryElement = document.getElementById("eur-try");
        const usdEurElement = document.getElementById("usd-eur");
        const goldUsdElement = document.getElementById("gold-usd");
        const goldTryElement = document.getElementById("gold-try");
        const statusElement = document.getElementById("currency-status");

        if (usdTryElement) {
          usdTryElement.textContent = currencyData.USD_TRY?.toFixed(4) || "N/A";
        }
        if (eurTryElement) {
          eurTryElement.textContent = currencyData.EUR_TRY?.toFixed(4) || "N/A";
        }
        if (usdEurElement) {
          usdEurElement.textContent = currencyData.USD_EUR?.toFixed(4) || "N/A";
        }
        const ouncePrice = goldData
          ? goldData.price ??
            goldData.ounceUsd ??
            (goldData.gramUsd
              ? goldData.gramUsd * this.OUNCE_TO_GRAM
              : null)
          : null;

        if (goldUsdElement) {
          goldUsdElement.textContent = ouncePrice
            ? `$${ouncePrice.toFixed(2)}`
            : "N/A";
        }
        if (goldTryElement) {
          goldTryElement.textContent = `₺${
            goldTRYPerGram?.price?.toFixed(2) || "N/A"
          }`;
        }
        if (statusElement) {
          statusElement.className = `currency-status ${statusClass}`;
          const statusText = statusElement.querySelector(".status-text");
          if (statusText) {
            statusText.textContent = status;
          }
        }

        // Note: Not calling updatePageTexts() here to avoid overriding status text
      })
      .catch((error) => {
        logger.error(
          `Failed to update currency display: ${error.message}`,
          "CURRENCY"
        );
      });
  }

  // Public API
  isDataAvailable() {
    return this.cache.data !== null;
  }

  getLastUpdateTime() {
    return this.cache.timestamp;
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      lastUpdate: this.cache.timestamp,
      isOffline: this.cache.data?.isOffline || false,
      enabledApis: this.apiEndpoints.filter((api) => api.enabled).length,
      totalApis: this.apiEndpoints.length,
    };
  }
}

// Export the service
window.CurrencyService = CurrencyService;

// API Service for Backend Communication via IPC

class APIService {
  constructor() {
    this.isElectron = typeof window.airisAPI !== "undefined";
    this.baseURL = "http://localhost:8001";
    this.timeout = 600000; // 10 minutes timeout

    // Always set up axios for API calls, regardless of environment
    this.setupAxios();

    if (!this.isElectron) {
      console.warn("Running in browser mode - some features may not work");
    }
  }

  setupAxios() {
    // Set up fetch-based API client
    this.api = {
      get: async (url, config = {}) => {
        return this.makeRequest(url, "GET", null, config);
      },
      post: async (url, data, config = {}) => {
        return this.makeRequest(url, "POST", data, config);
      },
      delete: async (url, config = {}) => {
        return this.makeRequest(url, "DELETE", null, config);
      },
      put: async (url, data, config = {}) => {
        return this.makeRequest(url, "PUT", data, config);
      },
      patch: async (url, data, config = {}) => {
        return this.makeRequest(url, "PATCH", data, config);
      },
      defaults: {
        baseURL: this.baseURL,
        timeout: this.timeout,
      },
    };
  }

  async makeRequest(url, method = "GET", data = null, config = {}) {
    let fullUrl = url.startsWith("http") ? url : `${this.baseURL}${url}`;

    // Handle query parameters
    if (config.params) {
      const urlObj = new URL(fullUrl);
      Object.keys(config.params).forEach((key) => {
        urlObj.searchParams.set(key, config.params[key]);
      });
      fullUrl = urlObj.toString();
    }

    console.log(`[API] ${method.toUpperCase()} ${fullUrl}`);

    // Create abort controller for manual timeout management
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, config.timeout || this.timeout);

    const requestOptions = {
      method,
      headers: {
        "Content-Type": "application/json",
        ...config.headers,
      },
      signal: controller.signal,
    };

    if (data) {
      if (data instanceof FormData) {
        // Remove Content-Type header for FormData (browser will set it with boundary)
        delete requestOptions.headers["Content-Type"];
        requestOptions.body = data;
      } else {
        requestOptions.body = JSON.stringify(data);
      }
    }

    try {
      const response = await fetch(fullUrl, requestOptions);
      clearTimeout(timeoutId); // Clear timeout on successful response

      console.log(`[API] Response: ${response.status} ${fullUrl}`);

      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage;

        try {
          const parsed = JSON.parse(errorData);
          errorMessage =
            parsed.message || parsed.detail || `HTTP ${response.status}`;
        } catch {
          errorMessage = errorData || `HTTP ${response.status}`;
        }

        if (response.status >= 500) {
          throw new Error(`Server error (${response.status}): ${errorMessage}`);
        } else if (response.status >= 400) {
          throw new Error(`Client error (${response.status}): ${errorMessage}`);
        }
      }

      const responseData = await response.json();
      return {
        data: responseData,
        status: response.status,
        config: { url: fullUrl },
      };
    } catch (error) {
      clearTimeout(timeoutId); // Clear timeout on error
      console.error("[API] Request error:", error);

      if (error.name === "AbortError") {
        throw new Error("İstek zaman aşımına uğradı - lütfen tekrar deneyin");
      }

      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(
          "Sunucuya bağlanılamıyor. Lütfen backend'in çalıştığından emin olun."
        );
      }

      throw error;
    }
  }

  // Update configuration
  updateConfig(config) {
    if (config.baseURL) {
      this.baseURL = config.baseURL;
      this.api.defaults.baseURL = config.baseURL;
    }

    if (config.timeout) {
      this.timeout = config.timeout;
      this.api.defaults.timeout = config.timeout;
    }
  }

  // Test connection to backend
  async testConnection() {
    try {
      const response = await this.api.get("/health");
      return {
        success: true,
        status: "online",
        latency: Date.now() - performance.now(),
      };
    } catch (error) {
      return {
        success: false,
        status: "offline",
        error: error.message,
      };
    }
  }
  // Send query to AI system
  async sendQuery(
    query,
    webSearchEnabled = false,
    useSpdrag = false,
    sessionId = null,
    selectedFiles = null
  ) {
    try {
      // Determine timeout based on enabled features
      let timeout = 600000; // Base timeout: 10 minutes
      if (webSearchEnabled) timeout += 60000; // Add 1 minute for web search
      // RAG Fusion disabled - no timeout adjustment needed

      console.log(
        `[API] AI Query timeout set to: ${timeout / 1000
        }s (Web: ${webSearchEnabled}, RAG Fusion: disabled)`
      );

      const response = await this.api.post(
        "/api/query",
        {
          query: query.trim(),
          webSearchEnabled: webSearchEnabled,
          useSpdrag: useSpdrag,
          sessionId: sessionId,
          selectedFiles: selectedFiles,
        },
        {
          timeout: timeout, // Dynamic timeout based on features
        }
      );

      return {
        success: true,
        data: response.data,
        response: response.data.response || response.data,
        images: response.data.images || [],
        charts: response.data.charts || [],
        sessionId: response.data.sessionId,
      };
    } catch (error) {
      console.error("Query API error:", error);

      let errorMessage = "Beklenmeyen bir hata oluştu";

      if (
        error.name === "AbortError" ||
        error.message.includes("timeout") ||
        error.message.includes("zaman aşımı")
      ) {
        let timeoutReason = "AI sorgusu";
        if (webSearchEnabled) {
          timeoutReason = "web araması ile AI sorgusu";
        }

        errorMessage = `${timeoutReason} tamamlanması çok uzun sürdü. Lütfen daha kısa bir soru deneyin veya birkaç saniye bekleyip tekrar deneyin.`;
      } else if (
        error.message.includes("fetch") ||
        error.message.includes("bağlan")
      ) {
        errorMessage =
          "AI servisine bağlanılamıyor. Lütfen bağlantınızı kontrol edin ve tekrar deneyin.";
      } else if (error.message.includes("500")) {
        errorMessage =
          "AI servisi geçici olarak kullanılamıyor. Lütfen birkaç dakika sonra tekrar deneyin.";
      } else if (
        error.message.includes("502") ||
        error.message.includes("503")
      ) {
        errorMessage =
          "Backend servisi şu anda meşgul. Lütfen birkaç saniye bekleyin ve tekrar deneyin.";
      } else {
        errorMessage = error.message;
      }

      return {
        success: false,
        error: errorMessage,
        images: [], // Error durumunda empty images array
        charts: [], // Error durumunda empty charts array
      };
    }
  }

  // Send streaming query to AI system using Server-Sent Events
  // callbacks may include: onToken, onToolStart, onToolEnd, onDone, onError
  async sendQueryStream(
    query,
    webSearchEnabled = false,
    useSpdrag = false,
    sessionId = null,
    selectedFiles = null,
    callbacks = {}
  ) {
    const { onToken, onToolStart, onToolEnd, onDone, onError, onSpdragDocStart, onSpdragDocEnd, onSpdragSynthesisStart } = callbacks;

    const fetchOptions = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: query.trim(),
        webSearchEnabled: webSearchEnabled,
        useSpdrag: useSpdrag,
        sessionId: sessionId,
        selectedFiles: selectedFiles,
      }),
    };

    try {
      const response = await fetch(`${this.baseURL}/api/query/stream`, fetchOptions);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              switch (data.type) {
                case "token":
                  if (onToken) onToken(data.content);
                  break;
                case "tool_start":
                  if (onToolStart) onToolStart(data.tool_name, data.parent_agent, data.query);
                  break;
                case "tool_end":
                  if (onToolEnd) onToolEnd(data.tool_name, data.parent_agent);
                  break;
                case "done":
                  if (onDone) {
                    onDone({
                      content: data.content ?? null,
                      images: data.images || [],
                      charts: data.charts || [],
                      generatedFiles: data.generatedFiles || [],
                      sources: data.sources || [],
                    });
                  }
                  break;
                case "spdrag_doc_start":
                  if (onSpdragDocStart) onSpdragDocStart(data.document);
                  break;
                case "spdrag_doc_end":
                  if (onSpdragDocEnd) onSpdragDocEnd(data.document);
                  break;
                case "spdrag_synthesis_start":
                  if (onSpdragSynthesisStart) onSpdragSynthesisStart();
                  break;
                case "error":
                  if (onError) onError(data.content);
                  break;
              }
            } catch (parseError) {
              console.warn("[API] Failed to parse SSE data:", line, parseError);
            }
          }
        }
      }

      return { success: true };
    } catch (error) {
      console.error("[API] Streaming query error:", error);

      let errorMessage = "Beklenmeyen bir hata oluştu";

      if (error.message.includes("fetch") || error.message.includes("bağlan")) {
        errorMessage =
          "AI servisine bağlanılamıyor. Lütfen bağlantınızı kontrol edin ve tekrar deneyin.";
      } else if (error.message.includes("500")) {
        errorMessage =
          "AI servisi geçici olarak kullanılamıyor. Lütfen birkaç dakika sonra tekrar deneyin.";
      } else {
        errorMessage = error.message;
      }

      if (onError) onError(errorMessage);

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Chat Session Management
  async createChatSession() {
    try {
      const response = await this.api.post("/api/chat/sessions");
      return {
        success: true,
        sessionId: response.data.session_id,
        createdAt: response.data.created_at,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async getChatSession(sessionId) {
    try {
      const response = await this.api.get(`/api/chat/sessions/${sessionId}`);
      return {
        success: true,
        session: response.data.session,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async listChatSessions() {
    try {
      const response = await this.api.get("/api/chat/sessions");
      return {
        success: true,
        sessions: response.data.sessions,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        sessions: [],
      };
    }
  }

  async deleteChatSession(sessionId) {
    try {
      const response = await this.api.delete(`/api/chat/sessions/${sessionId}`);
      return {
        success: true,
        message: response.data.message,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async updateChatSession(sessionId, title) {
    try {
      const response = await this.api.put(`/api/chat/sessions/${sessionId}`, {
        title: title,
      });
      return {
        success: true,
        session: response.data.session,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  // Upload file to backend with progress tracking
  async uploadFile(file, options = {}, progressCallback) {
    return new Promise((resolve, reject) => {
      try {
        const formData = new FormData();
        formData.append("file", file);

        if (options && options.photoLessMode !== undefined) {
          formData.append(
            "photoLessMode",
            options.photoLessMode ? "true" : "false"
          );
        }

        // Use XMLHttpRequest for progress tracking
        const xhr = new XMLHttpRequest();
        const baseURL = this.api.defaults.baseURL || "http://localhost:8001";

        // Set up progress tracking
        if (progressCallback) {
          xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
              const percentComplete = Math.round((e.loaded / e.total) * 100);
              progressCallback(percentComplete);
            } else {
              // Indeterminate progress
              progressCallback(null);
            }
          });
        }

        // Handle successful upload
        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              if (progressCallback) {
                progressCallback(100);
              }
              resolve({
                success: true,
                data: response,
                message: response.message || "File uploaded successfully",
              });
            } catch (error) {
              reject(new Error("Invalid response format"));
            }
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        });

        // Handle upload error
        xhr.addEventListener("error", () => {
          reject(new Error("Upload failed"));
        });

        // Handle upload abort
        xhr.addEventListener("abort", () => {
          reject(new Error("Upload aborted"));
        });

        // Start upload
        xhr.open("POST", `${baseURL}/api/upload`);

        // Set timeout
        xhr.timeout = 180000; // 3 minutes

        xhr.addEventListener("timeout", () => {
          reject(new Error("Upload timeout"));
        });

        // Send request
        xhr.send(formData);
      } catch (error) {
        reject(error);
      }
    });
  }

  async uploadBalanceDocument(file, options = {}, progressCallback) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      if (options && options.photoLessMode !== undefined) {
        formData.append(
          "photoLessMode",
          options.photoLessMode ? "true" : "false"
        );
      }

      const config = {
        timeout: 180000,
      };

      if (progressCallback) {
        progressCallback(0);
      }

      const response = await this.api.post(
        "/api/balance-of-payments/upload",
        formData,
        config
      );

      if (progressCallback) {
        progressCallback(100);
      }

      return {
        success: true,
        data: response.data,
        message:
          response.data.message || "Balance document uploaded successfully",
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  // Get uploaded files list
  async getFiles() {
    try {
      const response = await this.api.get("/api/files");
      return {
        success: true,
        files: response.data.files || [],
      };
    } catch (error) {
      console.error("Error fetching files:", error);
      return {
        success: false,
        error: error.message,
        files: [],
      };
    }
  }

  // Get created documents list
  async getCreatedDocuments() {
    try {
      const response = await this.api.get("/api/created-documents");
      return {
        success: true,
        files: response.data.files || [],
      };
    } catch (error) {
      console.error("Error fetching created documents:", error);
      return {
        success: false,
        error: error.message,
        files: [],
      };
    }
  }

  async getBalanceCalendar(months = 3, endDate = null) {
    try {
      const params = { months };
      if (endDate) {
        params.endDate = endDate;
      }

      const response = await this.api.get(
        "/api/balance-of-payments/calendar",
        { params }
      );

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      console.error("Error fetching balance calendar:", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async processBalanceWorkbook(fileName, replaceExisting = true) {
    try {
      const response = await this.api.post(
        "/api/balance-of-payments/process",
        {
          fileName,
          replaceExisting,
        },
        {
          timeout: 300000,
        }
      );

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      console.error("Error processing balance workbook:", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async getBalanceTransactions(date) {
    try {
      const response = await this.api.get(
        `/api/balance-of-payments/transactions/${date}`
      );
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      console.error("Error fetching balance transactions:", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async getBalanceCategoryTotals() {
    try {
      const response = await this.api.get(
        "/api/balance-of-payments/category-totals"
      );
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      console.error("Error fetching balance category totals:", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async getBalanceCategoryNetValues() {
    try {
      const response = await this.api.get(
        "/api/balance-of-payments/category-net-values"
      );
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      console.error("Error fetching balance category net values:", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  // Batch operations
  async batchUpload(files, progressCallback) {
    const results = [];
    let completed = 0;

    for (const file of files) {
      try {
        const result = await this.uploadFile(file, (fileProgress) => {
          if (progressCallback) {
            const totalProgress = Math.round(
              ((completed + fileProgress / 100) / files.length) * 100
            );
            progressCallback(totalProgress, file.name);
          }
        });

        results.push({
          file: file.name,
          ...result,
        });

        completed++;

        if (progressCallback) {
          progressCallback(
            Math.round((completed / files.length) * 100),
            file.name
          );
        }
      } catch (error) {
        results.push({
          file: file.name,
          success: false,
          error: error.message,
        });
        completed++;
      }
    }

    return {
      success: true,
      results,
      summary: {
        total: files.length,
        successful: results.filter((r) => r.success).length,
        failed: results.filter((r) => !r.success).length,
      },
    };
  }

  // Health check with detailed status
  async healthCheck() {
    const startTime = performance.now();

    try {
      const response = await this.testConnection();
      const endTime = performance.now();

      if (response.success) {
        return {
          status: "online",
          latency: Math.round(endTime - startTime),
          timestamp: new Date().toISOString(),
          version: "unknown", // Could be extracted from response headers
        };
      } else {
        return {
          status: "offline",
          error: response.error,
          timestamp: new Date().toISOString(),
        };
      }
    } catch (error) {
      return {
        status: "error",
        error: error.message,
        timestamp: new Date().toISOString(),
      };
    }
  }

  // Health check endpoint
  async checkHealth() {
    try {
      const response = await this.makeRequest("/health", "GET");
      return {
        status: "healthy",
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      throw new Error(`Health check failed: ${error.message}`);
    }
  }

  // Get finance news
  async getFinanceNews(forceRefresh = false) {
    try {
      // Use much longer timeout for finance news (5 minutes) since we now do comprehensive AI summarization
      const params = forceRefresh ? { force_refresh: true } : {};
      const response = await this.api.get("/api/finance-news", {
        timeout: 300000,
        params: params,
      });

      return {
        success: response.data.status === "success",
        data: response.data,
        articles: response.data.articles || [],
        lastUpdated: response.data.last_updated,
        totalClusters: response.data.total_clusters || 0,
        totalArticles: response.data.total_articles || 0,
        sourcesCount: response.data.sources_count || 0,
        feature: response.data.feature || "single_source",
      };
    } catch (error) {
      console.error("[API] Finance news error:", error);
      return {
        success: false,
        error: error.message.includes("aborted")
          ? "İstek zaman aşımına uğradı - lütfen tekrar deneyın"
          : error.message,
        articles: [],
      };
    }
  }

  async getMarketEod(symbol = "TUPRS.IS", limit = 7) {
    console.log(`[API] Getting market EOD for ${symbol} with limit ${limit}`);
    return this.makeRequest(`/api/market/eod`, "GET", null, {
      params: { symbol, limit },
    });
  }

  async refreshMarketEod(symbols = "TUPRS.IS", limit = 7) {
    console.log(`[API] Refreshing market EOD`);
    return this.makeRequest(`/api/market/eod/refresh`, "POST", null, {
      params: { symbols, limit },
    });
  }

  async getMostChangedQuotes(symbols, limit = 30, chart_num = 8) {
    console.log(
      `[API] Getting most changed quotes for ${symbols.length} symbols`
    );
    return this.makeRequest(`/api/market/most-changed`, "POST", {
      symbols,
      limit,
      chart_num,
    });
  }

  async getGainersLosersActive(symbols, limit = 30, chart_num = 8) {
    console.log(
      `[API] Getting gainers/losers/active for ${symbols.length} symbols`
    );
    return this.makeRequest(`/api/market/gainers-losers-active`, "POST", {
      symbols,
      limit,
      chart_num,
    });
  }

  async getCompanyInfo(symbol = "TUPRS.IS") {
    console.log(`[API] Getting company info for ${symbol}`);
    return this.makeRequest(`/api/market/company-info`, "GET", null, {
      params: { symbol },
    });
  }

  async searchSymbols(query = "") {
    const response = await this.makeRequest(
      `/api/market/search-symbols`,
      "GET",
      null,
      { params: { query } }
    );
    console.log(
      `[API] Searching symbols for ${query} response:`,
      response.data
    );
    return response.data;
  }

  // News Chat API method
  async sendNewsChatQuery(message, newsContext) {
    try {
      const response = await this.api.post(
        "/api/news-chat",
        {
          query: message,
          news_context: newsContext,
          web_search_enabled: true,
        },
        {
          timeout: 120000, // 2 minutes timeout for news chat
        }
      );

      return {
        success: response.data.status === "success",
        response: response.data.response,
        images: response.data.images || [],
        sessionId: response.data.sessionId,
      };
    } catch (error) {
      console.error("[API] News chat error:", error);
      return {
        success: false,
        error: error.message.includes("aborted")
          ? "Request timed out - please try again"
          : error.message,
        response: null,
      };
    }
  }

  // Dev tools (handled by main process)
  openDevTools() {
    if (window.airisAPI && window.airisAPI.openDevTools) {
      window.airisAPI.openDevTools();
    } else {
      console.warn("Dev tools not available");
    }
  }
}

// Create global API service instance
window.apiService = new APIService();

// API Service for Backend Communication via IPC

class APIService {
  constructor() {
    this.isElectron = typeof window.airisAPI !== "undefined";
    this.baseURL = "http://localhost:8000";
    this.timeout = 45000; // Increased from 30s to 45s

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
      defaults: {
        baseURL: this.baseURL,
        timeout: this.timeout,
      },
    };
  }

  async makeRequest(url, method = "GET", data = null, config = {}) {
    const fullUrl = url.startsWith("http") ? url : `${this.baseURL}${url}`;

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
    wolframEnabled = false,
    ragFusionEnabled = false,
    sessionId = null,
    selectedFiles = null
  ) {
    try {
      // Determine timeout based on enabled features
      let timeout = 90000; // Base timeout: 90 seconds
      if (webSearchEnabled) timeout += 30000; // Add 30s for web search
      if (wolframEnabled) timeout += 30000; // Add 30s for Wolfram
      // RAG Fusion disabled - no timeout adjustment needed

      console.log(
        `[API] AI Query timeout set to: ${
          timeout / 1000
        }s (Web: ${webSearchEnabled}, Wolfram: ${wolframEnabled}, RAG Fusion: disabled)`
      );

      const response = await this.api.post(
        "/api/query",
        {
          query: query.trim(),
          webSearchEnabled: webSearchEnabled,
          wolframEnabled: wolframEnabled,
          ragFusionEnabled: false, // Hardcoded to false
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
        if (webSearchEnabled && wolframEnabled) {
          timeoutReason =
            "web araması ve Wolfram Alpha ile karmaşık AI sorgusu";
        } else if (webSearchEnabled) {
          timeoutReason = "web araması ile AI sorgusu";
        } else if (wolframEnabled) {
          timeoutReason = "Wolfram Alpha ile AI sorgusu";
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

  // Upload file to backend
  async uploadFile(file, progressCallback) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const config = {
        timeout: 180000, // 3 minutes for file uploads (increased for larger files)
      };

      // Note: Fetch API doesn't support upload progress natively
      // For now, we'll call the progress callback with indeterminate progress
      if (progressCallback) {
        progressCallback(0);
      }

      const response = await this.api.post("/api/upload", formData, config);

      if (progressCallback) {
        progressCallback(100);
      }

      return {
        success: true,
        data: response.data,
        message: response.data.message || "File uploaded successfully",
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

  // Get system metrics (Prometheus endpoint)
  async getMetrics() {
    try {
      // Make a special request for metrics that expects plain text, not JSON
      const fullUrl = `${this.baseURL}/`;
      const response = await fetch(fullUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const metricsText = await response.text(); // Get as plain text, not JSON

      // Parse Prometheus metrics format
      const metrics = this.parsePrometheusMetrics(metricsText);

      return {
        success: true,
        metrics,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        metrics: {},
      };
    }
  }

  // Parse Prometheus metrics format
  parsePrometheusMetrics(metricsText) {
    const metrics = {};
    const lines = metricsText.split("\n");

    for (const line of lines) {
      if (line.startsWith("#") || !line.trim()) continue;

      const match = line.match(
        /^([a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^}]*\})?) (.+)$/
      );
      if (match) {
        const [, metricName, value] = match;
        const cleanName = metricName.split("{")[0];

        if (!metrics[cleanName]) {
          metrics[cleanName] = [];
        }

        metrics[cleanName].push({
          name: metricName,
          value: parseFloat(value) || value,
        });
      }
    }

    return metrics;
  }

  // Get aggregated system stats from the proper analytics endpoint
  async getSystemStats() {
    try {
      const response = await this.api.get("/api/metrics");

      const data = response.data;

      // Map the backend response to frontend expected format
      const stats = {
        apiRequests: data.totalQueries || 0,
        averageResponseTime: data.avgResponseTime || "0ms",
        documentsProcessed: data.totalDocuments || 0,
        systemHealth:
          data.systemHealth === "Healthy"
            ? "healthy"
            : data.systemHealth === "No Data"
            ? "idle"
            : "offline",
        recentActivity: data.recentActivity || [],
      };

      return {
        success: true,
        stats,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        stats: {
          apiRequests: 0,
          averageResponseTime: "0ms",
          documentsProcessed: 0,
          systemHealth: "offline",
          recentActivity: [],
        },
      };
    }
  }

  // Determine system health based on metrics
  determineSystemHealth(metrics) {
    // Simple health check based on available metrics
    if (!metrics || Object.keys(metrics).length === 0) {
      return "offline";
    }

    // Check for recent activity
    const hasRecentActivity =
      metrics.api_requests_total &&
      metrics.api_requests_total.some((m) => m.value > 0);

    if (hasRecentActivity) {
      return "healthy";
    }

    return "idle";
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
  async getFinanceNews() {
    try {
      const response = await this.api.get("/api/finance-news");

      return {
        success: response.data.status === "success",
        data: response.data,
        articles: response.data.articles || [],
        lastUpdated: response.data.last_updated,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        articles: [],
      };
    }
  }

  // Document Verification API methods
  async getVerificationTypes() {
    try {
      const response = await this.api.get("/api/verification-types");
      return {
        success: true,
        data: response.data,
        verificationTypes: response.data.verification_types || {},
        supportedFormats: response.data.supported_formats || [],
        defaultType: response.data.default_type || "auto"
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        verificationTypes: {},
        supportedFormats: [],
        defaultType: "auto"
      };
    }
  }

  async verifyDocument(file, verificationType = "auto", wolframEnabled = false, progressCallback) {
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("verification_type", verificationType);
      formData.append("wolfram_enabled", wolframEnabled);

      const config = {
        timeout: 120000, // 2 minutes for document verification
      };

      // Call progress callback for start
      if (progressCallback) {
        progressCallback(0, "Starting verification...");
      }

      const response = await this.api.post("/api/verify", formData, config);

      // Call progress callback for completion
      if (progressCallback) {
        progressCallback(100, "Verification completed");
      }

      return {
        success: true,
        data: response.data,
        verificationResult: response.data,
        status: response.data.status,
        confidenceScore: response.data.confidence_score || 0,
        stages: response.data.stages || {},
        warnings: response.data.warnings || [],
        errors: response.data.errors || []
      };
    } catch (error) {
      console.error("Document verification API error:", error);

      let errorMessage = "Document verification failed";

      if (error.name === "AbortError" || error.message.includes("timeout")) {
        errorMessage = "Verification took too long to complete. Please try with a smaller file or try again.";
      } else if (error.message.includes("fetch")) {
        errorMessage = "Unable to connect to the verification service. Please check your connection.";
      } else if (error.message.includes("500")) {
        errorMessage = "The verification service is temporarily unavailable. Please try again.";
      } else if (error.message.includes("400")) {
        errorMessage = "Invalid file format or request. Please check the file and try again.";
      } else {
        errorMessage = error.message;
      }

      return {
        success: false,
        error: errorMessage,
        verificationResult: null,
        status: "error"
      };
    }
  }

  // Batch document verification
  async batchVerifyDocuments(files, verificationType = "auto", wolframEnabled = false, progressCallback) {
    const results = [];
    let completed = 0;

    for (const file of files) {
      try {
        const result = await this.verifyDocument(file, verificationType, wolframEnabled, (fileProgress, status) => {
          if (progressCallback) {
            const totalProgress = Math.round(
              ((completed + fileProgress / 100) / files.length) * 100
            );
            progressCallback(totalProgress, file.name, status);
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
            file.name,
            "Completed"
          );
        }
      } catch (error) {
        results.push({
          file: file.name,
          success: false,
          error: error.message,
          status: "error"
        });
        completed++;
      }
    }

    return {
      success: true,
      results,
      summary: {
        total: files.length,
        verified: results.filter((r) => r.success && r.status === "verified").length,
        rejected: results.filter((r) => r.success && r.status === "rejected").length,
        reviewRequired: results.filter((r) => r.success && r.status === "review_required").length,
        failed: results.filter((r) => !r.success).length,
      },
    };
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

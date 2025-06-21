// API Service for Backend Communication via IPC

class APIService {
  constructor() {
    this.isElectron = typeof window.airisAPI !== "undefined";
    this.baseURL = "http://localhost:8000";
    this.timeout = 30000;

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
        return this.makeRequest(url, 'GET', null, config);
      },
      post: async (url, data, config = {}) => {
        return this.makeRequest(url, 'POST', data, config);
      },
      defaults: {
        baseURL: this.baseURL,
        timeout: this.timeout
      }
    };
  }

  async makeRequest(url, method = 'GET', data = null, config = {}) {
    const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
    
    console.log(`[API] ${method.toUpperCase()} ${fullUrl}`);

    const requestOptions = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...config.headers
      },
      signal: AbortSignal.timeout(config.timeout || this.timeout)
    };

    if (data) {
      if (data instanceof FormData) {
        // Remove Content-Type header for FormData (browser will set it with boundary)
        delete requestOptions.headers['Content-Type'];
        requestOptions.body = data;
      } else {
        requestOptions.body = JSON.stringify(data);
      }
    }

    try {
      const response = await fetch(fullUrl, requestOptions);
      
      console.log(`[API] Response: ${response.status} ${fullUrl}`);

      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage;
        
        try {
          const parsed = JSON.parse(errorData);
          errorMessage = parsed.message || parsed.detail || `HTTP ${response.status}`;
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
      return { data: responseData, status: response.status, config: { url: fullUrl } };
    } catch (error) {
      console.error("[API] Request error:", error);
      
      if (error.name === 'AbortError') {
        throw new Error("Request timeout - please try again");
      }
      
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error("Unable to connect to server. Please check if the backend is running.");
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
      const response = await this.api.get("/");
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
  async sendQuery(query, webSearchEnabled = false, wolframEnabled = false) {
    try {
      const response = await this.api.post("/api/query", {
        query: query.trim(),
        webSearchEnabled: webSearchEnabled,
        wolframEnabled: wolframEnabled,
      });

      return {
        success: true,
        data: response.data,
        response: response.data.response || response.data,
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
        timeout: 120000, // 2 minutes for file uploads
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

  // Get system metrics (Prometheus endpoint)
  async getMetrics() {
    try {
      const response = await this.api.get("/");

      // Parse Prometheus metrics format
      const metrics = this.parsePrometheusMetrics(response.data);

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

  // Get aggregated system stats
  async getSystemStats() {
    try {
      const { metrics } = await this.getMetrics();

      const stats = {
        apiRequests: 0,
        averageResponseTime: 0,
        documentsProcessed: 0,
        systemHealth: "unknown",
      };

      // Extract API requests total
      if (metrics.api_requests_total) {
        stats.apiRequests = metrics.api_requests_total.reduce(
          (sum, metric) => sum + metric.value,
          0
        );
      }

      // Extract LLM response times
      if (metrics.llm_duration_seconds) {
        const responseTimes = metrics.llm_duration_seconds.map(
          (m) => m.value * 1000
        );
        stats.averageResponseTime =
          responseTimes.length > 0
            ? Math.round(
                responseTimes.reduce((a, b) => a + b) / responseTimes.length
              )
            : 0;
      }

      // Determine system health based on recent metrics
      stats.systemHealth = this.determineSystemHealth(metrics);

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
          averageResponseTime: 0,
          documentsProcessed: 0,
          systemHealth: "offline",
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
      const response = await this.makeRequest("/", "GET");
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

  // Document verification
  async verifyDocument(formData) {
    try {
      const config = {
        timeout: 120000, // 2 minutes for verification
      };

      const response = await this.api.post("/api/verify", formData, config);

      return {
        success: true,
        data: response.data,
        message: "Document verification completed",
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  // Get verification types
  async getVerificationTypes() {
    try {
      const response = await this.api.get("/api/verification-types");

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        data: {
          verification_types: {},
          supported_formats: []
        }
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

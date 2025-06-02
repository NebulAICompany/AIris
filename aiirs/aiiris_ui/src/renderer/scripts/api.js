// API Service for Backend Communication via IPC

class APIService {
  constructor() {
    this.isElectron = typeof window.airisAPI !== "undefined";
    this.baseURL = "http://localhost:8000";
    this.timeout = 30000;

    if (!this.isElectron) {
      console.warn("Running in browser mode - some features may not work");
      this.setupAxios();
    }
  }

  setupAxios() {
    // Create axios instance for browser fallback
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error("[API] Request error:", error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => {
        console.log(
          `[API] Response: ${response.status} ${response.config.url}`
        );
        return response;
      },
      (error) => {
        console.error("[API] Response error:", error);

        if (error.code === "ECONNABORTED") {
          throw new Error("Request timeout - please try again");
        }

        if (error.response) {
          // Server responded with error status
          const status = error.response.status;
          const message =
            error.response.data?.message ||
            error.response.data?.detail ||
            "Server error";

          if (status >= 500) {
            throw new Error(`Server error (${status}): ${message}`);
          } else if (status >= 400) {
            throw new Error(`Client error (${status}): ${message}`);
          }
        } else if (error.request) {
          // No response received
          throw new Error(
            "Unable to connect to server. Please check if the backend is running."
          );
        }

        throw error;
      }
    );
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
  async sendQuery(query) {
    try {
      const response = await this.api.post("/api/query", {
        query: query.trim(),
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
        headers: {
          "Content-Type": "multipart/form-data",
        },
        timeout: 120000, // 2 minutes for file uploads
        onUploadProgress: (progressEvent) => {
          if (progressCallback && progressEvent.lengthComputable) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            progressCallback(percentCompleted);
          }
        },
      };

      const response = await this.api.post("/api/upload", formData, config);

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

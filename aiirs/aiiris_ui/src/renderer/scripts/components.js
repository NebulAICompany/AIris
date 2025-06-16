/**
 * UI Components for AIris Electron App
 * Handles all user interface interactions and component management
 */

class UIComponents {
  constructor() {
    this.currentTab = "chat";
    this.chatHistory = [];
    this.uploadedFiles = [];
    this.isProcessing = false;
    this.isDarkMode = false;
    // Add webSearchEnabled flag, initialize from storage or default to false
    this.webSearchEnabled = Utils.isWebSearchEnabled();

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadTheme();
    this.initializeComponents();
    // Set toggle state on load
    const webSearchToggle = document.getElementById("web-search-toggle");
    if (webSearchToggle) {
      webSearchToggle.checked = this.webSearchEnabled;
    }
  }

  setupEventListeners() {
    // Navigation
    document.querySelectorAll(".nav-item").forEach((item) => {
      item.addEventListener("click", (e) => this.handleNavigation(e));
    });

    // Chat functionality
    const chatInput = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-button");

    if (chatInput && sendButton) {
      chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      chatInput.addEventListener("input", () => {
        this.toggleSendButton();
      });

      sendButton.addEventListener("click", () => this.sendMessage());
    }

    // File upload
    const uploadArea = document.getElementById("upload-area");
    const fileInput = document.getElementById("file-input");
    const uploadButton = document.getElementById("upload-button");
    const browseButton = document.getElementById("browse-files");

    if (uploadArea) {
      uploadArea.addEventListener("dragover", (e) => this.handleDragOver(e));
      uploadArea.addEventListener("dragleave", (e) => this.handleDragLeave(e));
      uploadArea.addEventListener("drop", (e) => this.handleFileDrop(e));
      uploadArea.addEventListener("click", () => fileInput?.click());
    }

    if (browseButton) {
      browseButton.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput?.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", (e) => this.handleFileSelect(e));
    }

    if (uploadButton) {
      uploadButton.addEventListener("click", () => this.processFiles());
    }

    // Theme toggle
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      themeToggle.addEventListener("click", () => this.toggleTheme());
    }

    // Clear chat
    const clearChatButton = document.getElementById("clear-chat");
    if (clearChatButton) {
      clearChatButton.addEventListener("click", () => this.clearChat());
    }

    // Settings save
    const saveSettingsButton = document.getElementById("save-settings");
    if (saveSettingsButton) {
      saveSettingsButton.addEventListener("click", () => this.saveSettings());
    }

    // Web Search toggle event
    const webSearchToggle = document.getElementById("web-search-toggle");
    if (webSearchToggle) {
      webSearchToggle.addEventListener("change", (e) => {
        this.webSearchEnabled = e.target.checked;
        Utils.setWebSearchEnabled(this.webSearchEnabled);
        // Optionally, notify backend here if needed
        // Example: window.airisAPI.setWebSearchEnabled?.(this.webSearchEnabled);
      })
      console.log("webSearchEnabled: ", this.webSearchEnabled);
    }

    // Event delegation for dynamic buttons
    document.addEventListener("click", (e) => {
      if (e.target.classList.contains("cta-button") && e.target.dataset.tab) {
        this.switchTab(e.target.dataset.tab);
      }
    });
  }

  handleNavigation(e) {
    e.preventDefault();
    const targetTab = e.currentTarget.getAttribute("data-tab");

    if (targetTab && targetTab !== this.currentTab) {
      this.switchTab(targetTab);
    }
  }

  switchTab(tabId) {
    // Update navigation
    document.querySelectorAll(".nav-item").forEach((item) => {
      item.classList.remove("active");
    });

    const activeNavItem = document.querySelector(
      `.nav-item[data-tab="${tabId}"]` );
    if (activeNavItem) {
      activeNavItem.classList.add("active");
    }

    // Update content
    document.querySelectorAll(".tab-content").forEach((content) => {
      content.classList.remove("active");
    });

    const activeContent = document.getElementById(`${tabId}-tab`);
    if (activeContent) {
      activeContent.classList.add("active");
      this.currentTab = tabId;

      // Load tab-specific data
      this.loadTabData(tabId);
    }
  }

  async loadTabData(tabId) {
    switch (tabId) {
      case "files":
        await this.loadFileLibrary();
        break;
      case "analytics":
        await this.loadAnalytics();
        break;
    }
  }

  toggleSendButton() {
    const chatInput = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-button");

    if (chatInput && sendButton) {
      const hasText = chatInput.value.trim().length > 0;
      sendButton.disabled = !hasText || this.isProcessing;
    }
  }

  async sendMessage() {
    const chatInput = document.getElementById("chat-input");
    const message = chatInput.value.trim();

    if (!message || this.isProcessing) return;

    this.isProcessing = true;
    chatInput.value = "";
    this.toggleSendButton();

    // Add user message to chat
    this.addMessageToChat("user", message);

    try {
      // Show typing indicator
      this.showTypingIndicator();

      // Send to backend
      const response = await window.airisAPI.sendQuery(message); // Remove typing indicator
      this.hideTypingIndicator();

      // Add AI response to chat
      this.addMessageToChat("assistant", response.response);

      // Update chat history
      this.chatHistory.push({ user: message, assistant: response.response });
    } catch (error) {
      this.hideTypingIndicator();
      this.addMessageToChat(
        "error",
        "Sorry, I encountered an error processing your request. Please try again."
      );
      console.error("Chat error:", error);
    } finally {
      this.isProcessing = false;
      this.toggleSendButton();
      chatInput.focus();
    }
  }

  addMessageToChat(type, content) {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}-message`;

    const timestamp = new Date().toLocaleTimeString();

    if (type === "user") {
      messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-text">${Utils.escapeHtml(content)}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
            `;
    } else if (type === "assistant") {
      messageDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">${marked.parse(content)}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
            `;
    } else if (type === "error") {
      messageDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <div class="message-content">
                    <div class="message-text error">${Utils.escapeHtml(
                      content
                    )}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
            `;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Apply syntax highlighting
    messageDiv.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightBlock(block);
    });
  }

  showTypingIndicator() {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    const typingDiv = document.createElement("div");
    typingDiv.className = "message assistant-message typing-indicator";
    typingDiv.id = "typing-indicator";

    typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  hideTypingIndicator() {
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  clearChat() {
    const chatMessages = document.getElementById("chat-messages");
    if (chatMessages) {
      chatMessages.innerHTML = "";
      this.chatHistory = [];

      // Add welcome message
      this.addMessageToChat(
        "assistant",
        "Hello! I'm your AI financial document assistant. Upload your documents and ask me questions about them."
      );
    }
  }

  // File handling
  handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add("drag-over");
  }

  handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove("drag-over");
  }

  handleFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove("drag-over");

    const files = Array.from(e.dataTransfer.files);
    this.addFilesToQueue(files);
  }

  handleFileSelect(e) {
    const files = Array.from(e.target.files);
    this.addFilesToQueue(files);
  }

  addFilesToQueue(files) {
    const validFiles = files.filter((file) => Utils.validateFile(file));
    const fileQueue = document.getElementById("file-queue");

    if (!fileQueue) return;

    validFiles.forEach((file) => {
      const fileItem = this.createFileQueueItem(file);
      fileQueue.appendChild(fileItem);
    });

    // Update upload button state
    this.updateUploadButton();
  }

  createFileQueueItem(file) {
    const fileItem = document.createElement("div");
    fileItem.className = "file-queue-item";
    fileItem.dataset.fileName = file.name;

    const fileIcon = Utils.getFileIcon(file.name);
    const fileSize = Utils.formatFileSize(file.size);

    fileItem.innerHTML = `
            <div class="file-info">
                <i class="${fileIcon}"></i>
                <div class="file-details">
                    <div class="file-name">${Utils.escapeHtml(file.name)}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
            </div>
            <div class="file-actions">
                <button class="remove-file" onclick="this.closest('.file-queue-item').remove(); window.uiComponents.updateUploadButton();">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="upload-progress" style="display: none;">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text">0%</div>
            </div>
        `;

    return fileItem;
  }

  updateUploadButton() {
    const uploadButton = document.getElementById("upload-button");
    const fileQueue = document.getElementById("file-queue");

    if (uploadButton && fileQueue) {
      const hasFiles = fileQueue.children.length > 0;
      uploadButton.disabled = !hasFiles || this.isProcessing;
    }
  }

  async processFiles() {
    const fileQueue = document.getElementById("file-queue");
    const fileInput = document.getElementById("file-input");

    if (!fileQueue || fileQueue.children.length === 0) return;

    this.isProcessing = true;
    this.updateUploadButton();

    const fileItems = Array.from(fileQueue.children);

    for (const fileItem of fileItems) {
      const fileName = fileItem.dataset.fileName;
      const file = Array.from(fileInput.files).find((f) => f.name === fileName);

      if (file) {
        await this.uploadFile(file, fileItem);
      }
    }

    this.isProcessing = false;
    this.updateUploadButton();

    // Clear file input
    fileInput.value = "";

    // Refresh file library
    if (this.currentTab === "files") {
      await this.loadFileLibrary();
    }
  }

  async uploadFile(file, fileItem) {
    const progressElement = fileItem.querySelector(".upload-progress");
    const progressFill = fileItem.querySelector(".progress-fill");
    const progressText = fileItem.querySelector(".progress-text");

    progressElement.style.display = "block";

    try {
      // Convert File to ArrayBuffer for IPC communication
      const fileBuffer = await file.arrayBuffer();

      // Simulate progress during file reading
      progressFill.style.width = "25%";
      progressText.textContent = "25%";

      // Call IPC with fileData and fileName separately
      const response = await window.airisAPI.uploadFile(fileBuffer, file.name);

      // Update progress to complete
      progressFill.style.width = "100%";
      progressText.textContent = "100%";

      // Success
      fileItem.classList.add("upload-success");
      progressText.textContent = "Complete";

      // Remove after delay
      setTimeout(() => {
        fileItem.remove();
        this.updateUploadButton();
      }, 2000);

      this.uploadedFiles.push({
        name: file.name,
        size: file.size,
        uploadDate: new Date(),
        id: response.file_id || Utils.generateId(),
      });
    } catch (error) {
      fileItem.classList.add("upload-error");
      progressText.textContent = "Error";
      console.error("Upload error:", error);
    }
  }

  async loadFileLibrary() {
    try {
      // Fetch the file list with metadata from the backend
      const response = await fetch("http://localhost:8000/api/files");
      if (!response.ok) throw new Error("Failed to fetch file list");
      const data = await response.json();
      const files = data.files || [];
      // Get the file library container
      const fileLibrary = document.getElementById("files-grid");
      if (!fileLibrary) return;
      fileLibrary.innerHTML = "";

      if (files.length === 0) {
        fileLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-folder-open"></i>
          <h3>No documents yet</h3>
          <p>Upload some documents to get started</p>
          <button class="cta-button" data-tab="upload">Upload Files</button>
        </div>`;
        return;
      }

      // Render each file with metadata
      files.forEach((file) => {
        const fileItem = document.createElement("div");
        fileItem.className = "file-card";
        fileItem.style.cursor = "pointer";
        fileItem.dataset.fileName = file.name;
        fileItem.innerHTML = `
          <div class="file-card-header">
            <div class="file-card-icon">
              <i class="${Utils.getFileIcon(file.name)}"></i>
            </div>
            <div class="file-card-info">
              <div class="file-card-name">${Utils.escapeHtml(file.name)}</div>
              <div class="file-card-details">${Utils.formatFileSize(file.size)} • ${Utils.formatDate(file.created_at)}</div>
            </div>
          </div>
        `;
        
        // Add click handler to open file
        fileItem.addEventListener('click', () => {
          this.openFile(file.name);
        });
        
        fileLibrary.appendChild(fileItem);
      });
    } catch (error) {
      const fileLibrary = document.getElementById("files-grid");
      if (fileLibrary) {
        fileLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>Error loading files</h3>
          <p>Failed to load files. Please try again later.</p>
        </div>`;
      }
      console.error("Error loading file library:", error);
    }
  }

  async openFile(fileName) {
    try {
      // Request the main process to open the file
      const result = await window.airisAPI.openFile(fileName);
      
      if (!result.success) {
        this.showNotification(`Failed to open file: ${result.error}`, 'error');
      }
    } catch (error) {
      console.error('Error opening file:', error);
      this.showNotification('Failed to open file. Please try again.', 'error');
    }
  }

  createFileLibraryItem(file) {
    const fileElement = document.createElement("div");
    fileElement.className = "file-item";

    const fileIcon = Utils.getFileIcon(file.name);
    const fileSize = Utils.formatFileSize(file.size);
    const uploadDate = new Date(file.uploadDate).toLocaleDateString();

    fileElement.innerHTML = `
            <div class="file-icon">
                <i class="${fileIcon}"></i>
            </div>
            <div class="file-details">
                <div class="file-name">${Utils.escapeHtml(file.name)}</div>
                <div class="file-meta">
                    <span class="file-size">${fileSize}</span>
                    <span class="file-date">Uploaded ${uploadDate}</span>
                </div>
            </div>
            <div class="file-actions">
                <button class="action-btn" onclick="window.uiComponents.downloadFile('${
                  file.id
                }')">
                    <i class="fas fa-download"></i>
                </button>
                <button class="action-btn delete" onclick="window.uiComponents.deleteFile('${
                  file.id
                }')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

    return fileElement;
  }

  async downloadFile(fileId) {
    try {
      // In a real app, this would download from the backend
      console.log("Downloading file:", fileId);
    } catch (error) {
      console.error("Download error:", error);
    }
  }

  async deleteFile(fileId) {
    if (!confirm("Are you sure you want to delete this file?")) return;

    try {
      // Remove from local storage
      this.uploadedFiles = this.uploadedFiles.filter((f) => f.id !== fileId);

      // Refresh the file library
      await this.loadFileLibrary();
    } catch (error) {
      console.error("Delete error:", error);
    }
  }

  async loadAnalytics() {
    try {
      const metrics = await window.airisAPI.getMetrics();
      this.updateAnalyticsDashboard(metrics);
      
      // Set up auto-refresh every 30 seconds when on analytics tab
      if (this.currentTab === "analytics") {
        if (this.analyticsRefreshTimer) {
          clearInterval(this.analyticsRefreshTimer);
        }
        this.analyticsRefreshTimer = setInterval(async () => {
          if (this.currentTab === "analytics") {
            try {
              const updatedMetrics = await window.airisAPI.getMetrics();
              this.updateAnalyticsDashboard(updatedMetrics);
            } catch (error) {
              console.error("Analytics refresh error:", error);
            }
          } else {
            clearInterval(this.analyticsRefreshTimer);
          }
        }, 30000); // Refresh every 30 seconds
      }
    } catch (error) {
      console.error("Analytics error:", error);
      // Show fallback data
      this.updateAnalyticsDashboard({
        totalQueries: 0,
        totalDocuments: 0,
        avgResponseTime: "N/A",
        systemHealth: "Error",
        recentActivity: []
      });
    }
  }

  updateAnalyticsDashboard(metrics) {
    // Update metric cards using the correct IDs from HTML
    const apiRequests = document.getElementById("api-requests");
    const responseTime = document.getElementById("response-time");
    const documentCount = document.getElementById("document-count");
    const systemHealth = document.getElementById("system-health");

    if (apiRequests) {
      apiRequests.textContent = metrics.totalQueries || "0";
    }
    if (responseTime) {
      responseTime.textContent = metrics.avgResponseTime || "N/A";
    }
    if (documentCount) {
      documentCount.textContent = metrics.totalDocuments || "0";
    }
    if (systemHealth) {
      systemHealth.textContent = metrics.systemHealth || "Unknown";
      // Color code the health status
      systemHealth.style.color = 
        metrics.systemHealth === "Healthy" ? "var(--success)" : 
        metrics.systemHealth === "Disconnected" ? "var(--error)" : 
        "var(--text-secondary)";
    }

    // Update recent activity
    this.updateRecentActivity(metrics.recentActivity || []);
  }

  updateRecentActivity(activities) {
    const activityList = document.getElementById("recent-activity");
    if (!activityList) return;

    activityList.innerHTML = "";

    if (activities.length === 0) {
      activityList.innerHTML =
        '<div class="no-activity">No recent activity</div>';
      return;
    }

    activities.forEach((activity) => {
      const activityItem = document.createElement("div");
      activityItem.className = "activity-item";

      activityItem.innerHTML = `
                <div class="activity-icon">
                    <i class="${activity.icon || "fas fa-circle"}"></i>
                </div>
                <div class="activity-details">
                    <div class="activity-title">${Utils.escapeHtml(
                      activity.title
                    )}</div>
                    <div class="activity-time">${activity.time}</div>
                </div>
            `;

      activityList.appendChild(activityItem);
    });
  }

  // Theme management
  loadTheme() {
    const savedTheme = localStorage.getItem("airis-theme") || "light";
    this.isDarkMode = savedTheme === "dark";
    this.applyTheme();
  }

  toggleTheme() {
    this.isDarkMode = !this.isDarkMode;
    this.applyTheme();
    localStorage.setItem("airis-theme", this.isDarkMode ? "dark" : "light");
  }

  applyTheme() {
    document.body.classList.toggle("dark-theme", this.isDarkMode);

    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      themeToggle.innerHTML = this.isDarkMode
        ? '<i class="fas fa-sun"></i>'
        : '<i class="fas fa-moon"></i>';
    }
  }

  // Settings management
  saveSettings() {
    const settings = {
      apiEndpoint:
        document.getElementById("api-endpoint")?.value ||
        "http://localhost:8000",
      maxFileSize: document.getElementById("max-file-size")?.value || "50",
      autoSave: document.getElementById("auto-save")?.checked || false,
      notifications: document.getElementById("notifications")?.checked || true,
    };

    localStorage.setItem("airis-settings", JSON.stringify(settings));

    // Show success message
    this.showNotification("Settings saved successfully!", "success");
  }

  loadSettings() {
    try {
      const settings = JSON.parse(
        localStorage.getItem("airis-settings") || "{}"
      );

      if (document.getElementById("api-endpoint")) {
        document.getElementById("api-endpoint").value =
          settings.apiEndpoint || "http://localhost:8000";
      }
      if (document.getElementById("max-file-size")) {
        document.getElementById("max-file-size").value =
          settings.maxFileSize || "50";
      }
      if (document.getElementById("auto-save")) {
        document.getElementById("auto-save").checked =
          settings.autoSave || false;
      }
      if (document.getElementById("notifications")) {
        document.getElementById("notifications").checked =
          settings.notifications !== false;
      }
    } catch (error) {
      console.error("Error loading settings:", error);
    }
  }

  showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
            <i class="fas fa-${
              type === "success"
                ? "check"
                : type === "error"
                ? "exclamation-triangle"
                : "info"
            }"></i>
            <span>${Utils.escapeHtml(message)}</span>
        `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add("show"), 100);

    // Remove after delay
    setTimeout(() => {
      notification.classList.remove("show");
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  initializeComponents() {
    // Load settings
    this.loadSettings();

    // Initialize with welcome message
    this.addMessageToChat(
      "assistant",
      "Hello! I'm your AI financial document assistant. Upload your documents and ask me questions about them."
    );

    // Update upload button state
    this.updateUploadButton();

    // Load initial tab data
    this.loadTabData(this.currentTab);
  }

  // Example method to get the flag for backend communication
  isWebSearchEnabled() {
    return this.webSearchEnabled;
  }
}

// Export for global access
window.UIComponents = UIComponents;

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

    // Add wolframEnabled flag, initialize from storage or default to false
    this.wolframEnabled = Utils.isWolframEnabled();

    // Finance news properties
    this.newsRefreshInterval = null;
    this.lastNewsUpdate = null;

    // Chat session management
    this.currentSessionId = null;
    this.chatSessions = [];

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

    const wolframToggle = document.getElementById("wolfram-toggle");
    if (wolframToggle) {
      wolframToggle.checked = this.wolframEnabled;
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
    // Suggestion chips
    this.setupSuggestionChips();

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

    // Clear chat functionality removed

    // New chat button
    const newChatButton = document.getElementById("new-chat-btn");
    if (newChatButton) {
      newChatButton.addEventListener(
        "click",
        async () => await this.startNewChat()
      );
    }

    // Chat history dropdown buttons
    const toggleChatHistoryButton = document.getElementById(
      "toggle-chat-history"
    );
    if (toggleChatHistoryButton) {
      toggleChatHistoryButton.addEventListener(
        "click",
        async () => await this.toggleChatHistoryDropdown()
      );
    }

    const closeChatHistoryButton =
      document.getElementById("close-chat-history");
    if (closeChatHistoryButton) {
      closeChatHistoryButton.addEventListener("click", () =>
        this.closeChatHistoryDropdown()
      );
    }

    // Settings save
    const saveSettingsButton = document.getElementById("save-settings");
    if (saveSettingsButton) {
      saveSettingsButton.addEventListener("click", () => this.saveSettings());
    } // Web Search toggle event
    const webSearchToggle = document.getElementById("web-search-toggle");
    if (webSearchToggle) {
      webSearchToggle.addEventListener("change", (e) => {
        this.webSearchEnabled = e.target.checked;
        Utils.setWebSearchEnabled(this.webSearchEnabled);
        console.log("Web search enabled:", this.webSearchEnabled);
        // Optionally, notify backend here if needed
        // Example: window.airisAPI.setWebSearchEnabled?.(this.webSearchEnabled);
      });
      console.log("webSearchEnabled: ", this.webSearchEnabled);
    }

    // Wolfram Alpha toggle event
    const wolframToggle = document.getElementById("wolfram-toggle");
    if (wolframToggle) {
      wolframToggle.addEventListener("change", (e) => {
        this.wolframEnabled = e.target.checked;
        Utils.setWolframEnabled(this.wolframEnabled);
        console.log("Wolfram Alpha enabled:", this.wolframEnabled);
        // Optionally, notify backend here if needed
        // Example: window.airisAPI.setWolframEnabled?.(this.wolframEnabled);
      });
      console.log("wolframEnabled: ", this.wolframEnabled);
    }

    // Finance News refresh button
    const refreshNewsButton = document.getElementById("refresh-news");
    if (refreshNewsButton) {
      refreshNewsButton.addEventListener("click", () =>
        this.loadFinanceNews(true)
      );
    }

    // Event delegation for dynamic buttons
    document.addEventListener("click", (e) => {
      if (e.target.classList.contains("cta-button") && e.target.dataset.tab) {
        this.switchTab(e.target.dataset.tab);
      }

      // Handle delete button clicks
      if (e.target.closest(".delete-btn")) {
        e.preventDefault();
        e.stopPropagation();
        const deleteBtn = e.target.closest(".delete-btn");
        const fileName = deleteBtn.dataset.filename;
        if (fileName) {
          this.deleteFile(fileName);
        }
      }

      // Handle news article clicks
      if (e.target.closest(".news-item")) {
        const newsItem = e.target.closest(".news-item");
        const link = newsItem.dataset.link;
        if (link) {
          window.open(link, "_blank");
        }
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
      `.nav-item[data-tab="${tabId}"]`
    );
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
      case "news":
        await this.loadFinanceNews();
        break;
    }
  }

  setupSuggestionChips() {
    const suggestionChips = document.querySelectorAll(".suggestion-chip");

    suggestionChips.forEach((chip) => {
      chip.addEventListener("click", (e) => {
        const chipText = e.target.textContent.trim();
        this.handleSuggestionChipClick(chipText);
      });
    });
  }

  handleSuggestionChipClick(chipText) {
    const chatInput = document.getElementById("chat-input");

    // Define the queries for each suggestion chip
    const chipQueries = {
      "Tüm Dosyalarımı özetle":
        "Yüklediğim tüm dosyaları analiz et ve içeriklerinin genel bir özetini çıkar. Hangi türde belgelerim var ve ne tür bilgiler içeriyorlar?",
      "Seçili Dosyalarımı özetle":
        "Seçili belgelerdeki finansal trendleri ve desenleri analiz et. Önemli değişiklikleri, büyüme kalıplarını ve dikkat çekici finansal görüşleri göster.",
      "Seçili dosyadan gider analizi":
        "Seçili dosyalarımda bulunan tüm giderlerin kapsamlı bir özetini hazırla. Giderleri kategoriye, zaman dilimine göre ayır ve önemli harcama kalıplarını vurgula.",
    };

    const query = chipQueries[chipText];

    if (query && chatInput) {
      // Set the query in the input field
      chatInput.value = query;

      // Auto-send the message
      this.sendMessage();

      // Hide the welcome message with chips since user has started chatting
      this.hideWelcomeMessage();
    }
  }

  hideWelcomeMessage() {
    const welcomeMessage = document.querySelector(".chat-messages .message");
    if (welcomeMessage && welcomeMessage.classList.contains("assistant")) {
      // Check if this is the welcome message by looking for suggestion chips
      const hasSuggestionChips =
        welcomeMessage.querySelector(".suggestion-chips");
      if (hasSuggestionChips) {
        welcomeMessage.style.display = "none";
      }
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

    // Create new session if none exists
    if (!this.currentSessionId) {
      const sessionId = await this.createNewChatSession();
      if (!sessionId) {
        console.warn("Failed to create session, proceeding without session ID");
      }
    }

    // Add user message to chat
    this.addMessageToChat("user", message);

    // Show enhanced typing indicator with progress info
    this.showEnhancedTypingIndicator(message);

    try {
      // Send to backend with enhanced error handling
      const response = await this.sendQueryWithRetry(
        message,
        this.webSearchEnabled,
        this.wolframEnabled,
        this.currentSessionId
      );

      // Remove typing indicator
      this.hideTypingIndicator();

      // Check if response is valid
      if (!response || !response.success) {
        const errorMsg = response?.error || "AI'dan yanıt alınamadı";
        this.addMessageToChat(
          "error",
          `Üzgünüm, isteğinizi işleyemedim: ${errorMsg}`
        );
        return;
      }

      // Ensure we have actual response content
      const assistantResponse =
        response.response ||
        response.data?.response ||
        "Özür dilerim, uygun bir yanıt oluşturamadım.";

      // Update session ID if it was created server-side
      if (response.sessionId && response.sessionId !== this.currentSessionId) {
        this.currentSessionId = response.sessionId;
        // Refresh sessions list to show the new session
        await this.loadChatSessions();
      }

      // Add AI response to chat
      this.addMessageToChat("assistant", assistantResponse);

      // Update chat history
      this.chatHistory.push({ user: message, assistant: assistantResponse });
    } catch (error) {
      this.hideTypingIndicator();

      let errorMessage =
        "Üzgünüm, isteğinizi işlerken bir hata oluştu. Lütfen tekrar deneyin.";

      // Enhanced error handling based on error type
      if (error.message) {
        if (
          error.message.includes("timeout") ||
          error.message.includes("zaman aşımı")
        ) {
          errorMessage =
            "İstek zaman aşımına uğradı. AI servisi meşgul olabilir. Lütfen daha kısa bir soru deneyin veya birkaç saniye bekleyin.";
        } else if (
          error.message.includes("fetch") ||
          error.message.includes("network") ||
          error.message.includes("bağlan")
        ) {
          errorMessage =
            "Bağlantı hatası. İnternet bağlantınızı kontrol edin ve tekrar deneyin.";
        } else if (
          error.message.includes("502") ||
          error.message.includes("503")
        ) {
          errorMessage =
            "Backend servisi geçici olarak kullanılamıyor. Lütfen birkaç saniye bekleyin ve tekrar deneyin.";
        } else if (error.message.includes("500")) {
          errorMessage =
            "AI servisi geçici olarak kullanılamıyor. Lütfen birkaç dakika sonra tekrar deneyin.";
        }
      }

      this.addMessageToChat("error", errorMessage);
      console.error("Chat error:", error);
    } finally {
      this.isProcessing = false;
      this.toggleSendButton();
      chatInput.focus();
    }
  }

  // Enhanced query sending with retry logic
  async sendQueryWithRetry(
    message,
    webSearchEnabled,
    wolframEnabled,
    sessionId,
    maxRetries = 2
  ) {
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`[Chat] Sending query attempt ${attempt}/${maxRetries}`);

        const response = await window.apiService.sendQuery(
          message,
          webSearchEnabled,
          wolframEnabled,
          sessionId
        );

        return response;
      } catch (error) {
        lastError = error;
        console.warn(`[Chat] Attempt ${attempt} failed:`, error.message);

        // Don't retry on certain error types
        if (
          error.message.includes("400") ||
          error.message.includes("401") ||
          error.message.includes("403")
        ) {
          throw error;
        }

        // If not the last attempt, wait before retrying
        if (attempt < maxRetries) {
          this.updateTypingIndicatorMessage(
            `Bağlantı sorunu, tekrar deneniyor... (${attempt}/${maxRetries})`
          );
          await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait 2 seconds
        }
      }
    }

    throw lastError;
  }

  // Enhanced typing indicator with progress info
  showEnhancedTypingIndicator(message) {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    // Remove any existing typing indicator
    this.hideTypingIndicator();

    const typingDiv = document.createElement("div");
    typingDiv.className = "message assistant-message typing-indicator";
    typingDiv.id = "typing-indicator";

    // Determine what features are enabled for status message
    let statusMessage = "AI düşünüyor...";
    if (this.webSearchEnabled && this.wolframEnabled) {
      statusMessage = "Web araması ve Wolfram Alpha ile analiz ediliyor...";
    } else if (this.webSearchEnabled) {
      statusMessage = "Web araması yapılıyor...";
    } else if (this.wolframEnabled) {
      statusMessage = "Wolfram Alpha ile analiz ediliyor...";
    }

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
        <div class="typing-status">${statusMessage}</div>
      </div>
    `;

    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Update typing indicator message
  updateTypingIndicatorMessage(message) {
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) {
      const statusElement = typingIndicator.querySelector(".typing-status");
      if (statusElement) {
        statusElement.textContent = message;
      }
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
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">${Utils.escapeHtml(content)}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
            `;
    } else if (type === "assistant") {
      // Detect and format metadata content automatically
      let processedContent = content || "No response received";

      // Auto-detect and format metadata sections
      processedContent = this.formatMetadataContent(processedContent);

      // Safely parse markdown content, fallback to escaped HTML if marked fails
      let parsedContent;
      try {
        parsedContent =
          processedContent && typeof processedContent === "string"
            ? marked.parse(processedContent)
            : Utils.escapeHtml(processedContent);
      } catch (error) {
        console.warn("Markdown parsing failed:", error);
        parsedContent = Utils.escapeHtml(processedContent);
      }

      messageDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">${parsedContent}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
            `;

      // Apply metadata formatting immediately after adding the message
      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        const messageTextElement = messageDiv.querySelector(".message-text");
        if (messageTextElement) {
          this.applyMetadataFormatting(messageTextElement);
        }
      });
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

    // Apply syntax highlighting and force metadata styling
    messageDiv.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightBlock(block);
    });

    // Apply metadata formatting to new message
    this.applyMetadataFormatting(messageDiv);
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

      // Start a new session
      this.currentSessionId = null;

      // Add welcome message
      this.addMessageToChat(
        "assistant",
        "Hello! I'm your AI financial document assistant. Upload your documents and ask me questions about them."
      );
    }
  }

  // Chat Session Management Methods
  async createNewChatSession() {
    try {
      const response = await window.apiService.createChatSession();
      if (response.success) {
        this.currentSessionId = response.sessionId;
        console.log("Created new chat session:", this.currentSessionId);

        // Reload chat sessions to show the new session in the list
        await this.loadChatSessions();

        return this.currentSessionId;
      } else {
        console.error("Failed to create chat session:", response.error);
        return null;
      }
    } catch (error) {
      console.error("Error creating chat session:", error);
      return null;
    }
  }

  async loadChatSession(sessionId) {
    try {
      const response = await window.apiService.getChatSession(sessionId);
      if (response.success) {
        this.currentSessionId = sessionId;
        this.chatHistory = [];

        // Clear current chat
        const chatMessages = document.getElementById("chat-messages");
        if (chatMessages) {
          chatMessages.innerHTML = "";
        }

        // Load messages from session
        const session = response.session;
        session.messages.forEach((msg) => {
          this.addMessageToChat(msg.role, msg.content);

          // Update local chat history
          if (msg.role === "user") {
            this.chatHistory.push({ user: msg.content });
          } else if (msg.role === "assistant") {
            if (
              this.chatHistory.length > 0 &&
              !this.chatHistory[this.chatHistory.length - 1].assistant
            ) {
              this.chatHistory[this.chatHistory.length - 1].assistant =
                msg.content;
            }
          }
        });

        // Update UI to show active session
        this.updateChatSessionsUI();

        // Apply metadata formatting more reliably
        // Use requestAnimationFrame to ensure DOM is ready
        requestAnimationFrame(() => {
          this.fixExistingMetadataFormatting();

          // Apply additional formatting passes to catch any delayed renders
          setTimeout(() => this.fixExistingMetadataFormatting(), 100);
          setTimeout(() => this.fixExistingMetadataFormatting(), 300);
          setTimeout(() => this.fixExistingMetadataFormatting(), 600);
        });

        console.log("Loaded chat session:", sessionId);
        this.showNotification("Chat session loaded", "success");
        return true;
      } else {
        console.error("Failed to load chat session:", response.error);
        this.showNotification("Failed to load chat session", "error");
        return false;
      }
    } catch (error) {
      console.error("Error loading chat session:", error);
      this.showNotification("Error loading chat session", "error");
      return false;
    }
  }

  async loadChatSessions() {
    try {
      const response = await window.apiService.listChatSessions();
      if (response.success) {
        this.chatSessions = response.sessions;
        this.updateChatSessionsUI();

        // Auto-load the most recent session if no current session and we have sessions
        if (!this.currentSessionId && this.chatSessions.length > 0) {
          const mostRecentSession = this.chatSessions[0]; // Sessions are sorted by updated_at desc
          await this.loadChatSession(mostRecentSession.session_id);
        }

        return this.chatSessions;
      } else {
        console.error("Failed to load chat sessions:", response.error);
        return [];
      }
    } catch (error) {
      console.error("Error loading chat sessions:", error);
      return [];
    }
  }

  async deleteChatSession(sessionId) {
    try {
      const response = await window.apiService.deleteChatSession(sessionId);
      if (response.success) {
        // If this was the current session, clear it
        if (this.currentSessionId === sessionId) {
          this.clearChat();
        }

        // Reload sessions list
        await this.loadChatSessions();

        this.showNotification("Chat session deleted successfully", "success");
        return true;
      } else {
        this.showNotification("Failed to delete chat session", "error");
        return false;
      }
    } catch (error) {
      console.error("Error deleting chat session:", error);
      this.showNotification("Error deleting chat session", "error");
      return false;
    }
  }

  async startNewChat() {
    // Clear current chat
    this.clearChat();

    // Create a new session - this will also reload the sessions list
    const sessionId = await this.createNewChatSession();

    if (sessionId) {
      console.log("New chat session created:", sessionId);
      this.showNotification("Started new chat session", "success");
    } else {
      console.error("Failed to create new chat session");
      this.showNotification("Failed to create new chat session", "error");
    }
  }

  async toggleChatHistoryDropdown() {
    const dropdown = document.getElementById("chat-history-dropdown");
    if (dropdown) {
      const isVisible = dropdown.classList.contains("show");
      if (isVisible) {
        this.closeChatHistoryDropdown();
      } else {
        await this.showChatHistoryDropdown();
      }
    }
  }

  async showChatHistoryDropdown() {
    const dropdown = document.getElementById("chat-history-dropdown");
    if (dropdown) {
      // Refresh sessions list before showing dropdown
      await this.loadChatSessions();

      dropdown.classList.add("show");
      // Add click outside listener
      setTimeout(() => {
        document.addEventListener("click", this.handleClickOutside.bind(this));
      }, 100);
    }
  }

  closeChatHistoryDropdown() {
    const dropdown = document.getElementById("chat-history-dropdown");
    if (dropdown) {
      dropdown.classList.remove("show");
      // Remove click outside listener
      document.removeEventListener("click", this.handleClickOutside.bind(this));
    }
  }

  handleClickOutside(event) {
    const dropdown = document.getElementById("chat-history-dropdown");
    const toggleButton = document.getElementById("toggle-chat-history");

    if (
      dropdown &&
      !dropdown.contains(event.target) &&
      !toggleButton.contains(event.target)
    ) {
      this.closeChatHistoryDropdown();
    }
  }

  updateChatSessionsUI() {
    const sessionsList = document.getElementById("chat-sessions-list");
    if (!sessionsList) {
      console.warn("Chat sessions list element not found");
      return;
    }

    console.log(
      "Updating chat sessions UI with",
      this.chatSessions.length,
      "sessions"
    );

    // Clear loading state
    sessionsList.innerHTML = "";

    if (this.chatSessions.length === 0) {
      sessionsList.innerHTML = `
        <div class="no-sessions">
          <i class="fas fa-comments"></i>
          <p>No chat history yet</p>
          <p>Start a conversation to see it here</p>
        </div>
      `;
      return;
    }

    // Render each session
    this.chatSessions.forEach((session) => {
      const sessionItem = this.createChatSessionItem(session);
      sessionsList.appendChild(sessionItem);
    });

    console.log("Chat sessions UI updated successfully");
  }

  createChatSessionItem(session) {
    const sessionItem = document.createElement("div");
    sessionItem.className = "chat-session-item";
    sessionItem.dataset.sessionId = session.session_id;

    // Mark as active if it's the current session
    if (session.session_id === this.currentSessionId) {
      sessionItem.classList.add("active");
    }

    // Format the date
    const date = new Date(session.updated_at);
    const formattedDate = this.formatChatDate(date);

    sessionItem.innerHTML = `
      <div class="chat-session-title">${Utils.escapeHtml(
        session.title || "Untitled Chat"
      )}</div>
      <div class="chat-session-meta">
        <span class="chat-session-date">${formattedDate}</span>
        <span class="chat-session-count">${session.message_count}</span>
        <div class="chat-session-actions">
          <button class="chat-session-delete" data-session-id="${
            session.session_id
          }" title="Delete session">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    `;

    // Add click handler to load session
    sessionItem.addEventListener("click", (e) => {
      // Don't load session if clicking delete button
      if (!e.target.closest(".chat-session-delete")) {
        this.loadChatSession(session.session_id);
        this.closeChatHistoryDropdown();
      }
    });

    // Add delete handler
    const deleteBtn = sessionItem.querySelector(".chat-session-delete");
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.deleteChatSession(session.session_id);
    });

    return sessionItem;
  }

  formatChatDate(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } else if (diffDays === 1) {
      return "Yesterday";
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  }

  formatMetadataContent(content) {
    if (!content || typeof content !== "string") {
      return content;
    }

    // More flexible patterns to catch metadata sections with various formatting
    const metadataPatterns = [
      /---\s*\n\s*🗂️\s*Kullanılan Bilgi Metadataları:/gi,
      /🗂️\s*Kullanılan Bilgi Metadataları:/gi,
      /📊\s*Kullanılan Bilgi Metadataları:/gi,
      /\*\*Kullanılan Bilgi Metadataları:\*\*/gi,
      /Kullanılan Bilgi Metadataları:/gi,
    ];

    // Check if content contains any metadata pattern
    let metadataMatch = null;
    let matchedPattern = null;

    for (const pattern of metadataPatterns) {
      const match = content.match(pattern);
      if (match) {
        metadataMatch = match;
        matchedPattern = pattern;
        break;
      }
    }

    if (!metadataMatch) {
      return content;
    }

    // Find the actual start of metadata section (including any preceding separators)
    const fullMatch = metadataMatch[0];
    const metadataStart = content.indexOf(fullMatch);

    if (metadataStart === -1) {
      return content;
    }

    // Check if there's a separator (---) before the metadata
    let actualStart = metadataStart;
    const beforeMetadataCheck = content.substring(
      Math.max(0, metadataStart - 10),
      metadataStart
    );
    const separatorMatch = beforeMetadataCheck.match(/---\s*$/);
    if (separatorMatch) {
      actualStart = metadataStart - separatorMatch[0].length;
    }

    // Extract parts
    const beforeMetadata = content.substring(0, actualStart).trim();
    let metadataSection = content.substring(actualStart);

    // Clean up metadata section - remove various formats of the title
    let cleanedMetadata = metadataSection
      .replace(/---\s*\n\s*/g, "")
      .replace(/🗂️\s*Kullanılan Bilgi Metadataları:\s*/gi, "")
      .replace(/📊\s*Kullanılan Bilgi Metadataları:\s*/gi, "")
      .replace(/\*\*Kullanılan Bilgi Metadataları:\*\*\s*/gi, "")
      .replace(/Kullanılan Bilgi Metadataları:\s*/gi, "")
      .trim();

    // Also remove any trailing separators
    cleanedMetadata = cleanedMetadata.replace(/\s*---\s*$/, "").trim();

    // Format as code block
    const formattedMetadata = `\`\`\`\n${cleanedMetadata}\n\`\`\``;

    // Combine everything
    let result = "";
    if (beforeMetadata) {
      result += beforeMetadata + "\n\n";
    }
    result += formattedMetadata;

    return result;
  }

  fixExistingMetadataFormatting() {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    const messages = chatMessages.querySelectorAll(
      ".message.assistant-message"
    );

    console.log(`Fixing metadata formatting for ${messages.length} messages`);

    messages.forEach((messageDiv, index) => {
      const messageText = messageDiv.querySelector(".message-text");
      if (!messageText) return;

      // Get the original content - try to get from data attribute first, then fallback to text
      let originalContent =
        messageDiv.dataset.originalContent ||
        messageText.textContent ||
        messageText.innerText;

      // Store original content if not already stored
      if (!messageDiv.dataset.originalContent) {
        messageDiv.dataset.originalContent = originalContent;
      }

      // Enhanced metadata detection
      const metadataIndicators = [
        "Kullanılan Bilgi Metadataları:",
        "🗂️",
        "📊",
        "Kaynak:",
        "- Kaynak:",
        "📂 Kaynak:",
        "İşlem Durumu:",
        "Kategori:",
        "- Kategori:",
        "🏷️ Kategori:",
        "Tarih:",
        "- Tarih:",
        "📅 Tarih:",
        "Belge Türü:",
        "📄 Belge Türü:",
        "- Belge Türü:",
        "Alpha Vantage", // Financial data indicator
        "Finansal veriler",
      ];

      const hasMetadata = metadataIndicators.some((indicator) =>
        originalContent.includes(indicator)
      );

      if (hasMetadata) {
        console.log(`Processing message ${index + 1} with metadata`);

        // Check if metadata is already properly formatted
        const hasFormattedMetadata = messageText.querySelector("pre code");
        const hasMetadataLabel = messageText.querySelector(".metadata-label");

        // If already properly formatted, just apply styling
        if (hasFormattedMetadata && hasMetadataLabel) {
          this.applyMetadataFormatting(messageText);
          return;
        }

        // Remove any existing metadata labels first
        const existingLabels = messageText.querySelectorAll(".metadata-label");
        existingLabels.forEach((label) => label.remove());

        try {
          // Process the content with our improved formatters
          const formattedContent = this.formatMetadataContent(originalContent);

          // Parse markdown and update content
          const parsedContent = marked.parse(formattedContent);
          messageText.innerHTML = parsedContent;

          // Apply our enhanced styling
          this.applyMetadataFormatting(messageText);

          console.log(`Successfully reformatted message ${index + 1}`);
        } catch (error) {
          console.warn(`Failed to reformat message ${index + 1}:`, error);

          // Fallback: try to apply basic formatting
          try {
            this.applyMetadataFormatting(messageText);
          } catch (fallbackError) {
            console.warn(
              `Fallback formatting also failed for message ${index + 1}:`,
              fallbackError
            );
          }
        }
      }
    });

    console.log("Metadata formatting fix completed");
  }

  applyMetadataFormatting(container) {
    // Detect dark mode
    const isDarkMode =
      document.body.classList.contains("dark-theme") ||
      document.documentElement.getAttribute("data-theme") === "dark";

    // Apply our metadata styling to a specific container
    container.querySelectorAll("pre").forEach((preBlock) => {
      // Check if this pre block contains metadata content
      const preContent = preBlock.textContent || preBlock.innerText;
      const metadataKeywords = [
        "Kaynak:",
        "İşlem Durumu:",
        "Kategori:",
        "dosya",
        "sayfa",
        "kimlik",
        "yazışma",
        "bilgilendirme",
      ];
      const hasMetadataContent = metadataKeywords.some((keyword) =>
        preContent.includes(keyword)
      );

      // Only apply metadata styling if it contains actual metadata
      if (!hasMetadataContent) {
        return;
      }

      if (isDarkMode) {
        // Dark mode colors
        preBlock.style.cssText = `
          background-color: #1e293b !important;
          border: 1px solid #334155 !important;
          border-left: 4px solid #3b82f6 !important;
          border-radius: 8px !important;
          padding: 16px !important;
          margin: 12px 0 !important;
          overflow-x: auto !important;
          position: relative !important;
        `;
      } else {
        // Light mode colors
        preBlock.style.cssText = `
          background-color: #f0f2f5 !important;
          border: 1px solid #d1d5db !important;
          border-left: 4px solid #3b82f6 !important;
          border-radius: 8px !important;
          padding: 16px !important;
          margin: 12px 0 !important;
          overflow-x: auto !important;
          position: relative !important;
        `;
      }

      // Always add metadata label to code blocks that contain metadata content
      const existingLabel = preBlock.querySelector(".metadata-label");

      if (!existingLabel) {
        const label = document.createElement("div");
        label.className = "metadata-label";

        if (isDarkMode) {
          // Dark mode label styling
          label.style.cssText = `
            font-size: 11px !important;
            color: #60a5fa !important;
            font-weight: 600 !important;
            margin-bottom: 12px !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            background-color: rgba(59, 130, 246, 0.15) !important;
            padding: 6px 12px !important;
            border-radius: 4px !important;
            border-left: 3px solid #60a5fa !important;
            display: inline-block !important;
          `;
        } else {
          // Light mode label styling
          label.style.cssText = `
            font-size: 11px !important;
            color: #3b82f6 !important;
            font-weight: 600 !important;
            margin-bottom: 12px !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            background-color: rgba(59, 130, 246, 0.1) !important;
            padding: 6px 12px !important;
            border-radius: 4px !important;
            border-left: 3px solid #3b82f6 !important;
            display: inline-block !important;
          `;
        }

        label.textContent = "📊 Kullanılan Bilgi Metadataları";
        preBlock.insertBefore(label, preBlock.firstChild);
      }

      // Force code styling
      preBlock.querySelectorAll("code, code *").forEach((codeEl) => {
        if (isDarkMode) {
          // Dark mode code styling
          codeEl.style.cssText = `
            background: none !important;
            background-color: transparent !important;
            color: #cbd5e1 !important;
            font-family: 'SFMono-Regular', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', monospace !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
          `;
        } else {
          // Light mode code styling
          codeEl.style.cssText = `
            background: none !important;
            background-color: transparent !important;
            color: #4b5563 !important;
            font-family: 'SFMono-Regular', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', monospace !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
          `;
        }
      });
    });
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

      // Call API service for file upload
      const response = await window.apiService.uploadFile(file);

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
            <div class="file-card-main">
              <div class="file-card-icon">
                <i class="${Utils.getFileIcon(file.name)}"></i>
              </div>
              <div class="file-card-info">
                <div class="file-card-name">${Utils.escapeHtml(file.name)}</div>
                <div class="file-card-details">${Utils.formatFileSize(
                  file.size
                )} • ${Utils.formatDate(file.created_at)}</div>
              </div>
            </div>
            <div class="file-card-actions">
              <button class="file-action-btn delete-btn" data-filename="${Utils.escapeHtml(
                file.name
              )}" title="Delete file">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        `;

        // Add click handler to open file (but not on action buttons)
        fileItem.addEventListener("click", (e) => {
          // Don't open file if clicking on action buttons
          if (!e.target.closest(".file-card-actions")) {
            this.openFile(file.name);
          }
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
      // Try to open the file using Electron's API
      if (window.airisAPI && window.airisAPI.openFile) {
        try {
          await window.airisAPI.openFile(fileName);
          this.showNotification(`Opened ${fileName}`, "success");
          return;
        } catch (electronError) {
          console.warn(
            "Electron API failed, trying web fallback:",
            electronError
          );
        }
      }

      // Fallback: Try to download the file through the web API
      try {
        const downloadUrl = `http://localhost:8000/api/files/${encodeURIComponent(
          fileName
        )}/download`;
        window.open(downloadUrl, "_blank");
        this.showNotification(`Downloading ${fileName}...`, "info");
      } catch (downloadError) {
        console.error("Download failed:", downloadError);

        // Last resort: Try to get file info
        const response = await fetch(
          `http://localhost:8000/api/files/${encodeURIComponent(fileName)}`
        );
        if (response.ok) {
          const fileInfo = await response.json();
          this.showNotification(
            `${fileName} (${Utils.formatFileSize(
              fileInfo.size || 0
            )}) - Unable to open directly`,
            "warning"
          );
        } else {
          throw new Error("Unable to access file");
        }
      }
    } catch (error) {
      console.error("Error opening file:", error);
      this.showNotification(
        `Failed to open ${fileName}. Please try again.`,
        "error"
      );
    }
  }

  async deleteFile(fileName) {
    console.log("🗑️ Frontend: deleteFile called for:", fileName);

    try {
      // Show confirmation dialog
      console.log("🤔 Frontend: Showing confirmation dialog for:", fileName);
      const confirmed = confirm(
        `Are you sure you want to delete "${fileName}"?\n\nThis will permanently remove the file and all its data from the vector store.`
      );

      if (!confirmed) {
        console.log("❌ Frontend: User cancelled deletion for:", fileName);
        return;
      }

      console.log("✅ Frontend: User confirmed deletion for:", fileName);

      // Show loading state
      this.showNotification("Deleting file...", "info");

      console.log("🚀 Frontend: Calling API to delete file:", fileName);

      // Request the API service to delete the file
      const result = await fetch(
        `http://localhost:8000/api/files/${encodeURIComponent(fileName)}`,
        {
          method: "DELETE",
        }
      );

      if (!result.ok) {
        throw new Error(`Failed to delete file: ${result.statusText}`);
      }

      const data = await result.json();
      const response = { success: true, message: data.message };

      console.log("📋 Frontend: API response received:", response);

      if (response.success) {
        console.log(
          "✅ Frontend: Deletion successful, showing success message"
        );
        this.showNotification(
          `File "${fileName}" deleted successfully`,
          "success"
        );
        // Refresh the file list
        console.log("🔄 Frontend: Refreshing file list");
        this.loadFileLibrary();
      } else {
        console.error("❌ Frontend: Deletion failed:", response.error);
        this.showNotification(
          `Failed to delete file: ${response.error}`,
          "error"
        );
      }
    } catch (error) {
      console.error("❌ Frontend: Error deleting file:", error);
      console.error("❌ Frontend: Error details:", error.message, error.stack);
      this.showNotification(
        "Failed to delete file. Please try again.",
        "error"
      );
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
      const metrics = await window.apiService.getSystemStats();
      this.updateAnalyticsDashboard(metrics.stats);

      // Set up auto-refresh every 30 seconds when on analytics tab
      if (this.currentTab === "analytics") {
        if (this.analyticsRefreshTimer) {
          clearInterval(this.analyticsRefreshTimer);
        }
        this.analyticsRefreshTimer = setInterval(async () => {
          if (this.currentTab === "analytics") {
            try {
              const updatedMetrics = await window.apiService.getSystemStats();
              this.updateAnalyticsDashboard(updatedMetrics.stats);
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
        apiRequests: 0,
        documentsProcessed: 0,
        averageResponseTime: "N/A",
        systemHealth: "Error",
        recentActivity: [],
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
      apiRequests.textContent = metrics.apiRequests || "0";
    }
    if (responseTime) {
      responseTime.textContent = metrics.averageResponseTime || "N/A";
    }
    if (documentCount) {
      documentCount.textContent = metrics.documentsProcessed || "0";
    }
    if (systemHealth) {
      systemHealth.textContent = metrics.systemHealth || "Unknown";
      // Color code the health status
      systemHealth.style.color =
        metrics.systemHealth === "healthy"
          ? "var(--success)"
          : metrics.systemHealth === "offline"
          ? "var(--error)"
          : "var(--text-secondary)";
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

    // Reformat existing metadata with new theme
    this.refreshMetadataFormatting();
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

  refreshMetadataFormatting() {
    // Refresh all existing metadata formatting when theme changes
    console.log("Refreshing metadata formatting after theme change");

    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    const messages = chatMessages.querySelectorAll(
      ".message.assistant-message"
    );
    console.log(
      `Refreshing formatting for ${messages.length} assistant messages`
    );

    messages.forEach((messageDiv, index) => {
      const messageText = messageDiv.querySelector(".message-text");
      if (messageText) {
        // Remove any existing metadata labels to prevent duplicates
        const existingLabels = messageText.querySelectorAll(".metadata-label");
        existingLabels.forEach((label) => label.remove());

        // Reapply formatting with current theme
        this.applyMetadataFormatting(messageText);
        console.log(`Refreshed formatting for message ${index + 1}`);
      }
    });

    // Also fix existing metadata formatting to ensure consistency
    // Small delay to ensure theme classes are applied
    setTimeout(() => {
      this.fixExistingMetadataFormatting();
    }, 100);

    console.log("Metadata formatting refresh completed");
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

  // Example method to get the flag for backend communication
  isWolframEnabled() {
    return this.wolframEnabled;
  }

  // Finance News functionality
  async loadFinanceNews(forceRefresh = false) {
    const newsGrid = document.getElementById("news-grid");
    const newsLastUpdated = document.getElementById("news-last-updated");
    const refreshButton = document.getElementById("refresh-news");

    if (!newsGrid) return;

    // Show loading state if forcing refresh or no news loaded
    if (forceRefresh || !this.lastNewsUpdate) {
      newsGrid.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading latest finance news...</p>
        </div>
      `;

      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML =
          '<i class="fas fa-sync-alt fa-spin"></i> Loading...';
      }
    }

    try {
      const result = await window.apiService.getFinanceNews();

      if (result.success && result.articles.length > 0) {
        this.renderFinanceNews(result.articles);
        this.lastNewsUpdate = new Date().toISOString();

        if (newsLastUpdated) {
          newsLastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }

        // Set up auto-refresh interval (1 minute)
        this.startNewsAutoRefresh();
      } else {
        throw new Error(result.error || "Failed to load news");
      }
    } catch (error) {
      console.error("Failed to load finance news:", error);
      newsGrid.innerHTML = `
        <div class="error-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>Failed to load news</h3>
          <p>${
            error.message || "Unable to fetch finance news. Please try again."
          }</p>
          <button class="btn btn-primary" onclick="window.uiComponents.loadFinanceNews(true)">
            <i class="fas fa-retry"></i> Retry
          </button>
        </div>
      `;

      if (newsLastUpdated) {
        newsLastUpdated.textContent = "Failed to update";
      }
    } finally {
      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
      }
    }
  }

  renderFinanceNews(articles) {
    const newsGrid = document.getElementById("news-grid");
    if (!newsGrid) return;

    // Sort articles by publication date (newest first) as a backup
    const sortedArticles = [...articles].sort((a, b) => {
      try {
        const dateA = new Date(a.published);
        const dateB = new Date(b.published);
        return dateB - dateA; // Newest first
      } catch (error) {
        console.warn("Error sorting articles by date:", error);
        return 0;
      }
    });

    newsGrid.innerHTML = sortedArticles
      .map((article) => this.createNewsItem(article))
      .join("");
  }

  createNewsItem(article) {
    const publishedDate = new Date(article.published);
    const timeAgo = this.getTimeAgo(publishedDate);

    // Create image HTML if image URL is available
    const imageHtml = article.image_url
      ? `
      <div class="news-image">
        <img src="${Utils.escapeHtml(article.image_url)}" 
             alt="${Utils.escapeHtml(article.title)}"
             loading="lazy"
             onerror="this.style.display='none'"
             ${article.image_width ? `width="${article.image_width}"` : ""}
             ${article.image_height ? `height="${article.image_height}"` : ""}
        />
      </div>
    `
      : "";

    return `
      <div class="news-item" data-link="${article.link}">
        ${imageHtml}
        <div class="news-content">
          <h3 class="news-title">${Utils.escapeHtml(article.title)}</h3>
          <p class="news-summary">${Utils.escapeHtml(article.summary || "")}</p>
          <div class="news-meta">
            <span class="news-source">
              <i class="fas fa-building"></i>
              ${Utils.escapeHtml(article.source)}
            </span>
            <span class="news-time">
              <i class="fas fa-clock"></i>
              ${timeAgo}
            </span>
          </div>
        </div>
        <div class="news-actions">
          <button class="news-link-btn" title="Open article">
            <i class="fas fa-external-link-alt"></i>
          </button>
        </div>
      </div>
    `;
  }

  getTimeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 60) {
      return `${minutes}m ago`;
    } else if (hours < 24) {
      return `${hours}h ago`;
    } else {
      return `${days}d ago`;
    }
  }

  startNewsAutoRefresh() {
    // Clear existing interval
    if (this.newsRefreshInterval) {
      clearInterval(this.newsRefreshInterval);
    }

    // Set up new interval for 1 minute (60000 ms)
    this.newsRefreshInterval = setInterval(() => {
      if (this.currentTab === "news") {
        this.loadFinanceNews(true);
      }
    }, 60000);
  }

  stopNewsAutoRefresh() {
    if (this.newsRefreshInterval) {
      clearInterval(this.newsRefreshInterval);
      this.newsRefreshInterval = null;
    }
  }
}

// Export for global access
window.UIComponents = UIComponents;

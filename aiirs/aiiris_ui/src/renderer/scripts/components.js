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
    
    // Subscribe to language changes
    if (window.languageService) {
      window.languageService.subscribe(() => {
        this.updateDynamicTexts();
      });
    }
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

    // Set language setting on load
    if (window.languageService) {
      const languageSetting = document.getElementById("language-setting");
      if (languageSetting) {
        languageSetting.value = window.languageService.getCurrentLanguage();
      }
      // Update texts with current language
      window.languageService.updatePageTexts();
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
    }

    // Language setting change
    const languageSetting = document.getElementById("language-setting");
    if (languageSetting) {
      languageSetting.addEventListener("change", (e) => {
        if (window.languageService) {
          window.languageService.setLanguage(e.target.value);
        }
      });
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

    try {
      // Show typing indicator
      this.showTypingIndicator(); // Send to backend
      const response = await window.apiService.sendQuery(
        message,
        this.webSearchEnabled,
        this.wolframEnabled,
        this.currentSessionId
      );

      // Remove typing indicator
      this.hideTypingIndicator();

      // Check if response is valid
      if (!response || !response.success) {
        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        const errorMsg = response?.error || "Failed to get response from AI";
        this.addMessageToChat(
          "error",
          `${t('sorryError')} ${errorMsg}`
        );
        return;
      }

      // Ensure we have actual response content
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      const assistantResponse =
        response.response ||
        response.data?.response ||
        t('apologizeResponse');

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

      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      let errorMessage = t('sorryEncounteredError');
      if (error.message) {
        if (error.message.includes("timeout")) {
          errorMessage = t('requestTookTooLong');
        } else if (
          error.message.includes("fetch") ||
          error.message.includes("network")
        ) {
          errorMessage = t('connectionErrorCheck');
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
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
    this.addMessageToChat(
      "assistant",
      t('welcomeAssistantMessage')
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

    messages.forEach((messageDiv) => {
      const messageText = messageDiv.querySelector(".message-text");
      if (!messageText) return;

      // Check if metadata is already properly formatted
      const hasFormattedMetadata = messageText.querySelector("pre code");
      const hasMetadataLabel = messageText.querySelector(".metadata-label");

      const currentContent = messageText.textContent || messageText.innerText;

      // More flexible check for metadata presence
      const metadataIndicators = [
        "Kullanılan Bilgi Metadataları:",
        "🗂️",
        "📊",
        "Kaynak:",
        "İşlem Durumu:",
        "Kategori:",
        "Belirtilmiş",
      ];

      const hasMetadata = metadataIndicators.some((indicator) =>
        currentContent.includes(indicator)
      );

      if (hasMetadata) {
        // If already has formatted metadata with label, skip
        if (hasFormattedMetadata && hasMetadataLabel) {
          return;
        }

        // Remove any existing metadata labels first
        const existingLabels = messageText.querySelectorAll(".metadata-label");
        existingLabels.forEach((label) => label.remove());

        // Get the raw HTML content to preserve any existing formatting
        const rawHtml = messageText.innerHTML;

        // Check if already formatted as code block
        const alreadyFormatted =
          rawHtml.includes("<pre>") &&
          (rawHtml.includes("Kaynak:") || rawHtml.includes("İşlem Durumu:"));

        if (!alreadyFormatted) {
          // Reprocess this message content
          const formattedContent = this.formatMetadataContent(currentContent);

          try {
            const parsedContent = marked.parse(formattedContent);
            messageText.innerHTML = parsedContent;
          } catch (error) {
            console.warn("Failed to reformat existing message:", error);
          }
        }

        // Apply our styling to the formatted content
        this.applyMetadataFormatting(messageText);
      }
    });
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
                <div class="progress-header">
                    <div class="progress-status">
                        <i class="fas fa-clock progress-icon"></i>
                        <span class="progress-stage">Preparing...</span>
                    </div>
                    <div class="progress-percentage">0%</div>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 0%">
                            <div class="progress-shine"></div>
                        </div>
                    </div>
                </div>
                <div class="progress-details">
                    <span class="upload-speed"></span>
                    <span class="time-remaining"></span>
                </div>
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
    const progressPercentage = fileItem.querySelector(".progress-percentage");
    const progressStage = fileItem.querySelector(".progress-stage");
    const progressIcon = fileItem.querySelector(".progress-icon");
    const uploadSpeed = fileItem.querySelector(".upload-speed");
    const timeRemaining = fileItem.querySelector(".time-remaining");

    // Show progress container
    progressElement.style.display = "block";
    
    // Track timing for speed calculation
    const startTime = Date.now();
    let lastTime = startTime;
    let lastLoaded = 0;

    try {
      // Stage 1: Preparing file
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      this.updateProgressStage(progressIcon, progressStage, "fas fa-cog fa-spin", t('preparingFile'));
      await this.animateProgress(progressFill, progressPercentage, 0, 10, 500);

      // Stage 2: Reading file
      this.updateProgressStage(progressIcon, progressStage, "fas fa-file-alt", t('readingFile'));
      
      // Read file with progress simulation
      let fileBuffer;
      await this.simulateAsyncOperation(
        async () => {
          fileBuffer = await file.arrayBuffer();
        },
        (progress) => {
          const currentProgress = 10 + (progress * 0.15); // 10% to 25%
          this.animateProgress(progressFill, progressPercentage, null, currentProgress, 100);
        },
        Math.max(500, Math.min(2000, file.size / 1000)) // Dynamic duration based on file size
      );

      // Stage 3: Uploading
      this.updateProgressStage(progressIcon, progressStage, "fas fa-cloud-upload-alt", t('uploading'));
      
      let uploadResponse;
      await this.simulateAsyncOperation(
        async () => {
          uploadResponse = await window.apiService.uploadFile(file);
        },
        (progress) => {
          const currentProgress = 25 + (progress * 0.45); // 25% to 70%
          const currentTime = Date.now();
          const deltaTime = currentTime - lastTime;
          const deltaLoaded = (progress - lastLoaded) * file.size;
          
          if (deltaTime > 100) { // Update speed every 100ms
            const speed = deltaLoaded / deltaTime * 1000; // bytes per second
            const remaining = file.size * (1 - progress);
            const eta = remaining / speed;
            
            uploadSpeed.textContent = this.formatSpeed(speed);
            timeRemaining.textContent = this.formatTime(eta);
            
            lastTime = currentTime;
            lastLoaded = progress;
          }
          
          this.animateProgress(progressFill, progressPercentage, null, currentProgress, 100);
        },
        Math.max(1000, Math.min(5000, file.size / 500)) // Dynamic duration based on file size
      );

      // Stage 4: Processing
      this.updateProgressStage(progressIcon, progressStage, "fas fa-brain fa-pulse", t('processingWithAI'));
      uploadSpeed.textContent = "";
      timeRemaining.textContent = "";
      
      // Processing stage (AI processing happens in background)
      await this.simulateAsyncOperation(
        async () => {
          // Wait a bit more to show processing stage
          await new Promise(resolve => setTimeout(resolve, 1000));
        },
        (progress) => {
          const currentProgress = 70 + (progress * 0.25); // 70% to 95%
          this.animateProgress(progressFill, progressPercentage, null, currentProgress, 100);
        },
        2000
      );

      // Stage 5: Complete
      this.updateProgressStage(progressIcon, progressStage, "fas fa-check", t('uploadComplete'));
      await this.animateProgress(progressFill, progressPercentage, null, 100, 500);

      // Success styling
      fileItem.classList.add("upload-success");
      progressFill.style.background = "linear-gradient(90deg, #10b981, #34d399)";
      
      // Calculate total time
      const totalTime = Date.now() - startTime;
      const avgSpeed = file.size / (totalTime / 1000);
      uploadSpeed.textContent = `${t('avgSpeed')}: ${this.formatSpeed(avgSpeed)}`;
      timeRemaining.textContent = `${t('completedIn')} ${this.formatTime(totalTime / 1000)}`;

      // Remove after delay
      setTimeout(() => {
        fileItem.style.opacity = "0";
        fileItem.style.transform = "translateX(100%)";
        setTimeout(() => {
          fileItem.remove();
          this.updateUploadButton();
        }, 300);
      }, 3000);

      this.uploadedFiles.push({
        name: file.name,
        size: file.size,
        uploadDate: new Date(),
        id: uploadResponse.file_id || Utils.generateId(),
      });

    } catch (error) {
      // Error state
      fileItem.classList.add("upload-error");
      this.updateProgressStage(progressIcon, progressStage, "fas fa-exclamation-triangle", t('uploadFailed'));
      progressFill.style.background = "linear-gradient(90deg, #ef4444, #f87171)";
      uploadSpeed.textContent = "";
      timeRemaining.textContent = t('errorOccurred');
      console.error("Upload error:", error);
      
      // Show retry option
      setTimeout(() => {
        const retryButton = document.createElement("button");
        retryButton.className = "retry-upload-btn";
        retryButton.innerHTML = `<i class="fas fa-redo"></i> ${t('retry')}`;
        retryButton.onclick = () => {
          fileItem.classList.remove("upload-error");
          this.uploadFile(file, fileItem);
        };
        fileItem.querySelector(".progress-details").appendChild(retryButton);
      }, 1000);
    }
  }

  updateProgressStage(iconElement, stageElement, iconClass, stageText) {
    iconElement.className = `${iconClass} progress-icon`;
    stageElement.textContent = stageText;
  }

  async animateProgress(fillElement, percentageElement, fromWidth, toWidth, duration) {
    return new Promise(resolve => {
      const startWidth = fromWidth !== null ? fromWidth : parseFloat(fillElement.style.width) || 0;
      const startTime = Date.now();
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function for smooth animation
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentWidth = startWidth + (toWidth - startWidth) * easeProgress;
        
        fillElement.style.width = `${currentWidth}%`;
        if (percentageElement) {
          percentageElement.textContent = `${Math.round(currentWidth)}%`;
        }
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          resolve();
        }
      };
      
      requestAnimationFrame(animate);
    });
  }

  async simulateAsyncOperation(operation, progressCallback, duration) {
    const startTime = Date.now();
    
    // Start the actual operation
    const operationPromise = operation();
    
    // Simulate progress updates
    const progressInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      progressCallback(progress);
      
      if (progress >= 1) {
        clearInterval(progressInterval);
      }
    }, 50);
    
    // Wait for either the operation to complete or the duration to pass
    await Promise.all([
      operationPromise,
      new Promise(resolve => setTimeout(resolve, duration))
    ]);
    
    clearInterval(progressInterval);
    progressCallback(1); // Ensure we end at 100%
  }

  formatSpeed(bytesPerSecond) {
    if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`;
    if (bytesPerSecond < 1024 * 1024) return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
    return `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`;
  }

  formatTime(seconds) {
    if (seconds < 1) return "< 1s";
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
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
        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        fileLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-folder-open"></i>
          <h3>${t('noDocuments')}</h3>
          <p>${t('uploadToGetStarted')}</p>
          <button class="cta-button" data-tab="upload">${t('uploadFilesBtn')}</button>
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
          <div class="file-card-preview" id="preview-${Utils.escapeHtml(file.name).replace(/[^a-zA-Z0-9]/g, '_')}">
            <div class="preview-loading">
              <i class="fas fa-spinner fa-spin"></i>
              <span data-i18n="previewLoading">Loading preview...</span>
            </div>
          </div>
        `;

        // Add click handler to open file (but not on action buttons)
        fileItem.addEventListener("click", (e) => {
          // Don't open file if clicking on action buttons or preview area
          if (!e.target.closest(".file-card-actions") && !e.target.closest(".file-card-preview")) {
            this.openFile(file.name);
          }
        });

        fileLibrary.appendChild(fileItem);
        
        // Load preview for this file
        this.loadFilePreview(file.name);
      });
    } catch (error) {
      const fileLibrary = document.getElementById("files-grid");
      if (fileLibrary) {
        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        fileLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>${t('error')}</h3>
          <p>${t('networkError')}</p>
        </div>`;
      }
      console.error("Error loading file library:", error);
    }
  }

  async loadFilePreview(fileName) {
    const previewId = `preview-${fileName.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const previewElement = document.getElementById(previewId);
    
    if (!previewElement) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/api/files/${encodeURIComponent(fileName)}/preview`
      );
      
      if (!response.ok) {
        throw new Error(`Failed to load preview: ${response.statusText}`);
      }
      
      const previewData = await response.json();
      this.renderFilePreview(previewElement, previewData);
    } catch (error) {
      console.error(`Error loading preview for ${fileName}:`, error);
      previewElement.innerHTML = `
        <div class="preview-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>Preview unavailable: ${Utils.escapeHtml(error.message || 'Network error')}</span>
        </div>
      `;
    }
  }

  renderFilePreview(previewElement, previewData) {
    if (!previewData.success) {
      previewElement.innerHTML = `
        <div class="preview-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>Preview error: ${Utils.escapeHtml(previewData.error || 'Unknown error')}</span>
        </div>
      `;
      return;
    }

    const { preview_type, preview_data } = previewData;

    switch (preview_type) {
      case 'image':
        previewElement.innerHTML = `
          <div class="preview-image">
            <img src="${preview_data}" alt="Document preview" />
          </div>
        `;
        break;
        
      case 'text':
        previewElement.innerHTML = `
          <div class="preview-text">
            <pre>${Utils.escapeHtml(preview_data)}</pre>
          </div>
        `;
        break;
        
      case 'excel':
        previewElement.innerHTML = `
          <div class="preview-excel">
            <div class="excel-summary">
              <strong>${preview_data.columns.length} columns, ${preview_data.rows_shown} rows</strong>
            </div>
            <div class="excel-data">${preview_data.html}</div>
          </div>
        `;
        break;
        
      case 'info':
        previewElement.innerHTML = `
          <div class="preview-info">
            <i class="fas fa-info-circle"></i>
            <span>${Utils.escapeHtml(preview_data)}</span>
          </div>
        `;
        break;
        
      case 'error':
        previewElement.innerHTML = `
          <div class="preview-error">
            <i class="fas fa-exclamation-triangle"></i>
            <span>${Utils.escapeHtml(preview_data)}</span>
          </div>
        `;
        break;
        
      default:
        previewElement.innerHTML = `
          <div class="preview-info">
            <i class="fas fa-file"></i>
            <span>Preview not available</span>
          </div>
        `;
    }
  }

  async openFile(fileName) {
    try {
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      
      // Try to open the file using Electron's API
      if (window.airisAPI && window.airisAPI.openFile) {
        try {
          await window.airisAPI.openFile(fileName);
          this.showNotification(`${t('openedFile')} ${fileName}`, "success");
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
        this.showNotification(`${t('downloadingFile')} ${fileName}...`, "info");
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
            )}) - ${t('unableToOpenDirectly')}`,
            "warning"
          );
        } else {
          throw new Error("Unable to access file");
        }
      }
    } catch (error) {
      console.error("Error opening file:", error);
      this.showNotification(
        `${t('failedToOpenFile')} ${fileName}. ${t('sorryEncounteredError')}`,
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
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      this.showNotification(t('deletingFile'), "info");

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
    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;

    fileElement.innerHTML = `
            <div class="file-icon">
                <i class="${fileIcon}"></i>
            </div>
            <div class="file-details">
                <div class="file-name">${Utils.escapeHtml(file.name)}</div>
                <div class="file-meta">
                    <span class="file-size">${fileSize}</span>
                    <span class="file-date">${t('uploadedOn')} ${uploadDate}</span>
                </div>
            </div>
            <div class="file-actions">
                <button class="action-btn" onclick="window.uiComponents.downloadFile('${
                  file.id
                }')" title="${t('downloadFile')}">
                    <i class="fas fa-download"></i>
                </button>
                <button class="action-btn delete" onclick="window.uiComponents.deleteFile('${
                  file.id
                }')" title="${t('deleteFile')}">
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
    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
    if (!confirm(t('areYouSureDelete'))) return;

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

    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
    
    if (apiRequests) {
      apiRequests.textContent = metrics.apiRequests || "0";
    }
    if (responseTime) {
      responseTime.textContent = metrics.averageResponseTime || t('notAvailable');
    }
    if (documentCount) {
      documentCount.textContent = metrics.documentsProcessed || "0";
    }
    if (systemHealth) {
      systemHealth.textContent = metrics.systemHealth || t('unknown');
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
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      activityList.innerHTML =
        `<div class="no-activity">${t('noActivity')}</div>`;
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
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    const metadataBlocks = chatMessages.querySelectorAll("pre");
    metadataBlocks.forEach((preBlock) => {
      // Remove existing labels to prevent duplicates
      const existingLabels = preBlock.querySelectorAll(".metadata-label");
      existingLabels.forEach((label) => label.remove());

      // Get the parent message container and reapply formatting
      const messageContainer = preBlock.closest(".message-text");
      if (messageContainer) {
        this.applyMetadataFormatting(messageContainer);
      }
    });
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
    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
    this.showNotification(t('settingsSavedSuccessfully'), "success");
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
    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
    this.addMessageToChat(
      "assistant",
      t('welcomeAssistantMessage')
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
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      newsGrid.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <p>${t('loadingLatestNews')}</p>
        </div>
      `;

      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML =
          `<i class="fas fa-sync-alt fa-spin"></i> ${t('loading')}`;
      }
    }

    try {
      const result = await window.apiService.getFinanceNews();

      if (result.success && result.articles.length > 0) {
        this.renderFinanceNews(result.articles);
        this.lastNewsUpdate = new Date().toISOString();

        if (newsLastUpdated) {
          const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
          newsLastUpdated.textContent = `${t('lastUpdatedAt')} ${new Date().toLocaleTimeString()}`;
        }

        // Set up auto-refresh interval (1 minute)
        this.startNewsAutoRefresh();
      } else {
        throw new Error(result.error || "Failed to load news");
      }
    } catch (error) {
      console.error("Failed to load finance news:", error);
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      newsGrid.innerHTML = `
        <div class="error-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>${t('failedToLoadNews')}</h3>
          <p>${
            error.message || t('unableToFetchNews')
          }</p>
          <button class="btn btn-primary" onclick="window.uiComponents.loadFinanceNews(true)">
            <i class="fas fa-retry"></i> ${t('retryAction')}
          </button>
        </div>
      `;

      if (newsLastUpdated) {
        newsLastUpdated.textContent = t('failedToUpdate');
      }
    } finally {
      if (refreshButton) {
        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        refreshButton.disabled = false;
        refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t('refresh')}`;
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

    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;

    if (minutes < 60) {
      return `${minutes}${t('minutesAgo')}`;
    } else if (hours < 24) {
      return `${hours}${t('hoursAgo')}`;
    } else {
      return `${days}${t('daysAgo')}`;
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

  updateDynamicTexts() {
    if (!window.languageService) return;

    const t = window.languageService.t.bind(window.languageService);

    // Update suggestion chips
    const chips = document.querySelectorAll('.suggestion-chip');
    chips.forEach((chip, index) => {
      const chipKeys = ['suggestedQuestions.latestReport', 'suggestedQuestions.analyzeTrends', 'suggestedQuestions.expenseSummary'];
      if (chipKeys[index]) {
        chip.textContent = t(chipKeys[index]);
      }
    });

    // Update upload progress stages
    this.updateProgressStage = (iconElement, stageElement, iconClass, stageText) => {
      iconElement.className = `${iconClass} progress-icon`;
      
      // Use translation for stage text
      let translatedText = stageText;
      if (stageText.includes('Preparing')) translatedText = t('preparing');
      else if (stageText.includes('Reading')) translatedText = t('readingFile');
      else if (stageText.includes('Uploading')) translatedText = t('uploading');
      else if (stageText.includes('Processing with AI')) translatedText = t('processingWithAI');
      else if (stageText.includes('complete')) translatedText = t('uploadComplete');
      else if (stageText.includes('failed')) translatedText = t('uploadFailed');
      
      stageElement.textContent = translatedText;
    };

    // Update file deletion confirmation dialog
    this.deleteFile = async (fileName) => {
      try {
        const confirmed = confirm(t('deleteConfirmation', { filename: fileName }));
        if (!confirmed) return;

        this.showNotification(t('loading'), "info");

        const result = await fetch(
          `http://localhost:8000/api/files/${encodeURIComponent(fileName)}`,
          { method: "DELETE" }
        );

        if (!result.ok) {
          throw new Error(`Failed to delete file: ${result.statusText}`);
        }

        const data = await result.json();

        this.showNotification(t('fileDeletedSuccessfully', { filename: fileName }), "success");
        this.loadFileLibrary();
      } catch (error) {
        console.error("Error deleting file:", error);
        this.showNotification(t('failedToDeleteFile'), "error");
      }
    };

    // Update status texts
    const statusTexts = document.querySelectorAll('.status-text');
    statusTexts.forEach(status => {
      if (status.textContent.includes('Loading')) {
        status.textContent = t('loading');
      } else if (status.textContent.includes('Connected')) {
        status.textContent = t('connected');
      } else if (status.textContent.includes('Connecting')) {
        status.textContent = t('connecting');
      }
    });

    // Update empty states
    this.updateEmptyStates();

    // Update news refresh button text
    const refreshButton = document.getElementById('refresh-news');
    if (refreshButton && !refreshButton.disabled) {
      refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t('refresh')}`;
    }

    // Update analytics metrics with translations
    const responseTime = document.getElementById("response-time");
    const systemHealth = document.getElementById("system-health");
    if (responseTime && responseTime.textContent === 'N/A') {
      responseTime.textContent = t('notAvailable');
    }
    if (systemHealth && systemHealth.textContent === 'Unknown') {
      systemHealth.textContent = t('unknown');
    }

    // Refresh current tab content with new language
    if (this.currentTab === 'files') {
      this.loadFileLibrary();
    } else if (this.currentTab === 'news') {
      this.loadFinanceNews();
    } else if (this.currentTab === 'analytics') {
      this.loadAnalytics();
    }
  }

  updateEmptyStates() {
    if (!window.languageService) return;

    const t = window.languageService.t.bind(window.languageService);

    // Update file empty state
    const fileEmptyState = document.querySelector('#files-grid .empty-state');
    if (fileEmptyState) {
      const heading = fileEmptyState.querySelector('h3');
      const paragraph = fileEmptyState.querySelector('p');
      const button = fileEmptyState.querySelector('button');
      
      if (heading) heading.textContent = t('noDocuments');
      if (paragraph) paragraph.textContent = t('uploadToGetStarted');
      if (button) button.textContent = t('uploadFilesBtn');
    }

    // Update no activity state
    const noActivity = document.querySelector('.no-activity');
    if (noActivity && noActivity.textContent.includes('Loading')) {
      noActivity.textContent = t('loadingActivity');
    } else if (noActivity && noActivity.textContent.includes('No recent')) {
      noActivity.textContent = t('noActivity');
    }
  }
}

// Export for global access
window.UIComponents = UIComponents;

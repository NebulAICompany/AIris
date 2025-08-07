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

    // File selection management
    this.selectedFiles = [];
    this.allFiles = [];
    this.fileSelectionModal = null;

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

    // File selection button
    const fileSelectionBtn = document.getElementById("file-selection-btn");
    if (fileSelectionBtn) {
      fileSelectionBtn.addEventListener("click", () => this.showFileSelectionModal());
    }

    // File selection modal close
    const closeFileSelection = document.getElementById("close-file-selection");
    if (closeFileSelection) {
      closeFileSelection.addEventListener("click", () => this.hideFileSelectionModal());
    }

    // File selection controls
    const selectAllFiles = document.getElementById("select-all-files");
    if (selectAllFiles) {
      selectAllFiles.addEventListener("click", () => this.selectAllFiles());
    }

    const deselectAllFiles = document.getElementById("deselect-all-files");
    if (deselectAllFiles) {
      deselectAllFiles.addEventListener("click", () => this.deselectAllFiles());
    }

    // Prompt buttons
    const promptReport = document.getElementById("prompt-report");
    if (promptReport) {
      promptReport.addEventListener("click", () => this.insertPrompt("report"));
    }

    const promptAnalyze = document.getElementById("prompt-analyze");
    if (promptAnalyze) {
      promptAnalyze.addEventListener("click", () => this.insertPrompt("analyze"));
    }

    const promptSummarize = document.getElementById("prompt-summarize");
    if (promptSummarize) {
      promptSummarize.addEventListener("click", () => this.insertPrompt("summarize"));
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

      // Handle file selection item clicks
      if (e.target.closest(".file-selection-item")) {
        e.preventDefault();
        const fileItem = e.target.closest(".file-selection-item");
        const fileName = fileItem.dataset.filename;
        if (fileName) {
          this.toggleFileSelection(fileName);
        }
      }

      // Handle modal backdrop clicks
      if (e.target.classList.contains("file-selection-modal")) {
        this.hideFileSelectionModal();
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
      case "verification":
        await this.loadVerificationTab();
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
        this.currentSessionId,
        2, // maxRetries
        this.selectedFiles.length > 0 ? this.selectedFiles : null // selectedFiles
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

      // Extract images from response
      const images = response.images || [];
      
      console.log(`Received response with ${images.length} images`);

      // Update session ID if it was created server-side
      if (response.sessionId && response.sessionId !== this.currentSessionId) {
        this.currentSessionId = response.sessionId;
        // Refresh sessions list to show the new session
        await this.loadChatSessions();
      }

      // Add AI response to chat with images
      this.addMessageToChat("assistant", assistantResponse, images);

      // Update chat history
      this.chatHistory.push({ 
        user: message, 
        assistant: assistantResponse,
        images: images 
      });
    } catch (error) {
      this.hideTypingIndicator();


      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      let errorMessage = t('sorryEncounteredError');
      if (error.message) {
        if (error.message.includes("timeout")) {
          errorMessage = t('requestTookTooLong');

        } else if (
          error.message.includes("fetch") ||
          error.message.includes("network") ||
          error.message.includes("bağlan")
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

  // Enhanced query sending with retry logic
  async sendQueryWithRetry(
    message,
    webSearchEnabled,
    wolframEnabled,
    sessionId,
    maxRetries = 2,
    selectedFiles = null
  ) {
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`[Chat] Sending query attempt ${attempt}/${maxRetries}`);

        const response = await window.apiService.sendQuery(
          message,
          webSearchEnabled,
          wolframEnabled,
          sessionId,
          selectedFiles
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

  addMessageToChat(type, content, images = []) {
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

    // Add images if any (yeni özellik)
    if (images && images.length > 0) {
      console.log(`Adding ${images.length} images to message`);
      
      const imagesContainer = document.createElement("div");
      imagesContainer.className = "message-images";
      imagesContainer.style.cssText = `
        margin-top: 12px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 12px;
        background: rgba(0, 0, 0, 0.02);
        border-radius: 8px;
        border: 1px solid rgba(0, 0, 0, 0.1);
      `;
      
      images.forEach((image, index) => {
        const imageWrapper = document.createElement("div");
        imageWrapper.className = "message-image-wrapper";
        imageWrapper.style.cssText = `
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 6px;
        `;
        
        const img = document.createElement("img");
        img.src = `data:${image.type || 'image/jpeg'};base64,${image.data}`;
        img.alt = `Attached Image: ${image.filename}`;
        img.className = "message-image";
        img.style.cssText = `
          max-width: 400px;
          max-height: 300px;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          cursor: pointer;
          transition: all 0.3s ease;
          object-fit: contain;
          background: white;
          border: 2px solid transparent;
        `;
        
        // Hover effects
        img.addEventListener('mouseenter', () => {
          img.style.transform = 'scale(1.02)';
          img.style.boxShadow = '0 6px 20px rgba(0,0,0,0.25)';
          img.style.borderColor = 'var(--accent-primary, #007bff)';
        });
        
        img.addEventListener('mouseleave', () => {
          img.style.transform = 'scale(1)';
          img.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
          img.style.borderColor = 'transparent';
        });
        
        // Click to expand functionality
        img.addEventListener('click', () => {
          this.showImageModal(image);
        });
        
        const caption = document.createElement("div");
        caption.className = "image-caption";
        caption.textContent = `📎 ${image.filename}`;
        caption.style.cssText = `
          font-size: 0.75em;
          color: #666;
          font-family: 'Segoe UI', system-ui, sans-serif;
          background: rgba(255, 255, 255, 0.9);
          padding: 4px 8px;
          border-radius: 4px;
          border: 1px solid rgba(0, 0, 0, 0.1);
          max-width: 400px;
          word-break: break-all;
          font-weight: 500;
        `;
        
        imageWrapper.appendChild(img);
        imageWrapper.appendChild(caption);
        imagesContainer.appendChild(imageWrapper);
      });
      
      // Images container'ını message content'in içine ekle
      const messageContent = messageDiv.querySelector(".message-content");
      if (messageContent) {
        messageContent.appendChild(imagesContainer);
      }
    }

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

  // Image modal for full-size viewing
  showImageModal(image) {
    // Remove existing modal if any
    const existingModal = document.querySelector('.image-modal');
    if (existingModal) {
      document.body.removeChild(existingModal);
    }

    const modal = document.createElement("div");
    modal.className = "image-modal";
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.9);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      z-index: 10000;
      cursor: pointer;
      animation: fadeIn 0.3s ease;
    `;
    
    const img = document.createElement("img");
    img.src = `data:${image.type || 'image/jpeg'};base64,${image.data}`;
    img.style.cssText = `
      max-width: 95%;
      max-height: 85%;
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      object-fit: contain;
    `;
    
    const caption = document.createElement("div");
    caption.textContent = image.filename;
    caption.style.cssText = `
      color: white;
      font-size: 1.1em;
      margin-top: 16px;
      text-align: center;
      background: rgba(0, 0, 0, 0.7);
      padding: 8px 16px;
      border-radius: 20px;
      font-family: 'Segoe UI', system-ui, sans-serif;
    `;
    
    const closeButton = document.createElement("div");
    closeButton.innerHTML = '✕';
    closeButton.style.cssText = `
      position: absolute;
      top: 20px;
      right: 30px;
      color: white;
      font-size: 2em;
      cursor: pointer;
      background: rgba(0, 0, 0, 0.5);
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.3s ease;
    `;
    
    closeButton.addEventListener('mouseenter', () => {
      closeButton.style.background = 'rgba(255, 0, 0, 0.7)';
    });
    
    closeButton.addEventListener('mouseleave', () => {
      closeButton.style.background = 'rgba(0, 0, 0, 0.5)';
    });
    
    modal.appendChild(img);
    modal.appendChild(caption);
    modal.appendChild(closeButton);
    document.body.appendChild(modal);
    
    // Close modal events
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });
    
    closeButton.addEventListener('click', () => {
      document.body.removeChild(modal);
    });
    
    // ESC key to close
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        document.body.removeChild(modal);
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
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
          // Images are stored in message metadata or content
          const images = msg.images || [];
          
          this.addMessageToChat(msg.role, msg.content, images);

          // Update local chat history
          if (msg.role === "user") {
            this.chatHistory.push({ user: msg.content });
          } else if (msg.role === "assistant") {
            if (
              this.chatHistory.length > 0 &&
              !this.chatHistory[this.chatHistory.length - 1].assistant
            ) {
              this.chatHistory[this.chatHistory.length - 1].assistant = msg.content;
              this.chatHistory[this.chatHistory.length - 1].images = images;
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

  // Document Verification functionality
  setupVerificationEventListeners() {
    const verificationUploadArea = document.getElementById("verification-upload-area");
    const verificationFileInput = document.getElementById("verification-file-input");
    const verificationBrowseBtn = document.getElementById("verification-browse-files");
    const verifyDocumentBtn = document.getElementById("verify-document-btn");
    const verifyAnotherBtn = document.getElementById("verify-another-document");
    const downloadReportBtn = document.getElementById("download-verification-report");

    if (verificationUploadArea) {
      // Drag and drop functionality
      verificationUploadArea.addEventListener("dragover", this.handleVerificationDragOver.bind(this));
      verificationUploadArea.addEventListener("dragleave", this.handleVerificationDragLeave.bind(this));
      verificationUploadArea.addEventListener("drop", this.handleVerificationDrop.bind(this));
      verificationUploadArea.addEventListener("click", () => verificationFileInput?.click());
    }

    if (verificationBrowseBtn) {
      verificationBrowseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        verificationFileInput?.click();
      });
    }

    if (verificationFileInput) {
      verificationFileInput.addEventListener("change", this.handleVerificationFileSelect.bind(this));
    }

    if (verifyDocumentBtn) {
      verifyDocumentBtn.addEventListener("click", this.startDocumentVerification.bind(this));
    }

    if (verifyAnotherBtn) {
      verifyAnotherBtn.addEventListener("click", this.resetVerificationInterface.bind(this));
    }

    if (downloadReportBtn) {
      downloadReportBtn.addEventListener("click", this.downloadVerificationReport.bind(this));
    }

    // Initialize Wolfram Alpha toggle for verification
    const verificationWolframToggle = document.getElementById("verification-wolfram-toggle");
    if (verificationWolframToggle) {
      verificationWolframToggle.checked = Utils.isWolframEnabled();
      verificationWolframToggle.addEventListener("change", (e) => {
        Utils.setWolframEnabled(e.target.checked);
        console.log("Verification Wolfram Alpha enabled:", e.target.checked);
      });
    }
  }

  async loadVerificationTypes() {
    try {
      const result = await window.apiService.getVerificationTypes();
      
      if (result.success) {
        this.verificationTypes = result.verificationTypes;
        this.updateVerificationTypeSelect(result.verificationTypes);
      } else {
        console.warn("Failed to load verification types:", result.error);
      }
    } catch (error) {
      console.error("Error loading verification types:", error);
    }
  }

  updateVerificationTypeSelect(types) {
    const select = document.getElementById("verification-type");
    if (!select || !types) return;

    // Clear existing options except the first one (Auto Detect)
    const autoOption = select.querySelector('option[value="auto"]');
    select.innerHTML = "";
    if (autoOption) {
      select.appendChild(autoOption);
    }

    // Add options for each verification type
    Object.entries(types).forEach(([key, value]) => {
      if (key !== "auto") {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = `${value} (${key})`;
        select.appendChild(option);
      }
    });
  }

  handleVerificationDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    const uploadArea = document.getElementById("verification-upload-area");
    if (uploadArea) {
      uploadArea.classList.add("drag-over");
    }
  }

  handleVerificationDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    const uploadArea = document.getElementById("verification-upload-area");
    if (uploadArea && !uploadArea.contains(e.relatedTarget)) {
      uploadArea.classList.remove("drag-over");
    }
  }

  handleVerificationDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const uploadArea = document.getElementById("verification-upload-area");
    if (uploadArea) {
      uploadArea.classList.remove("drag-over");
    }

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      this.handleVerificationFiles(files);
    }
  }

  handleVerificationFileSelect(e) {
    const files = Array.from(e.target.files);
    this.handleVerificationFiles(files);
  }

  handleVerificationFiles(files) {
    if (files.length === 0) return;

    // Take only the first file for verification
    const file = files[0];
    
    // Check file type
    const allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      this.showNotification(
        `${t('unsupportedFileType')}: ${fileExtension}. ${t('verificationSupportedFormats')}`, 
        "error"
      );
      return;
    }

    // Store the selected file and enable verification button
    this.selectedVerificationFile = file;
    this.updateVerificationUI(file);
  }

  updateVerificationUI(file) {
    const uploadArea = document.getElementById("verification-upload-area");
    const verifyBtn = document.getElementById("verify-document-btn");
    
    if (uploadArea && file) {
      uploadArea.classList.add("file-hover");
      const uploadIcon = uploadArea.querySelector(".upload-icon i");
      if (uploadIcon) {
        uploadIcon.className = "fas fa-file-check";
      }
      
      const uploadText = uploadArea.querySelector("h3");
      if (uploadText) {
        uploadText.textContent = `Selected: ${file.name}`;
      }
    }

    if (verifyBtn) {
      verifyBtn.disabled = !file;
    }
  }

  async startDocumentVerification() {
    if (!this.selectedVerificationFile) {
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      this.showNotification(t('pleaseSelectFile'), "warning");
      return;
    }

    const verificationType = document.getElementById("verification-type")?.value || "auto";
    const wolframEnabled = document.getElementById("verification-wolfram-toggle")?.checked || false;
    const verifyBtn = document.getElementById("verify-document-btn");
    const resultsContainer = document.getElementById("verification-results");

    try {
      // Disable button and show loading state
      if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Verifying...</span>';
      }

      // Show progress indicator
      this.showVerificationProgress("Starting verification...");

      // Call verification API with Wolfram Alpha if enabled
      const result = await window.apiService.verifyDocument(
        this.selectedVerificationFile,
        verificationType,
        wolframEnabled,
        (progress, status) => {
          this.updateVerificationProgress(progress, status);
        }
      );

      // Hide progress indicator
      this.hideVerificationProgress();

      if (result.success) {
        // Show verification results
        this.displayVerificationResults(result.verificationResult);
        
        if (resultsContainer) {
          resultsContainer.style.display = "block";
          resultsContainer.scrollIntoView({ behavior: "smooth" });
        }

        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        this.showNotification(t('verificationCompleted'), "success");
      } else {
        throw new Error(result.error);
      }

    } catch (error) {
      console.error("Verification failed:", error);
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      this.showNotification(`${t('verificationFailed')}: ${error.message}`, "error");
      
      this.hideVerificationProgress();
    } finally {
      // Re-enable button
      if (verifyBtn) {
        verifyBtn.disabled = false;
        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        verifyBtn.innerHTML = `<i class="fas fa-shield-alt"></i> <span>${t('verifyDocument')}</span>`;
      }
    }
  }

  showVerificationProgress(message) {
    const uploadSection = document.querySelector(".verification-upload-section");
    if (!uploadSection) return;

    // Remove existing progress indicator
    const existingProgress = uploadSection.querySelector(".verification-progress");
    if (existingProgress) {
      existingProgress.remove();
    }

    // Create progress indicator
    const progressDiv = document.createElement("div");
    progressDiv.className = "verification-progress";
    progressDiv.innerHTML = `
      <i class="fas fa-spinner fa-spin"></i>
      <span class="verification-progress-text">${message}</span>
    `;

    uploadSection.appendChild(progressDiv);
  }

  updateVerificationProgress(progress, status) {
    const progressText = document.querySelector(".verification-progress-text");
    if (progressText && status) {
      progressText.textContent = status;
    }
  }

  hideVerificationProgress() {
    const progressDiv = document.querySelector(".verification-progress");
    if (progressDiv) {
      progressDiv.remove();
    }
  }

  displayVerificationResults(result) {
    this.currentVerificationResult = result;

    // Update status badge
    const statusBadge = document.getElementById("verification-status-badge");
    if (statusBadge) {
      statusBadge.textContent = result.status || "Unknown";
      statusBadge.className = `status-badge ${result.status || "processing"}`;
    }

    // Update confidence score
    this.updateConfidenceScore(result.confidence_score || 0);

    // Update verification details
    this.updateVerificationDetails(result);

    // Update verification stages
    this.updateVerificationStages(result.stages || {});

    // Show issues if any
    this.updateVerificationIssues(result.warnings || [], result.errors || []);
  }

  updateConfidenceScore(score) {
    const scoreValue = document.getElementById("verification-score-value");
    const scoreCircle = document.getElementById("verification-score-circle");
    
    if (scoreValue) {
      scoreValue.textContent = `${Math.round(score * 100)}%`;
    }

    if (scoreCircle) {
      // Update the conic gradient based on score
      const percentage = score * 360; // Convert to degrees
      const color = score >= 0.8 ? '#22c55e' : score >= 0.6 ? '#f59e0b' : '#ef4444';
      
      scoreCircle.style.background = `conic-gradient(
        ${color} 0deg,
        ${color} ${percentage}deg,
        var(--border-color) ${percentage}deg,
        var(--border-color) 360deg
      )`;
    }
  }

  updateVerificationDetails(result) {
    const detectedType = document.getElementById("detected-document-type");
    const finalStatus = document.getElementById("verification-final-status");
    const fraudRisk = document.getElementById("fraud-risk-level");

    if (detectedType) {
      detectedType.textContent = result.verification_type || "Unknown";
    }

    if (finalStatus) {
      finalStatus.textContent = result.status || "Unknown";
      finalStatus.className = `detail-value ${result.status}`;
    }

    if (fraudRisk) {
      const fraudLevel = result.stages?.fraud_analysis?.risk_level || "unknown";
      fraudRisk.textContent = fraudLevel;
      fraudRisk.className = `detail-value risk-${fraudLevel}`;
    }
  }

  updateVerificationStages(stages) {
    const stagesGrid = document.getElementById("verification-stages-grid");
    if (!stagesGrid) return;

    stagesGrid.innerHTML = "";

    const stageNames = {
      quality_control: "Quality Control",
      classification: "Document Classification", 
      text_extraction: "Text Extraction",
      template_validation: "Template Validation",
      data_consistency: "Data Consistency",
      fraud_analysis: "Fraud Analysis"
    };

    Object.entries(stages).forEach(([stageName, stageData]) => {
      const stageCard = this.createStageCard(stageNames[stageName] || stageName, stageData);
      stagesGrid.appendChild(stageCard);
    });
  }

  createStageCard(stageName, stageData) {
    const card = document.createElement("div");
    card.className = "stage-card";

    // Determine stage status
    let stageStatus = "warning";
    let statusIcon = "fas fa-exclamation-triangle";
    
    if (stageData.passed || stageData.valid || stageData.consistent || stageData.risk_level === "low") {
      stageStatus = "passed";
      statusIcon = "fas fa-check";
    } else if (stageData.failed || stageData.risk_level === "high") {
      stageStatus = "failed";
      statusIcon = "fas fa-times";
    }

    // Get stage score
    const score = stageData.score || stageData.confidence || stageData.quality_score || 0;
    const percentage = Math.round(score * 100);

    // Get stage details
    const issues = stageData.issues || stageData.indicators || [];
    const details = Array.isArray(issues) ? issues.join(", ") : 
                   stageData.assessment || stageData.reasoning || "No details available";

    card.innerHTML = `
      <div class="stage-header">
        <div class="stage-name">${stageName}</div>
        <div class="stage-status ${stageStatus}">
          <i class="${statusIcon}"></i>
        </div>
      </div>
      <div class="stage-details">${Utils.escapeHtml(details)}</div>
      <div class="stage-score">
        <span class="stage-score-label">Score</span>
        <span class="stage-score-value">${percentage}%</span>
      </div>
    `;

    return card;
  }

  updateVerificationIssues(warnings, errors) {
    const issuesContainer = document.getElementById("verification-issues");
    const issuesList = document.getElementById("verification-issues-list");

    const allIssues = [...warnings, ...errors];

    if (allIssues.length === 0) {
      if (issuesContainer) {
        issuesContainer.style.display = "none";
      }
      return;
    }

    if (issuesContainer) {
      issuesContainer.style.display = "block";
    }

    if (issuesList) {
      issuesList.innerHTML = allIssues.map(issue => `
        <div class="issue-item">
          <i class="fas fa-exclamation-triangle"></i>
          <span class="issue-text">${Utils.escapeHtml(issue)}</span>
        </div>
      `).join("");
    }
  }

  resetVerificationInterface() {
    // Reset file selection
    this.selectedVerificationFile = null;
    
    // Reset upload area
    const uploadArea = document.getElementById("verification-upload-area");
    const verifyBtn = document.getElementById("verify-document-btn");
    const resultsContainer = document.getElementById("verification-results");
    const fileInput = document.getElementById("verification-file-input");

    if (uploadArea) {
      uploadArea.classList.remove("file-hover");
      const uploadIcon = uploadArea.querySelector(".upload-icon i");
      if (uploadIcon) {
        uploadIcon.className = "fas fa-shield-alt";
      }
      
      const uploadText = uploadArea.querySelector("h3");
      if (uploadText) {
        const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
        uploadText.textContent = t('verificationDragDrop');
      }
    }

    if (verifyBtn) {
      verifyBtn.disabled = true;
    }

    if (resultsContainer) {
      resultsContainer.style.display = "none";
    }

    if (fileInput) {
      fileInput.value = "";
    }

    // Hide any progress indicators
    this.hideVerificationProgress();

    // Scroll back to top
    const verificationContainer = document.querySelector(".verification-container");
    if (verificationContainer) {
      verificationContainer.scrollIntoView({ behavior: "smooth" });
    }
  }

  downloadVerificationReport() {
    if (!this.currentVerificationResult) {
      const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
      this.showNotification(t('noVerificationDataToDownload'), "warning");
      return;
    }

    // Create a comprehensive report
    const report = {
      document_name: this.selectedVerificationFile?.name || "Unknown Document",
      verification_timestamp: new Date().toISOString(),
      verification_result: this.currentVerificationResult
    };

    // Convert to JSON and create download
    const reportJson = JSON.stringify(report, null, 2);
    const blob = new Blob([reportJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    // Create download link
    const a = document.createElement("a");
    a.href = url;
    a.download = `verification_report_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    const t = window.languageService ? window.languageService.t.bind(window.languageService) : (key) => key;
    this.showNotification(t('reportDownloaded'), "success");
  }

  // Initialize verification when tab loads
  async loadVerificationTab() {
    if (!this.verificationInitialized) {
      this.setupVerificationEventListeners();
      await this.loadVerificationTypes();
      this.verificationInitialized = true;
    }
  }

  // File Selection Modal Methods
  async showFileSelectionModal() {
    const modal = document.getElementById("file-selection-modal");
    if (!modal) return;

    // Store reference to modal
    this.fileSelectionModal = modal;

    // Load files if not already loaded
    await this.loadFilesForSelection();

    // Show modal with animation
    modal.classList.add("show");

    // Update file selection display
    this.updateFileSelectionDisplay();
  }

  hideFileSelectionModal() {
    const modal = document.getElementById("file-selection-modal");
    if (modal) {
      modal.classList.remove("show");
    }
    this.fileSelectionModal = null;
  }

  async loadFilesForSelection() {
    const filesList = document.getElementById("files-selection-list");
    if (!filesList) return;

    // Show loading state
    filesList.innerHTML = `
      <div class="loading-files">
        <i class="fas fa-spinner fa-spin"></i>
        <span>Loading files...</span>
      </div>
    `;

    try {
      // Fetch files from API
      const result = await window.apiService.getFiles();
      
      if (result.success && result.files) {
        this.allFiles = result.files;
        
        // Initialize selected files to all files if not already set
        if (this.selectedFiles.length === 0) {
          this.selectedFiles = this.allFiles.map(file => file.name);
        }

        this.renderFileSelectionList();
        this.updateFileSelectionButton();
      } else {
        throw new Error(result.error || "Failed to load files");
      }
    } catch (error) {
      console.error("Error loading files for selection:", error);
      filesList.innerHTML = `
        <div class="loading-files">
          <i class="fas fa-exclamation-triangle"></i>
          <span>Error loading files: ${error.message}</span>
        </div>
      `;
    }
  }

  renderFileSelectionList() {
    const filesList = document.getElementById("files-selection-list");
    if (!filesList || !this.allFiles) return;

    if (this.allFiles.length === 0) {
      filesList.innerHTML = `
        <div class="loading-files">
          <i class="fas fa-folder-open"></i>
          <span>No files available. Upload some files first.</span>
        </div>
      `;
      return;
    }

    filesList.innerHTML = this.allFiles.map(file => {
      const isSelected = this.selectedFiles.includes(file.name);
      const fileExtension = file.name.split('.').pop().toLowerCase();
      const fileIcon = this.getFileIcon(fileExtension);
      const fileSize = this.formatFileSize(file.size);

      return `
        <div class="file-selection-item ${isSelected ? 'selected' : ''}" data-filename="${file.name}">
          <div class="file-checkbox ${isSelected ? 'checked' : ''}">
            <i class="fas fa-check"></i>
          </div>
          <div class="file-item-icon ${fileExtension}">
            <i class="${fileIcon}"></i>
          </div>
          <div class="file-item-info">
            <div class="file-item-name" title="${file.name}">${file.name}</div>
            <div class="file-item-size">${fileSize}</div>
          </div>
        </div>
      `;
    }).join('');
  }

  getFileIcon(extension) {
    const iconMap = {
      'pdf': 'fas fa-file-pdf',
      'docx': 'fas fa-file-word',
      'doc': 'fas fa-file-word',
      'xlsx': 'fas fa-file-excel',
      'xls': 'fas fa-file-excel',
      'txt': 'fas fa-file-alt',
      'jpg': 'fas fa-file-image',
      'jpeg': 'fas fa-file-image',
      'png': 'fas fa-file-image',
      'gif': 'fas fa-file-image',
      'bmp': 'fas fa-file-image',
      'tiff': 'fas fa-file-image'
    };
    return iconMap[extension] || 'fas fa-file';
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  toggleFileSelection(fileName) {
    const index = this.selectedFiles.indexOf(fileName);
    
    if (index > -1) {
      // File is selected, remove it
      this.selectedFiles.splice(index, 1);
    } else {
      // File is not selected, add it
      this.selectedFiles.push(fileName);
    }

    // Update display
    this.updateFileSelectionDisplay();
    this.updateFileSelectionButton();
  }

  selectAllFiles() {
    this.selectedFiles = [...this.allFiles.map(file => file.name)];
    this.updateFileSelectionDisplay();
    this.updateFileSelectionButton();
  }

  deselectAllFiles() {
    this.selectedFiles = [];
    this.updateFileSelectionDisplay();
    this.updateFileSelectionButton();
  }

  updateFileSelectionDisplay() {
    // Update checkboxes and selection state
    const fileItems = document.querySelectorAll('.file-selection-item');
    
    fileItems.forEach(item => {
      const fileName = item.dataset.filename;
      const isSelected = this.selectedFiles.includes(fileName);
      const checkbox = item.querySelector('.file-checkbox');
      
      if (isSelected) {
        item.classList.add('selected');
        checkbox.classList.add('checked');
      } else {
        item.classList.remove('selected');
        checkbox.classList.remove('checked');
      }
    });
  }

  updateFileSelectionButton() {
    const button = document.getElementById("file-selection-btn");
    if (!button) return;

    const selectedCount = this.selectedFiles.length;
    const totalCount = this.allFiles.length;

    if (selectedCount === 0) {
      button.classList.remove('has-selection');
      button.removeAttribute('data-count');
      button.title = "Select files to include";
    } else if (selectedCount === totalCount) {
      button.classList.add('has-selection');
      button.setAttribute('data-count', 'All');
      button.title = `All ${totalCount} files selected`;
    } else {
      button.classList.add('has-selection');
      button.setAttribute('data-count', selectedCount);
      button.title = `${selectedCount} of ${totalCount} files selected`;
    }
  }

  insertPrompt(type) {
    const chatInput = document.getElementById("chat-input");
    if (!chatInput) return;

    let prompt = "";
    const selectedFilesList = this.selectedFiles.length > 0 
      ? `Selected files: ${this.selectedFiles.join(', ')}\n\n` 
      : "";

    switch (type) {
      case "report":
        prompt = `${selectedFilesList}Please write a comprehensive report about the content of the selected files. Include key insights, findings, and recommendations based on the data.`;
        break;
      case "analyze":
        prompt = `${selectedFilesList}Please analyze the content and numbers/statistics in the selected files. Identify trends, patterns, and provide detailed analysis of any financial data, metrics, or numerical information found.`;
        break;
      case "summarize":
        prompt = `${selectedFilesList}Please provide a concise summary of the selected files. Highlight the main points, key information, and essential details from each document.`;
        break;
      default:
        return;
    }

    // Insert prompt into chat input
    chatInput.value = prompt;
    
    // Hide modal
    this.hideFileSelectionModal();
    
    // Focus chat input
    chatInput.focus();
    
    // Enable send button
    this.toggleSendButton();
  }
}

// Export for global access
window.UIComponents = UIComponents;

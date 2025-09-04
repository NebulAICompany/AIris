/**
 * UI Components for AIris Electron App
 * Handles all user interface interactions and component management
 */

class UIComponents {
  constructor() {
    this.currentTab = "chat";
    this.chatHistory = [];
    this.uploadedFiles = [];
    this.chatUploadedFiles = []; // Add this property for chat uploads
    this.isProcessing = false;
    this.isDarkMode = false;
    // Add webSearchEnabled flag, initialize from storage or default to false
    this.webSearchEnabled = Utils.isWebSearchEnabled();

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
    // Theme loading moved to AIrisApp class to load before loading screen
    // this.loadTheme();
    this.initializeComponents();

    // Set toggle state on load
    const webSearchToggle = document.getElementById("web-search-toggle");
    if (webSearchToggle) {
      if (this.webSearchEnabled) {
        webSearchToggle.classList.add("active");
      }
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
      webSearchToggle.addEventListener("click", (e) => {
        e.preventDefault();
        this.webSearchEnabled = !this.webSearchEnabled;
        Utils.setWebSearchEnabled(this.webSearchEnabled);

        // Update button state
        if (this.webSearchEnabled) {
          webSearchToggle.classList.add("active");
        } else {
          webSearchToggle.classList.remove("active");
        }

        console.log("Web search enabled:", this.webSearchEnabled);
        // Optionally, notify backend here if needed
        // Example: window.airisAPI.setWebSearchEnabled?.(this.webSearchEnabled);
      });

      // Set initial state
      if (this.webSearchEnabled) {
        webSearchToggle.classList.add("active");
      }

      console.log("webSearchEnabled: ", this.webSearchEnabled);
    }

    // Finance News refresh button
    const refreshNewsButton = document.getElementById("refresh-news");
    if (refreshNewsButton) {
      refreshNewsButton.addEventListener("click", () =>
        this.refreshFinanceNews()
      );
    }

    // File selection button
    const fileSelectionBtn = document.getElementById("file-selection-btn");
    if (fileSelectionBtn) {
      fileSelectionBtn.addEventListener("click", () =>
        this.showFileSelectionModal()
      );
    }

    // Chat file upload listeners - UPDATED FOR CHAT INPUT DRAG & DROP
    const chatInputElement = document.getElementById("chat-input");
    const chatFileInput = document.getElementById("chat-file-input");

    // File input change
    if (chatFileInput) {
      chatFileInput.addEventListener("change", (e) =>
        this.handleNewFileSelect(e)
      );
    }

    // Drag and drop for chat input
    if (chatInputElement) {
      chatInputElement.addEventListener("dragover", (e) =>
        this.handleChatInputDragOver(e)
      );
      chatInputElement.addEventListener("dragleave", (e) =>
        this.handleChatInputDragLeave(e)
      );
      chatInputElement.addEventListener("drop", (e) =>
        this.handleChatInputDrop(e)
      );
    }

    // File attachment button (paperclip)
    const fileAttachmentBtn = document.getElementById("file-attachment-btn");
    if (fileAttachmentBtn) {
      fileAttachmentBtn.addEventListener("click", () => {
        chatFileInput?.click();
      });
    }

    // File selection modal close
    const closeFileSelection = document.getElementById("close-file-selection");
    if (closeFileSelection) {
      closeFileSelection.addEventListener("click", () =>
        this.hideFileSelectionModal()
      );
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
      promptAnalyze.addEventListener("click", () =>
        this.insertPrompt("analyze")
      );
    }

    const promptSummarize = document.getElementById("prompt-summarize");
    if (promptSummarize) {
      promptSummarize.addEventListener("click", () =>
        this.insertPrompt("summarize")
      );
    }

    // Removed keyboard shortcuts as requested by user

    // Event delegation for dynamic buttons
    document.addEventListener("click", (e) => {
      if (e.target.classList.contains("cta-button") && e.target.dataset.tab) {
        this.switchTab(e.target.dataset.tab);
      }

      // Handle markdown download links in chat messages
      if (
        e.target.tagName === "A" &&
        e.target.href &&
        e.target.href.includes("/api/created-documents/")
      ) {
        e.preventDefault();
        e.stopPropagation();

        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        const url = e.target.href;

        // Extract filename for notification
        const urlParts = url.split("/");
        const filename = decodeURIComponent(
          urlParts[urlParts.indexOf("created-documents") + 1]
        );

        // Open the download URL in a new tab/window
        window.open(url, "_blank");
        this.showNotification(`${t("downloadingFile")} ${filename}...`, "info");

        return;
      }

      // Handle delete button clicks
      if (e.target.closest(".delete-btn")) {
        e.preventDefault();
        e.stopPropagation();
        const deleteBtn = e.target.closest(".delete-btn");
        const fileName = deleteBtn.dataset.filename;
        if (fileName) {
          // Check if this is a created document or regular file based on context
          const fileCard = deleteBtn.closest(".file-card");
          if (fileCard && fileCard.closest("#created-documents-grid")) {
            // This is a created document
            this.deleteCreatedDocument(fileName);
          } else {
            // This is a regular file
            this.deleteFile(fileName);
          }
        }
      }

      // Handle news article clicks
      if (e.target.closest(".news-item")) {
        const newsItem = e.target.closest(".news-item");
        const articleIndex = newsItem.dataset.articleIndex;
        if (articleIndex !== undefined) {
          this.showNewsDetail(parseInt(articleIndex));
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

    // Calculator functionality
    const calculateBtn = document.getElementById("calculate-btn");
    const resetCalcBtn = document.getElementById("reset-calc-btn");
    const loanAmountInput = document.getElementById("loan-amount");
    const loanTermInput = document.getElementById("loan-term");
    const interestRateInput = document.getElementById("interest-rate");

    if (calculateBtn) {
      calculateBtn.addEventListener("click", () => this.calculateLoan());
    }

    if (resetCalcBtn) {
      resetCalcBtn.addEventListener("click", () => this.resetCalculator());
    }

    // Add Enter key support for calculator inputs
    [loanAmountInput, loanTermInput, interestRateInput].forEach((input) => {
      if (input) {
        input.addEventListener("keypress", (e) => {
          if (e.key === "Enter") {
            this.calculateLoan();
          }
        });
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
      case "created-documents":
        await this.loadCreatedDocumentsLibrary();
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
      const hasFiles =
        this.chatUploadedFiles && this.chatUploadedFiles.length > 0;
      sendButton.disabled = !(hasText || hasFiles) || this.isProcessing;
    }
  }

  async sendMessage() {
    const chatInput = document.getElementById("chat-input");
    const message = chatInput.value.trim();

    // Allow sending if there's either a message or files attached
    if (
      (!message &&
        (!this.chatUploadedFiles || this.chatUploadedFiles.length === 0)) ||
      this.isProcessing
    )
      return;

    this.isProcessing = true;
    chatInput.value = "";

    // Clear chat files preview immediately when send button is pressed
    const filesToUpload = [...this.chatUploadedFiles]; // Copy the files array
    this.chatUploadedFiles = []; // Clear the files array
    this.updateChatFilesPreview(); // Hide the preview immediately

    this.toggleSendButton();

    // Create new session if none exists
    if (!this.currentSessionId) {
      const sessionId = await this.createNewChatSession();
      if (!sessionId) {
        console.warn("Failed to create session, proceeding without session ID");
      }
    }

    // Add user message if there's text
    if (message) {
      this.addMessageToChat("user", message);
    }

    // Handle file uploads with status messages
    let uploadedFiles = [];
    if (filesToUpload.length > 0) {
      // Show uploading status for each file
      for (const file of filesToUpload) {
        this.addFileStatusMessage(file.name, "uploading");
      }

      // Upload files one by one
      for (let i = 0; i < filesToUpload.length; i++) {
        const file = filesToUpload[i];
        try {
          const response = await window.apiService.uploadFile(file);
          if (response.success) {
            uploadedFiles.push({
              name: file.name,
              size: file.size,
              id: response.data.file_id || response.data.filename,
            });

            // Update status to success
            this.updateFileStatusMessage(file.name, "success");
          } else {
            // Update status to error
            this.updateFileStatusMessage(file.name, "error", "Upload failed");
          }
        } catch (error) {
          console.error("Failed to upload file:", file.name, error);
          this.updateFileStatusMessage(file.name, "error", "Upload failed");
        }
      }
    }

    // Only send to AI if there's a text message
    if (message) {
      // Show enhanced typing indicator
      this.showEnhancedTypingIndicator(message);

      try {
        // Send to backend
        const response = await this.sendQueryWithRetry(
          message,
          this.webSearchEnabled,
          this.currentSessionId,
          2,
          uploadedFiles.length > 0 ? uploadedFiles : null
        );

        if (response) {
          // Extract response content properly from API response
          const responseContent =
            response.response || response.content || response.data?.response;
          const responseImages = response.images || response.data?.images || [];
          const responseCharts = response.charts || response.data?.charts || [];
          const responseGeneratedFiles =
            response.generatedFiles || response.data?.generatedFiles || [];

          if (responseContent) {
            this.addMessageToChat(
              "assistant",
              responseContent,
              responseImages,
              responseCharts,
              responseGeneratedFiles
            );
          } else {
            console.warn("Empty response received:", response);
            this.addMessageToChat(
              "assistant",
              "Response received but content was empty. Please try again."
            );
          }
        }
      } catch (error) {
        console.error("Chat error:", error);
        this.addMessageToChat(
          "error",
          "Sorry, there was an error processing your request. Please try again."
        );
      } finally {
        this.hideTypingIndicator();
      }
    }

    this.isProcessing = false;
    this.toggleSendButton();
    chatInput.focus();
  }

  // Enhanced query sending with retry logic
  async sendQueryWithRetry(
    message,
    webSearchEnabled,
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
    if (this.webSearchEnabled) {
      statusMessage = "Web araması yapılıyor...";
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

  addMessageToChat(
    type,
    content,
    images = [],
    charts = [],
    generatedFiles = []
  ) {
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
      // Simple content processing
      let processedContent = content || "No response received";

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

    // Add charts if provided (BEFORE the message content, so they appear above the response)
    if (charts && charts.length > 0) {
      const chartsContainer = document.createElement("div");
      chartsContainer.className = "message-charts";

      const chartsHeader = document.createElement("div");
      chartsHeader.className = "charts-header";
      chartsHeader.innerHTML = `
        <i class="fas fa-chart-line"></i>
        <span>Interactive Charts</span>
`;

      chartsContainer.appendChild(chartsHeader);

      charts.forEach((chart, index) => {
        const chartWrapper = document.createElement("div");
        chartWrapper.className = "message-chart-wrapper";

        // Create chart header with controls
        const chartHeader = document.createElement("div");
        chartHeader.className = "chart-header";

        // Create iframe for chart content
        const chartFrame = document.createElement("iframe");
        chartFrame.className = "message-chart";
        chartFrame.srcdoc = chart.data || chart.content; // Handle both possible field names
        chartFrame.style.cssText = `
          width: 100%;
          height: 600px;
          border: none;
          border-radius: 8px;
          background: white;
        `;

        // Add security attributes
        chartFrame.setAttribute("sandbox", "allow-scripts allow-same-origin");
        chartFrame.setAttribute("loading", "lazy");

        // Add loading placeholder effect
        chartFrame.addEventListener("load", () => {
          chartFrame.style.opacity = "1";
          chartWrapper.classList.add("loaded");
        });

        chartFrame.style.opacity = "0";
        chartFrame.style.transition = "opacity 0.5s ease";

        // Create fullscreen button
        const fullscreenBtn = document.createElement("button");
        fullscreenBtn.className = "chart-fullscreen-btn";
        fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
        fullscreenBtn.title = "Tam Ekran Yap";
        fullscreenBtn.addEventListener("click", () => {
          this.showChartFullscreen(chart, index);
        });

        // Create caption
        const caption = document.createElement("div");
        caption.className = "chart-caption";

        // Extract chart metadata for caption
        const chartInfo = [];
        if (chart.symbols && chart.symbols.length > 0) {
          chartInfo.push(`Symbols: ${chart.symbols.join(", ")}`);
        }
        if (chart.chart_type) {
          chartInfo.push(
            `Type: ${
              chart.chart_type.charAt(0).toUpperCase() +
              chart.chart_type.slice(1)
            }`
          );
        }
        if (chart.period) {
          chartInfo.push(
            `Period: ${
              chart.period.charAt(0).toUpperCase() + chart.period.slice(1)
            }`
          );
        }
        if (chart.time_range_days) {
          chartInfo.push(`Range: ${chart.time_range_days} days`);
        }

        caption.innerHTML =
          chartInfo.length > 0 ? chartInfo.join(" • ") : `Chart ${index + 1}`;

        // Add header with fullscreen button
        chartHeader.appendChild(fullscreenBtn);
        chartWrapper.appendChild(chartHeader);
        chartWrapper.appendChild(chartFrame);
        chartWrapper.appendChild(caption);
        chartsContainer.appendChild(chartWrapper);
      });

      // Charts container'ı message content'in en başına ekle (response metninden önce)
      const messageContent = messageDiv.querySelector(".message-content");
      if (messageContent) {
        messageContent.insertBefore(chartsContainer, messageContent.firstChild);
      }
    }

    chatMessages.appendChild(messageDiv);

    // Add attachments (images and generated files) if any (AFTER charts, so they appear below the response)
    if (
      (images && images.length > 0) ||
      (generatedFiles && generatedFiles.length > 0)
    ) {
      console.log(
        `Adding ${(images || []).length} images and ${
          (generatedFiles || []).length
        } generated files to message`
      );

      const attachmentsContainer = document.createElement("div");
      attachmentsContainer.className = "message-images"; // Keep existing class for styling

      // Add a header for the attachments section with toggle functionality
      // Add a minimal header for the attachments section with toggle functionality
      const attachmentsHeader = document.createElement("div");
      attachmentsHeader.className = "images-header";
      attachmentsHeader.innerHTML = `
        <i class="fas fa-paperclip" style="font-size: 0.9em; opacity: 0.7;"></i>
        <span style="font-size: 1em; opacity: 0.9;">${
          (images || []).length + (generatedFiles || []).length
        } attachment</span>
        <i class="fas fa-chevron-down toggle-icon" style="margin-left: auto; font-size: 0.8em; opacity: 0.6; cursor: pointer;"></i>
      `;
      attachmentsHeader.style.cssText = `
        grid-column: 1 / -1;
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75em;
        color: var(--text-secondary);
        margin: 8px 0 4px 0;
        padding: 6px 8px;
        border-radius: 6px;
        cursor: pointer;
        user-select: none;
        transition: background-color 0.2s ease;
      `;

      // Create minimal content container that will be toggleable
      const attachmentsContent = document.createElement("div");
      attachmentsContent.className = "attachments-content";
      attachmentsContent.style.cssText = `
        display: none;
        grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
        gap: 8px;
        padding: 4px 0;
        animation: slideDown 0.2s ease-out;
      `;

      // Add toggle functionality
      let isExpanded = false;
      const toggleIcon = attachmentsHeader.querySelector(".toggle-icon");

      attachmentsHeader.addEventListener("click", () => {
        isExpanded = !isExpanded;

        if (isExpanded) {
          attachmentsContent.style.display = "grid";
          toggleIcon.style.transform = "rotate(180deg)";
          toggleIcon.className = "fas fa-chevron-up toggle-icon";
        } else {
          attachmentsContent.style.display = "none";
          toggleIcon.style.transform = "rotate(0deg)";
          toggleIcon.className = "fas fa-chevron-down toggle-icon";
        }
      });

      attachmentsContainer.appendChild(attachmentsHeader);
      attachmentsContainer.appendChild(attachmentsContent);

      // Add images first
      if (images && images.length > 0) {
        images.forEach((image, index) => {
          const imageWrapper = document.createElement("div");
          imageWrapper.className = "message-image-wrapper";

          const img = document.createElement("img");
          img.src = `data:${image.type || "image/jpeg"};base64,${image.data}`;
          img.alt = `Attached Image: ${image.filename}`;
          img.className = "message-image";
          img.style.cssText = `
            max-width: 100%;
            max-height: 300px;
            object-fit: contain;
            cursor: pointer;
          `;

          // Add loading placeholder effect
          img.addEventListener("load", () => {
            img.style.opacity = "1";
          });

          img.style.opacity = "0";
          img.style.transition = "opacity 0.3s ease";

          // Click to expand functionality
          img.addEventListener("click", () => {
            this.showImageModal(image);
          });

          const caption = document.createElement("div");
          caption.className = "image-caption";
          caption.innerHTML = `${image.filename}`;

          imageWrapper.appendChild(img);
          imageWrapper.appendChild(caption);
          attachmentsContent.appendChild(imageWrapper);
        });
      }

      // Add generated files after images
      if (generatedFiles && generatedFiles.length > 0) {
        generatedFiles.forEach((file, index) => {
          const fileWrapper = document.createElement("div");
          fileWrapper.className = "message-image-wrapper"; // Use same class as images for consistent styling

          // Create file preview based on file type
          const filePreview = this.createFilePreview(file);

          const caption = document.createElement("div");
          caption.className = "image-caption"; // Use same class as images for consistent styling
          caption.innerHTML = `${file.filename}`;
          caption.style.cssText = `
          font-size: 0.65em;
          color: var(--text-secondary);
          text-align: center;
          max-width: 80px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          opacity: 0.8;
        `;

          fileWrapper.appendChild(filePreview);
          fileWrapper.appendChild(caption);
          attachmentsContent.appendChild(fileWrapper);
        });
      }

      // Attachments container'ını message content'in içine ekle
      const messageContent = messageDiv.querySelector(".message-content");
      if (messageContent) {
        messageContent.appendChild(attachmentsContainer);
      }
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Apply syntax highlighting
    messageDiv.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightBlock(block);
    });
  }

  showChartFullscreen(chart, index) {
    // Create fullscreen modal
    const modal = document.createElement("div");
    modal.className = "chart-fullscreen-modal";
    modal.id = `chart-fullscreen-${index}`;

    const modalContent = document.createElement("div");
    modalContent.className = "chart-fullscreen-content";

    // Create header with close button
    const modalHeader = document.createElement("div");
    modalHeader.className = "chart-fullscreen-header";

    const closeBtn = document.createElement("button");
    closeBtn.className = "chart-fullscreen-close";
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.title = "Kapat";
    closeBtn.addEventListener("click", () => {
      modal.remove();
      document.body.style.overflow = "auto";
    });

    // Create title
    const title = document.createElement("h3");
    title.className = "chart-fullscreen-title";

    // Extract chart metadata for title
    const chartInfo = [];
    if (chart.symbols && chart.symbols.length > 0) {
      chartInfo.push(chart.symbols.join(", "));
    }
    if (chart.chart_type) {
      chartInfo.push(
        chart.chart_type.charAt(0).toUpperCase() + chart.chart_type.slice(1)
      );
    }
    if (chart.period) {
      chartInfo.push(
        chart.period.charAt(0).toUpperCase() + chart.period.slice(1)
      );
    }

    title.textContent =
      chartInfo.length > 0 ? chartInfo.join(" - ") : `Chart ${index + 1}`;

    modalHeader.appendChild(closeBtn);
    modalHeader.appendChild(title);

    // Create fullscreen iframe
    const fullscreenFrame = document.createElement("iframe");
    fullscreenFrame.className = "chart-fullscreen-frame";
    fullscreenFrame.srcdoc = chart.data || chart.content;
    fullscreenFrame.setAttribute("sandbox", "allow-scripts allow-same-origin");

    // Add content to modal
    modalContent.appendChild(modalHeader);
    modalContent.appendChild(fullscreenFrame);
    modal.appendChild(modalContent);

    // Add to body and prevent scrolling
    document.body.appendChild(modal);
    document.body.style.overflow = "hidden";

    // Focus modal for keyboard navigation
    modal.focus();

    // Close on escape key
    const handleEscape = (e) => {
      if (e.key === "Escape") {
        modal.remove();
        document.body.style.overflow = "auto";
        document.removeEventListener("keydown", handleEscape);
      }
    };
    document.addEventListener("keydown", handleEscape);

    // Close on outside click
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.remove();
        document.body.style.overflow = "auto";
        document.removeEventListener("keydown", handleEscape);
      }
    });

    // Animate in
    setTimeout(() => {
      modal.classList.add("active");
    }, 10);
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

  // Create file preview based on file type
  createFilePreview(file) {
    const filePreview = document.createElement("div");
    filePreview.className = "file-preview";

    // Get file extension
    const fileExtension = file.filename.split(".").pop().toLowerCase();

    // Create icon based on file type
    let iconClass = "fas fa-file";
    let previewContent = "";

    switch (fileExtension) {
      case "xlsx":
        iconClass = "fas fa-file-excel";
        previewContent = `
          <div class="file-preview-content excel-preview">
            <i class="${iconClass}"></i>
            <span class="file-type">Excel</span>
          </div>
        `;
        break;
      case "docx":
        iconClass = "fas fa-file-word";
        previewContent = `
          <div class="file-preview-content word-preview">
            <i class="${iconClass}"></i>
            <span class="file-type">Word</span>
          </div>
        `;
        break;
      case "pptx":
        iconClass = "fas fa-file-powerpoint";
        previewContent = `
          <div class="file-preview-content powerpoint-preview">
            <i class="${iconClass}"></i>
            <span class="file-type">PowerPoint</span>
          </div>
        `;
        break;
      case "pdf":
        iconClass = "fas fa-file-pdf";
        previewContent = `
          <div class="file-preview-content pdf-preview">
            <i class="${iconClass}"></i>
            <span class="file-type">PDF</span>
          </div>
        `;
        break;
      default:
        previewContent = `
          <div class="file-preview-content default-preview">
            <i class="${iconClass}"></i>
            <span class="file-type">${fileExtension.toUpperCase()}</span>
          </div>
        `;
    }

    filePreview.innerHTML = previewContent;
    filePreview.style.cssText = `
      max-width: 100%;
      max-height: 80px;
      width: 60px;
      height: 60px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      overflow: hidden;
    `;

    // No hover effects for minimal design

    // Click to open file
    filePreview.addEventListener("click", () => {
      this.openGeneratedFile(file);
    });

    return filePreview;
  }

  // Image modal for full-size viewing
  showImageModal(image) {
    // Remove existing modal if any
    const existingModal = document.querySelector(".image-modal");
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
    img.src = `data:${image.type || "image/jpeg"};base64,${image.data}`;
    img.style.cssText = `
      max-width: 90%;
      max-height: 80%;
      border-radius: 12px;
      box-shadow: 0 12px 48px rgba(0,0,0,0.6);
      object-fit: contain;
      border: 2px solid rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(20px);
    `;

    const caption = document.createElement("div");
    caption.innerHTML = `
      <i class="fas fa-image"></i>
      <span>${image.filename}</span>
    `;
    caption.style.cssText = `
      color: white;
      font-size: 1.1em;
      margin-top: 20px;
      text-align: center;
      background: rgba(0, 0, 0, 0.8);
      padding: 12px 20px;
      border-radius: 25px;
      font-family: 'Segoe UI', system-ui, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border: 1px solid rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
    `;

    const closeButton = document.createElement("div");
    closeButton.innerHTML = '<i class="fas fa-times"></i>';
    closeButton.style.cssText = `
      position: absolute;
      top: 25px;
      right: 35px;
      color: white;
      font-size: 1.5em;
      cursor: pointer;
      background: rgba(0, 0, 0, 0.6);
      width: 45px;
      height: 45px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
      border: 1px solid rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
    `;

    closeButton.addEventListener("mouseenter", () => {
      closeButton.style.background = "rgba(239, 68, 68, 0.8)";
      closeButton.style.transform = "scale(1.05)";
    });

    closeButton.addEventListener("mouseleave", () => {
      closeButton.style.background = "rgba(0, 0, 0, 0.6)";
      closeButton.style.transform = "scale(1)";
    });

    modal.appendChild(img);
    modal.appendChild(caption);
    modal.appendChild(closeButton);
    document.body.appendChild(modal);

    // Close modal events
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });

    closeButton.addEventListener("click", () => {
      document.body.removeChild(modal);
    });

    // ESC key to close
    const handleEscape = (e) => {
      if (e.key === "Escape") {
        document.body.removeChild(modal);
        document.removeEventListener("keydown", handleEscape);
      }
    };
    document.addEventListener("keydown", handleEscape);
  }

  // Open generated file
  openGeneratedFile(file) {
    try {
      // Use Electron's shell to open the file with default application
      if (window.airisAPI && window.airisAPI.openGeneratedFile) {
        window.airisAPI
          .openGeneratedFile(file.file_path)
          .then((result) => {
            if (!result.success) {
              console.error("Error opening file:", result.error);
              alert(`Error opening file: ${result.error}`);
            }
          })
          .catch((error) => {
            console.error("Error opening generated file:", error);
            alert(`Error opening file: ${error.message}`);
          });
      } else {
        // Fallback: try to open with system default application
        console.log(`Opening file: ${file.file_path}`);
        // You can implement additional logic here if needed
        alert(
          `File: ${file.filename}\nPath: ${file.file_path}\n\nThis file has been created successfully. You can find it in the specified directory.`
        );
      }
    } catch (error) {
      console.error("Error opening generated file:", error);
      alert(`Error opening file: ${error.message}`);
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
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.addMessageToChat("assistant", t("welcomeAssistantMessage"));
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
          // Extract images, charts, and generated files properly - they should be fresh for each message
          const images = msg.images || msg.metadata?.images || [];
          const charts = msg.charts || msg.metadata?.charts || [];
          const generatedFiles = msg.metadata?.generatedFiles || [];

          // Ensure images, charts, and generated files are not accumulated from previous sessions
          const cleanImages = Array.isArray(images) ? images.slice() : [];
          const cleanCharts = Array.isArray(charts) ? charts.slice() : [];
          const cleanGeneratedFiles = Array.isArray(generatedFiles)
            ? generatedFiles.slice()
            : [];

          this.addMessageToChat(
            msg.role,
            msg.content,
            cleanImages,
            cleanCharts,
            cleanGeneratedFiles
          );

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
              this.chatHistory[this.chatHistory.length - 1].images =
                cleanImages;
              this.chatHistory[this.chatHistory.length - 1].charts =
                cleanCharts;
              this.chatHistory[this.chatHistory.length - 1].generatedFiles =
                cleanGeneratedFiles;
            }
          }
        });

        // Update UI to show active session
        this.updateChatSessionsUI();

        console.log("Loaded chat session:", sessionId);
        this.showNotification("Chat loaded", "success");
        return true;
      } else {
        console.error("Failed to load chat session:", response.error);
        this.showNotification("Failed to load chat", "error");
        return false;
      }
    } catch (error) {
      console.error("Error loading chat session:", error);
      this.showNotification("Error loading chat", "error");
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

        this.showNotification("Chat session deleted", "success");
        return true;
      } else {
        this.showNotification("Failed to delete chat", "error");
        return false;
      }
    } catch (error) {
      console.error("Error deleting chat session:", error);
      this.showNotification("Error deleting chat", "error");
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
      this.showNotification("New chat started", "success");
    } else {
      console.error("Failed to create new chat session");
      this.showNotification("Failed to create new chat", "error");
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

    console.log("Chat sessions UI updated");
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

  convertUrlsToLinks(content) {
    if (!content || typeof content !== "string") {
      return content;
    }

    // Pattern to match download URLs and convert them to clickable links
    const urlPattern =
      /(http:\/\/localhost:8001\/api\/created-documents\/[^\/\s]+\/download)/g;

    // Replace URLs with clickable download buttons
    content = content.replace(urlPattern, (match, url) => {
      // Extract filename from URL
      const filename = decodeURIComponent(url.split("/").slice(-2, -1)[0]);
      return `[📥 Download ${filename}](${url})`;
    });

    // Also handle direct file path mentions and convert them to download links
    const filePathPattern =
      /Download:\s*(http:\/\/localhost:8001\/api\/created-documents\/[^\/\s]+\/download)/g;
    content = content.replace(filePathPattern, (match, url) => {
      const filename = decodeURIComponent(url.split("/").slice(-2, -1)[0]);
      return `**Download:** [📥 ${filename}](${url})`;
    });

    return content;
  }

  // Chat file upload methods
  handleChatDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    const uploadArea = document.getElementById("chat-file-upload");
    if (uploadArea) {
      uploadArea.style.display = "block";
      uploadArea.classList.add("drag-over");
    }
  }

  handleChatDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    // Only hide if leaving the wrapper entirely
    if (!e.currentTarget.contains(e.relatedTarget)) {
      const uploadArea = document.getElementById("chat-file-upload");
      if (uploadArea && this.chatUploadedFiles.length === 0) {
        uploadArea.style.display = "none";
      }
      uploadArea?.classList.remove("drag-over");
    }
  }

  handleChatFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    const uploadArea = document.getElementById("chat-file-upload");
    uploadArea?.classList.remove("drag-over");

    const files = Array.from(e.dataTransfer.files);
    this.addFilesToChat(files);
  }

  handleChatFileSelect(e) {
    const files = Array.from(e.target.files);
    this.addFilesToChat(files);
    e.target.value = ""; // Clear input
  }

  addFilesToChat(files) {
    const validFiles = files.filter((file) => Utils.validateFile(file));

    validFiles.forEach((file) => {
      // Check if file already exists
      if (!this.chatUploadedFiles.find((f) => f.name === file.name)) {
        this.chatUploadedFiles.push(file);
      }
    });

    this.updateChatFilesPreview();

    if (validFiles.length > 0) {
      this.showNotification(
        `${validFiles.length} file(s) attached to chat`,
        "success"
      );
    }
  }

  updateChatFilesPreview() {
    const uploadArea = document.getElementById("chat-file-upload");
    const filesPreview = document.getElementById("chat-uploaded-files");

    if (!uploadArea || !filesPreview) return;

    if (this.chatUploadedFiles.length > 0) {
      uploadArea.style.display = "block";

      filesPreview.innerHTML = this.chatUploadedFiles
        .map(
          (file, index) => `
        <div class="chat-file-item">
          <i class="${Utils.getFileIcon(file.name)}"></i>
          <span class="file-name">${Utils.escapeHtml(file.name)}</span>
          <button class="remove-file" onclick="window.uiComponents.removeChatFile(${index})">
            <i class="fas fa-times"></i>
          </button>
        </div>
      `
        )
        .join("");
    } else {
      uploadArea.style.display = "none";
      filesPreview.innerHTML = "";
    }

    // Update send button state when files change
    this.toggleSendButton();
  }

  removeChatFile(index) {
    this.chatUploadedFiles.splice(index, 1);
    this.updateChatFilesPreview();
  }

  // Updated file upload handlers for chat input drag & drop
  handleNewFileSelect(event) {
    const files = Array.from(event.target.files);
    this.addFilesToChat(files);
  }

  handleChatInputDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    const chatInput = document.getElementById("chat-input");
    chatInput.classList.add("drag-over");
  }

  handleChatInputDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    const chatInput = document.getElementById("chat-input");
    if (!chatInput.contains(event.relatedTarget)) {
      chatInput.classList.remove("drag-over");
    }
  }

  handleChatInputDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    const chatInput = document.getElementById("chat-input");
    chatInput.classList.remove("drag-over");

    const files = Array.from(event.dataTransfer.files);
    this.addFilesToChat(files);
  }

  addFilesToChat(files) {
    if (!this.chatUploadedFiles) {
      this.chatUploadedFiles = [];
    }

    // Add files to the upload queue
    files.forEach((file) => {
      this.chatUploadedFiles.push(file);
    });

    // Update the preview
    this.updateChatFilesPreview();
  }

  // File status message methods
  addFileStatusMessage(fileName, status, errorMessage = "") {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    let statusIcon, statusText, statusClass;

    switch (status) {
      case "uploading":
        statusIcon =
          '<div class="upload-animation"><div class="dots"><span></span><span></span><span></span></div></div>';
        statusText = "";
        statusClass = "uploading";
        break;
      case "success":
        statusIcon = "✅";
        statusText = `Uploaded`;
        statusClass = "success";
        break;
      case "error":
        statusIcon = "❌";
        statusText = errorMessage || "Upload failed";
        statusClass = "error";
        break;
    }

    const messageElement = document.createElement("div");
    messageElement.className = `file-status-message ${statusClass}`;
    messageElement.innerHTML = `
      <div class="status-icon">${statusIcon}</div>
      <div class="status-text">
        <span class="file-name">${Utils.escapeHtml(
          fileName
        )}</span>: ${statusText}
      </div>
    `;

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Store reference for updates
    messageElement.dataset.fileName = fileName;
  }

  updateFileStatusMessage(fileName, status, errorMessage = "") {
    const statusMessage = document.querySelector(
      `[data-file-name="${fileName}"]`
    );
    if (!statusMessage) return;

    let statusIcon, statusText, statusClass;

    switch (status) {
      case "success":
        statusIcon = "✅";
        statusText = `Uploaded`;
        statusClass = "success";
        break;
      case "error":
        statusIcon = "❌";
        statusText = errorMessage || "Upload failed";
        statusClass = "error";
        break;
    }

    // Update the message
    statusMessage.className = `file-status-message ${statusClass}`;
    statusMessage.innerHTML = `
      <div class="status-icon">${statusIcon}</div>
      <div class="status-text">
        <span class="file-name">${Utils.escapeHtml(
          fileName
        )}</span>: ${statusText}
      </div>
    `;
  }

  updateProgressStage(iconElement, stageElement, iconClass, stageText) {
    iconElement.className = `${iconClass} progress-icon`;
    stageElement.textContent = stageText;
  }

  async animateProgress(
    fillElement,
    percentageElement,
    fromWidth,
    toWidth,
    duration
  ) {
    return new Promise((resolve) => {
      const startWidth =
        fromWidth !== null
          ? fromWidth
          : parseFloat(fillElement.style.width) || 0;
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
      new Promise((resolve) => setTimeout(resolve, duration)),
    ]);

    clearInterval(progressInterval);
    progressCallback(1); // Ensure we end at 100%
  }

  formatSpeed(bytesPerSecond) {
    if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`;
    if (bytesPerSecond < 1024 * 1024)
      return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
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
      // Fetch the file list from the backend
      const response = await fetch("http://localhost:8001/api/files");
      if (!response.ok) throw new Error("Failed to fetch file list");
      const data = await response.json();
      const files = data.files || [];
      // Get the file library container
      const fileLibrary = document.getElementById("files-grid");
      if (!fileLibrary) return;
      fileLibrary.innerHTML = "";

      if (files.length === 0) {
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        fileLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-folder-open"></i>
          <h3>${t("noDocuments")}</h3>
          <p>${t("uploadToGetStarted")}</p>
          <button class="cta-button" data-tab="chat">${t(
            "uploadFilesBtn"
          )}</button>
        </div>`;
        return;
      }

      // Render each file
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
          <div class="file-card-preview" id="preview-${Utils.escapeHtml(
            file.name
          ).replace(/[^a-zA-Z0-9]/g, "_")}">
            <div class="preview-loading">
              <i class="fas fa-spinner fa-spin"></i>
              <span data-i18n="previewLoading">Loading preview...</span>
            </div>
          </div>
        `;

        // Add click handler to open file (but not on action buttons)
        fileItem.addEventListener("click", (e) => {
          // Don't open file if clicking on action buttons or preview area
          if (
            !e.target.closest(".file-card-actions") &&
            !e.target.closest(".file-card-preview")
          ) {
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
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        fileLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>${t("error")}</h3>
          <p>${t("networkError")}</p>
        </div>`;
      }
      console.error("Error loading file library:", error);
    }
  }

  async loadCreatedDocumentsLibrary() {
    try {
      // Fetch the created documents list from the backend
      const response = await fetch(
        "http://localhost:8001/api/created-documents"
      );
      if (!response.ok)
        throw new Error("Failed to fetch created documents list");
      const data = await response.json();
      const files = data.files || [];

      // Get the created documents library container
      const documentsLibrary = document.getElementById(
        "created-documents-grid"
      );
      if (!documentsLibrary) return;
      documentsLibrary.innerHTML = "";

      if (files.length === 0) {
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        documentsLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-file-invoice"></i>
          <h3>${t("noCreatedDocuments")}</h3>
          <p>${t("askAiToCreateDocuments")}</p>
          <button class="cta-button" data-tab="chat">${t(
            "startChatBtn"
          )}</button>
        </div>`;
        return;
      }

      // Render each created document
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
          <div class="file-card-preview" id="created-preview-${Utils.escapeHtml(
            file.name
          ).replace(/[^a-zA-Z0-9]/g, "_")}">
            <div class="preview-loading">
              <i class="fas fa-spinner fa-spin"></i>
              <span data-i18n="previewLoading">Loading preview...</span>
            </div>
          </div>
        `;

        // Add click handler to open created document (but not on preview area or action buttons)
        fileItem.addEventListener("click", (e) => {
          // Don't open file if clicking on action buttons or preview area
          if (
            !e.target.closest(".file-card-actions") &&
            !e.target.closest(".file-card-preview")
          ) {
            this.openCreatedDocument(file.name);
          }
        });

        documentsLibrary.appendChild(fileItem);

        // Load preview for this created document
        this.loadCreatedDocumentPreview(file.name);
      });
    } catch (error) {
      const documentsLibrary = document.getElementById(
        "created-documents-grid"
      );
      if (documentsLibrary) {
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        documentsLibrary.innerHTML = `<div class="empty-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>${t("error")}</h3>
          <p>${t("errorLoadingFiles")}</p>
        </div>`;
      }
      console.error("Error loading created documents library:", error);
    }
  }

  async loadFilePreview(fileName) {
    const previewId = `preview-${fileName.replace(/[^a-zA-Z0-9]/g, "_")}`;
    const previewElement = document.getElementById(previewId);

    if (!previewElement) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8001/api/files/${encodeURIComponent(
          fileName
        )}/preview`
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
          <span>Preview unavailable: ${Utils.escapeHtml(
            error.message || "Connection error"
          )}</span>
        </div>
      `;
    }
  }

  renderFilePreview(previewElement, previewData) {
    if (!previewData.success) {
      previewElement.innerHTML = `
        <div class="preview-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>Preview error: ${Utils.escapeHtml(
            previewData.error || "Error occurred"
          )}</span>
        </div>
      `;
      return;
    }

    const { preview_type, preview_data } = previewData;

    switch (preview_type) {
      case "image":
        previewElement.innerHTML = `
          <div class="preview-image">
            <div class="preview-image-wrapper">
              <img src="${preview_data}" alt="Document preview" 
                   onload="this.parentElement.classList.add('loaded')" />
              <div class="preview-image-overlay">
                <i class="fas fa-expand-alt"></i>
                <span>Click to enlarge</span>
              </div>
            </div>
          </div>
        `;
        break;

      case "text":
        previewElement.innerHTML = `
          <div class="preview-text">
            <div class="preview-header">
              <i class="fas fa-file-alt"></i>
              <span>Text Preview</span>
            </div>
            <div class="preview-content">
              <pre>${Utils.escapeHtml(preview_data)}</pre>
            </div>
          </div>
        `;
        break;

      case "excel":
        previewElement.innerHTML = `
          <div class="preview-excel">
            <div class="preview-header">
              <i class="fas fa-table"></i>
              <span>Spreadsheet Preview</span>
            </div>
            <div class="excel-summary">
              <strong>${preview_data.columns.length} columns, ${preview_data.rows_shown} rows</strong>
            </div>
            <div class="excel-data">${preview_data.html}</div>
          </div>
        `;
        break;

      case "info":
        previewElement.innerHTML = `
          <div class="preview-info">
            <div class="preview-header">
              <i class="fas fa-info-circle"></i>
              <span>Document Information</span>
            </div>
            <div class="preview-content">
              <span>${Utils.escapeHtml(preview_data)}</span>
            </div>
          </div>
        `;
        break;

      case "error":
        previewElement.innerHTML = `
          <div class="preview-error">
            <div class="preview-header">
              <i class="fas fa-exclamation-triangle"></i>
              <span>Preview Error</span>
            </div>
            <div class="preview-content">
              <span>${Utils.escapeHtml(preview_data)}</span>
            </div>
          </div>
        `;
        break;

      default:
        previewElement.innerHTML = `
          <div class="preview-info">
            <div class="preview-header">
              <i class="fas fa-file"></i>
              <span>Preview Not Available</span>
            </div>
            <div class="preview-content">
              <span>This file type does not support preview</span>
            </div>
          </div>
        `;
    }
  }

  async loadCreatedDocumentPreview(fileName) {
    const previewId = `created-preview-${fileName.replace(
      /[^a-zA-Z0-9]/g,
      "_"
    )}`;
    const previewElement = document.getElementById(previewId);

    if (!previewElement) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8001/api/created-documents/${encodeURIComponent(
          fileName
        )}/preview`
      );

      if (!response.ok) {
        throw new Error(`Failed to load preview: ${response.statusText}`);
      }

      const previewData = await response.json();
      this.renderFilePreview(previewElement, previewData);
    } catch (error) {
      console.error(
        `Error loading preview for created document ${fileName}:`,
        error
      );
      previewElement.innerHTML = `
        <div class="preview-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>Preview unavailable: ${Utils.escapeHtml(
            error.message || "Connection error"
          )}</span>
        </div>
      `;
    }
  }

  async openFile(fileName) {
    try {
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;

      // Try to open the file using Electron's API
      if (window.airisAPI && window.airisAPI.openFile) {
        try {
          await window.airisAPI.openFile(fileName);
          this.showNotification(`${t("openedFile")} ${fileName}`, "success");
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
        const downloadUrl = `http://localhost:8001/api/files/${encodeURIComponent(
          fileName
        )}/download`;
        window.open(downloadUrl, "_blank");
        this.showNotification(`${t("downloadingFile")} ${fileName}...`, "info");
      } catch (downloadError) {
        console.error("Download failed:", downloadError);

        // Last resort: Try to get file info
        const response = await fetch(
          `http://localhost:8001/api/files/${encodeURIComponent(fileName)}`
        );
        if (response.ok) {
          const fileInfo = await response.json();
          this.showNotification(
            `${fileName} (${Utils.formatFileSize(fileInfo.size || 0)}) - ${t(
              "unableToOpenDirectly"
            )}`,
            "warning"
          );
        } else {
          throw new Error("Unable to access file");
        }
      }
    } catch (error) {
      console.error("Error opening file:", error);
      this.showNotification(
        `${t("failedToOpenFile")} ${fileName}. ${t("sorryEncounteredError")}`,
        "error"
      );
    }
  }

  async openCreatedDocument(fileName) {
    try {
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;

      // Try to open the file using Electron's API first
      if (window.airisAPI && window.airisAPI.openFile) {
        try {
          await window.airisAPI.openFile(fileName);
          this.showNotification(`${t("openedFile")} ${fileName}`, "success");
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
        const downloadUrl = `http://localhost:8001/api/created-documents/${encodeURIComponent(
          fileName
        )}/download`;
        window.open(downloadUrl, "_blank");
        this.showNotification(`${t("downloadingFile")} ${fileName}...`, "info");
      } catch (downloadError) {
        console.error("Download failed:", downloadError);

        // Last resort: Try to get file info
        const response = await fetch(
          `http://localhost:8001/api/created-documents/${encodeURIComponent(
            fileName
          )}`
        );
        if (response.ok) {
          const fileInfo = await response.json();
          this.showNotification(
            `${fileName} (${Utils.formatFileSize(fileInfo.size || 0)}) - ${t(
              "unableToOpenDirectly"
            )}`,
            "warning"
          );
        } else {
          throw new Error("Unable to access file");
        }
      }
    } catch (error) {
      console.error("Error opening created document:", error);
      this.showNotification(
        `${t("failedToOpenFile")} ${fileName}. ${t("sorryEncounteredError")}`,
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
        `Are you sure you want to delete "${fileName}"?\n\nThis will permanently remove the file and all its data from the document archive.`
      );

      if (!confirmed) {
        console.log("❌ Frontend: User cancelled deletion for:", fileName);
        return;
      }

      console.log("✅ Frontend: User confirmed deletion for:", fileName);

      // Show loading state
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showNotification(t("deletingFile"), "info");

      console.log("🚀 Frontend: Calling API to delete file:", fileName);

      // Request the API service to delete the file
      const result = await fetch(
        `http://localhost:8001/api/files/${encodeURIComponent(fileName)}`,
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
        console.log("✅ Frontend: Deletion completed, showing success message");
        this.showNotification(`File "${fileName}" deleted`, "success");
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

  async deleteCreatedDocument(fileName) {
    console.log("🗑️ Frontend: deleteCreatedDocument called for:", fileName);

    try {
      // Show confirmation dialog
      console.log("🤔 Frontend: Showing confirmation dialog for:", fileName);
      const confirmed = confirm(
        `Are you sure you want to delete "${fileName}"?\n\nThis will permanently remove the file from your local storage.`
      );

      if (!confirmed) {
        console.log("❌ Frontend: User cancelled deletion for:", fileName);
        return;
      }

      console.log("✅ Frontend: User confirmed deletion for:", fileName);

      // Show loading state
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showNotification(t("deletingFile"), "info");

      console.log(
        "🚀 Frontend: Calling IPC to delete created document:",
        fileName
      );

      // Request the IPC service to delete the created document
      const result = await window.airisAPI.deleteCreatedDocument(fileName);

      if (!result.success) {
        throw new Error(`Failed to delete created document: ${result.error}`);
      }

      const response = { success: true, message: result.data.message };

      console.log("📋 Frontend: API response received:", response);

      if (response.success) {
        console.log("✅ Frontend: Deletion completed, showing success message");
        this.showNotification(`Document "${fileName}" deleted`, "success");
        // Refresh the created documents list
        console.log("🔄 Frontend: Refreshing created documents list");
        this.loadCreatedDocumentsLibrary();
      } else {
        console.error("❌ Frontend: Deletion failed:", response.error);
        this.showNotification(
          `Failed to delete document: ${response.error}`,
          "error"
        );
      }
    } catch (error) {
      console.error("❌ Frontend: Error deleting created document:", error);
      console.error("❌ Frontend: Error details:", error.message, error.stack);
      this.showNotification(
        "Failed to delete document. Please try again.",
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
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    fileElement.innerHTML = `
            <div class="file-icon">
                <i class="${fileIcon}"></i>
            </div>
            <div class="file-details">
                <div class="file-name">${Utils.escapeHtml(file.name)}</div>
                <div class="file-meta">
                    <span class="file-size">${fileSize}</span>
                    <span class="file-date">${t(
                      "uploadedOn"
                    )} ${uploadDate}</span>
                </div>
            </div>
            <div class="file-actions">
                <button class="action-btn" onclick="window.uiComponents.downloadFile('${
                  file.id
                }')" title="${t("downloadFile")}">
                    <i class="fas fa-download"></i>
                </button>
                <button class="action-btn delete" onclick="window.uiComponents.deleteFile('${
                  file.id
                }')" title="${t("deleteFile")}">
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

  // Theme management
  loadTheme() {
    const savedTheme = localStorage.getItem("airis-theme") || "light";
    this.currentTheme = savedTheme;
    this.applyTheme();
  }

  toggleTheme() {
    // Cycle through themes: light -> dark -> nebula -> light
    const themes = ["light", "dark", "nebula"];
    const currentIndex = themes.indexOf(this.currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    this.currentTheme = themes[nextIndex];
    this.applyTheme();
    localStorage.setItem("airis-theme", this.currentTheme);
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

  // Settings management
  saveSettings() {
    const settings = {
      apiEndpoint:
        document.getElementById("api-endpoint")?.value ||
        "http://localhost:8001",
      maxFileSize: document.getElementById("max-file-size")?.value || "50",
      autoSave: document.getElementById("auto-save")?.checked || false,
      notifications: document.getElementById("notifications")?.checked || true,
    };

    localStorage.setItem("airis-settings", JSON.stringify(settings));

    // Show success message
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;
    this.showNotification(t("settingsSavedSuccessfully"), "success");
  }

  loadSettings() {
    try {
      const settings = JSON.parse(
        localStorage.getItem("airis-settings") || "{}"
      );

      if (document.getElementById("api-endpoint")) {
        document.getElementById("api-endpoint").value =
          settings.apiEndpoint || "http://localhost:8001";
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
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;
    this.addMessageToChat("assistant", t("welcomeAssistantMessage"));

    // Load initial tab data
    this.loadTabData(this.currentTab);
  }

  // Example method to get the flag for backend communication
  isWebSearchEnabled() {
    return this.webSearchEnabled;
  }

  // Finance News functionality
  async loadFinanceNews(forceRefresh = false) {
    const newsGrid = document.getElementById("news-grid");
    const newsLastUpdated = document.getElementById("news-last-updated");
    const refreshButton = document.getElementById("refresh-news");

    if (!newsGrid) return;

    // Show loading state if forcing refresh or no news loaded
    if (forceRefresh || !this.lastNewsUpdate) {
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      newsGrid.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <p>${t("loadingLatestNews")}</p>
          <small style="color: #666; margin-top: 8px; display: block;">AI ile akıllı haber kümeleme yapılıyor...</small>
        </div>
      `;

      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML = `<i class="fas fa-sync-alt fa-spin"></i> ${t(
          "loading"
        )}`;
      }
    }

    try {
      // Load from database by default (no force refresh)
      const result = await window.apiService.getFinanceNews(false);

      if (result.success) {
        if (result.articles.length > 0) {
          // We have articles - render them
          this.renderFinanceNews(result.articles, result.data);
          this.lastNewsUpdate = new Date().toISOString();

          if (newsLastUpdated) {
            const t = window.languageService
              ? window.languageService.t.bind(window.languageService)
              : (key) => key;
            newsLastUpdated.textContent = `${t(
              "lastUpdatedAt"
            )} ${new Date().toLocaleTimeString()}`;
          }

          // Update scheduler status
          this.updateSchedulerStatus();

          // Set up auto-refresh interval
          this.startNewsAutoRefresh();
        } else {
          // Empty database - show empty state and try initial refresh
          const t = window.languageService
            ? window.languageService.t.bind(window.languageService)
            : (key) => key;

          newsGrid.innerHTML = `
            <div class="empty-state">
              <i class="fas fa-newspaper"></i>
              <h3>No news available</h3>
              <p>Database is empty. Let's fetch the latest financial news.</p>
              <button class="btn btn-primary" onclick="window.uiComponents.refreshFinanceNews()">
                <i class="fas fa-sync-alt"></i> Fetch Latest News
              </button>
            </div>
          `;

          if (newsLastUpdated) {
            newsLastUpdated.textContent =
              t("noNewsAvailable") || "No news available";
          }

          // Still set up auto-refresh for future updates
          this.startNewsAutoRefresh();
        }
      } else {
        throw new Error(result.error || "Failed to load news");
      }
    } catch (error) {
      console.error("Failed to load finance news:", error);
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      newsGrid.innerHTML = `
        <div class="error-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>${t("failedToLoadNews")}</h3>
          <p>${error.message || t("unableToFetchNews")}</p>
          <button class="btn btn-primary" onclick="window.uiComponents.loadFinanceNews(true)">
            <i class="fas fa-retry"></i> ${t("retryAction")}
          </button>
        </div>
      `;

      if (newsLastUpdated) {
        newsLastUpdated.textContent = t("failedToUpdate");
      }
    } finally {
      if (refreshButton) {
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        refreshButton.disabled = false;
        refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t(
          "refresh"
        )}`;
      }
    }
  }

  renderFinanceNews(articles, newsData = null) {
    const newsGrid = document.getElementById("news-grid");
    if (!newsGrid) return;

    // Store full news data including clustered_articles
    this.currentNewsData = newsData;

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

    // Add indices to articles for detail view navigation
    const articlesWithIndices = sortedArticles.map((article, index) => ({
      ...article,
      index: index,
    }));

    // FIXED: Store the sorted articles with indices (not the original unsorted ones)
    this.currentArticles = articlesWithIndices;

    newsGrid.innerHTML = articlesWithIndices
      .map((article) => this.createNewsItem(article))
      .join("");
  }

  createNewsItem(article) {
    // Handle article.published safely
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    let timeAgo = t("unknown");
    try {
      if (article.published) {
        const publishedDate = new Date(article.published);
        timeAgo = this.getTimeAgo(publishedDate);
      }
    } catch (error) {
      console.warn("Error processing article date:", error, article.published);
      timeAgo = t("unknown");
    }

    // Create image HTML if image URL is available
    let imageHtml = "";
    let imageSrc = "";
    let imageAlt = Utils.escapeHtml(article.title);
    let imageWidth = "";
    let imageHeight = "";

    // First, try the direct image_url from the article
    if (article.image_url) {
      imageSrc = article.image_url;
      imageWidth = article.image_width ? `width="${article.image_width}"` : "";
      imageHeight = article.image_height
        ? `height="${article.image_height}"`
        : "";
    }
    // If no direct image, try available_images from cluster data
    else if (article.available_images && article.available_images.length > 0) {
      // Use the first image from available_images (or you can randomize)
      const selectedImage = article.available_images[0]; // First image
      // Or randomize: article.available_images[Math.floor(Math.random() * article.available_images.length)]

      imageSrc = selectedImage.url;
      imageAlt = `${Utils.escapeHtml(
        article.title
      )} - Image from ${Utils.escapeHtml(selectedImage.source)}`;
      imageWidth = selectedImage.width ? `width="${selectedImage.width}"` : "";
      imageHeight = selectedImage.height
        ? `height="${selectedImage.height}"`
        : "";
    }

    // Create image HTML if we have an image source
    if (imageSrc) {
      imageHtml = `
      <div class="news-image">
        <img src="${Utils.escapeHtml(imageSrc)}"
             alt="${imageAlt}"
             loading="lazy"
             onerror="this.style.display='none'"
             ${imageWidth}
             ${imageHeight}
        />
      </div>
    `;
    }

    return `
      <div class="news-item" data-article-index="${article.index || 0}">
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
          <button class="news-link-btn" title="Read full article">
            <i class="fas fa-arrow-right"></i>
          </button>
        </div>
      </div>
    `;
  }

  getTimeAgo(date) {
    const now = new Date();

    // Handle different date formats and timezone issues
    let articleDate;
    try {
      if (typeof date === "string") {
        // Parse the date string and convert to user's local time
        articleDate = new Date(date);
      } else {
        articleDate = new Date(date);
      }

      // Check if date is valid
      if (isNaN(articleDate.getTime())) {
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        return t("unknown");
      }

      // Calculate difference in milliseconds
      const diff = now.getTime() - articleDate.getTime();

      // If difference is negative (future date), it's probably a timezone issue
      // Assume the article date should be treated as local time
      let actualDiff = diff;
      if (diff < 0) {
        // Try adjusting for potential timezone offset issues
        // If the date seems to be in the future, assume it's UTC and convert to local
        const timezoneOffsetMs = now.getTimezoneOffset() * 60 * 1000;
        actualDiff = diff + timezoneOffsetMs;

        // If still negative, just use absolute value but cap it
        if (actualDiff < 0) {
          actualDiff = Math.abs(diff);
        }
      }

      const minutes = Math.floor(actualDiff / 60000);
      const hours = Math.floor(actualDiff / 3600000);
      const days = Math.floor(actualDiff / 86400000);

      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;

      // Ensure we don't show negative values
      if (minutes < 0) {
        return t("justNow");
      } else if (minutes < 1) {
        return t("justNow");
      } else if (minutes < 60) {
        return `~${minutes}${t("minutesAgo")}`;
      } else if (hours < 24) {
        return `~${hours}${t("hoursAgo")}`;
      } else {
        return `~${days}${t("daysAgo")}`;
      }
    } catch (error) {
      console.warn("Error calculating time ago:", error, "for date:", date);
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      return t("unknown");
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
    }, 300000);
  }

  stopNewsAutoRefresh() {
    if (this.newsRefreshInterval) {
      clearInterval(this.newsRefreshInterval);
      this.newsRefreshInterval = null;
    }
  }

  async refreshFinanceNews() {
    const refreshButton = document.getElementById("refresh-news");
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    try {
      // Show loading state on button
      if (refreshButton) {
        const originalContent = refreshButton.innerHTML;
        refreshButton.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${t(
          "loading"
        )}...`;
        refreshButton.disabled = true;
      }

      // Force refresh from sources and update database
      const result = await window.apiService.getFinanceNews(true);

      if (result.success) {
        if (result.articles.length > 0) {
          this.renderFinanceNews(result.articles, result.data);
          this.lastNewsUpdate = new Date().toISOString();

          const newsLastUpdated = document.getElementById("news-last-updated");
          if (newsLastUpdated) {
            newsLastUpdated.textContent = `${t(
              "lastUpdated"
            )} ${new Date().toLocaleTimeString()}`;
          }

          // Update scheduler status hint
          this.updateSchedulerStatus();

          // Show success message briefly
          if (refreshButton) {
            refreshButton.innerHTML = `<i class="fas fa-check"></i> ${t(
              "refresh"
            )}`;
            setTimeout(() => {
              refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t(
                "refresh"
              )}`;
            }, 2000);
          }
        } else {
          // No articles found even after refresh
          const newsGrid = document.getElementById("news-grid");
          if (newsGrid) {
            newsGrid.innerHTML = `
              <div class="empty-state">
                <i class="fas fa-newspaper"></i>
                <h3>No news found</h3>
                <p>Unable to fetch news from any sources at the moment. Please try again later.</p>
                <button class="btn btn-primary" onclick="window.uiComponents.refreshFinanceNews()">
                  <i class="fas fa-sync-alt"></i> Try Again
                </button>
              </div>
            `;
          }

          if (refreshButton) {
            refreshButton.innerHTML = `<i class="fas fa-info-circle"></i> No News Found`;
            setTimeout(() => {
              refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t(
                "refresh"
              )}`;
            }, 3000);
          }
        }
      } else {
        throw new Error(result.error || "Failed to refresh news");
      }
    } catch (error) {
      console.error("Failed to refresh finance news:", error);

      if (refreshButton) {
        refreshButton.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${t(
          "retryAction"
        )}`;
        setTimeout(() => {
          refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t(
            "refresh"
          )}`;
        }, 3000);
      }

      // Show error to user (could add toast notification here)
      alert(
        t("failedToLoadNews") + ": " + (error.message || t("unableToFetchNews"))
      );
    } finally {
      // Re-enable button
      if (refreshButton) {
        refreshButton.disabled = false;
      }
    }
  }

  showNewsDetail(articleIndex) {
    if (!this.currentArticles || !this.currentArticles[articleIndex]) {
      console.error("Article not found:", articleIndex);
      return;
    }

    const article = this.currentArticles[articleIndex];
    const newsGrid = document.getElementById("news-grid");
    const newsDetail = document.getElementById("news-detail");

    if (!newsGrid || !newsDetail) return;

    // Hide news grid and show detail view
    newsGrid.style.display = "none";
    newsDetail.style.display = "flex";

    // Populate detail view
    this.populateNewsDetail(article);

    // Set up back button handler
    const backButton = document.getElementById("news-detail-back");
    if (backButton) {
      backButton.onclick = () => this.hideNewsDetail();
    }

    // Ensure chat input is fixed at the bottom while viewing details
    const chatContainer = document.getElementById("news-chat-input-container");
    const detail = document.getElementById("news-detail");
    if (chatContainer && detail) {
      chatContainer.classList.add("news-chat-fixed");
      detail.classList.add("news-chat-fixed-active");
    }
  }

  hideNewsDetail() {
    const newsGrid = document.getElementById("news-grid");
    const newsDetail = document.getElementById("news-detail");

    if (!newsGrid || !newsDetail) return;

    // Check if we're in Q&A mode
    if (this.newsQAStarted && this.currentNewsArticle) {
      // If in Q&A mode, reset to original article view first, then hide detail
      this.resetNewsDetailToOriginal();
      // Continue to hide the detail view after reset
    }

    // Show news grid and hide detail view
    newsDetail.style.display = "none";
    newsGrid.style.display = "grid";

    // Clean up event listeners when hiding detail view
    const sourcesListElement = document.getElementById("news-sources-list");
    if (sourcesListElement && this.sourceLinkClickHandler) {
      sourcesListElement.removeEventListener(
        "click",
        this.sourceLinkClickHandler
      );
      this.sourceLinkClickHandler = null;
    }

    // Remove fixed chat styling when leaving detail view
    const chatContainer = document.getElementById("news-chat-input-container");
    if (chatContainer) chatContainer.classList.remove("news-chat-fixed");
    newsDetail.classList.remove("news-chat-fixed-active");
  }

  resetNewsDetailToOriginal() {
    if (!this.currentNewsArticle) return;

    // Reset the news detail view to the original article
    this.populateNewsDetail(this.currentNewsArticle);

    // Reset Q&A mode state
    this.newsQAStarted = false;

    // Remove Q&A mode styling
    const newsDetail = document.getElementById("news-detail");
    if (newsDetail) {
      newsDetail.classList.remove("news-qa-mode");
    }

    // Clear any Q&A container content
    const newsDetailArticle = document.getElementById("news-detail-article");
    if (newsDetailArticle) {
      const qaContainer = newsDetailArticle.querySelector("#news-qa-container");
      if (qaContainer) {
        qaContainer.remove();
      }
    }

    // Reset chat interface
    this.resetNewsChatInterface();

    // Update button text back to "Back to News"
    this.updateNewsBackButtonText();
  }

  updateNewsBackButtonText() {
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    const backButton = document.querySelector('[data-i18n="backToNews"]');
    if (backButton) {
      if (this.newsQAStarted) {
        // In Q&A mode, show "Go back"
        backButton.textContent = t("goBack");
      } else {
        // In normal news view, show "Back to News"
        backButton.textContent = t("backToNews");
      }
    }
  }

  populateNewsDetail(article) {
    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    // Set title
    const titleElement = document.getElementById("news-detail-title");
    if (titleElement) {
      titleElement.textContent = article.title;
    }

    // Set sources
    const sourcesElement = document.getElementById("news-detail-sources");
    if (sourcesElement) {
      // Try to get sources from cluster data first
      const clusterData = this.findClusterForArticle(article);
      let sourceText = "";

      if (clusterData && clusterData.sources) {
        // Use cluster sources
        sourceText = Array.isArray(clusterData.sources)
          ? clusterData.sources.join(", ")
          : clusterData.sources;
      } else if (article.sources) {
        // Fallback to article sources
        sourceText = Array.isArray(article.sources)
          ? article.sources.join(", ")
          : article.sources;
      } else {
        // Last fallback to article source
        sourceText = article.source || "Unknown source";
      }

      sourcesElement.textContent = sourceText;
    }

    // Set time
    const timeElement = document.getElementById("news-detail-time");
    if (timeElement) {
      try {
        if (article.published) {
          const publishedDate = new Date(article.published);
          const timeAgo = this.getTimeAgo(publishedDate);
          timeElement.textContent = timeAgo;
        }
      } catch (error) {
        timeElement.textContent = t("unknown");
      }
    }

    // Process and set content
    this.populateNewsContent(article);

    // Populate sources list
    this.populateSourcesList(article);

    // Initialize news chat functionality
    this.initializeNewsChat(article);

    // Update button text based on current state
    this.updateNewsBackButtonText();
  }

  populateNewsContent(article) {
    const contentElement = document.getElementById("news-detail-content");
    if (!contentElement) return;

    let content = article.summary || article.unified_description || "";

    // Try to get images from cluster data
    const clusterData = this.findClusterForArticle(article);
    const availableImages =
      (clusterData && clusterData.available_images) ||
      article.available_images ||
      [];

    // Process image markers and replace with actual images
    content = this.processImageMarkers(content, availableImages);

    // Convert markdown-style formatting to HTML if needed
    content = this.formatNewsContent(content);

    contentElement.innerHTML = content;
  }

  processImageMarkers(content, availableImages) {
    if (!availableImages || availableImages.length === 0) {
      // Remove image markers if no images available
      return content.replace(/\{\{IMAGE_\w+\}\}/g, "");
    }

    // Replace image markers with actual images
    let imageIndex = 0;

    // Lead image
    if (content.includes("{{IMAGE_LEAD}}") && availableImages[imageIndex]) {
      const img = availableImages[imageIndex];
      const imageHtml = `
        <div class="news-detail-image lead-image large">
          <img src="${Utils.escapeHtml(img.url)}" 
               alt="News image from ${Utils.escapeHtml(img.source)}"
               loading="lazy"
               onerror="this.style.display='none'" />
          <div class="image-caption">Image from ${Utils.escapeHtml(
            img.source
          )}</div>
        </div>
      `;
      content = content.replace("{{IMAGE_LEAD}}", imageHtml);
      imageIndex++;
    }

    // Mid images
    for (let i = 1; i <= 2; i++) {
      const marker = `{{IMAGE_MID_${i}}}`;
      if (content.includes(marker) && availableImages[imageIndex]) {
        const img = availableImages[imageIndex];
        const sizeClass = i === 1 ? "medium" : "small";
        const imageHtml = `
          <div class="news-detail-image ${sizeClass}">
            <img src="${Utils.escapeHtml(img.url)}" 
                 alt="News image from ${Utils.escapeHtml(img.source)}"
                 loading="lazy"
                 onerror="this.style.display='none'" />
            <div class="image-caption">Image from ${Utils.escapeHtml(
              img.source
            )}</div>
          </div>
        `;
        content = content.replace(marker, imageHtml);
        imageIndex++;
      }
    }

    // Remove any remaining markers
    content = content.replace(/\{\{IMAGE_\w+\}\}/g, "");

    return content;
  }

  formatNewsContent(content) {
    // Convert markdown-style bold formatting to HTML
    content = content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Convert double line breaks to paragraphs
    const paragraphs = content.split(/\n\s*\n/);

    return paragraphs
      .map((para) => {
        para = para.trim();
        if (!para) return "";

        // Check if it's an image div
        if (para.includes('<div class="news-detail-image')) {
          return para;
        }

        // Wrap in paragraph tags
        return `<p>${para}</p>`;
      })
      .filter((para) => para)
      .join("\n");
  }

  populateSourcesList(article) {
    const sourcesListElement = document.getElementById("news-sources-list");
    if (!sourcesListElement) return;

    let sources = [];

    // Try to find the corresponding cluster data for this article
    const clusterData = this.findClusterForArticle(article);

    if (clusterData && clusterData.articles) {
      // Use the full cluster data to get all sources
      sources = clusterData.articles.map((art) => ({
        name: art.source,
        url: art.link,
        source: art.source,
      }));
    } else if (article.articles && Array.isArray(article.articles)) {
      // Fallback: if article has articles property directly
      sources = article.articles.map((art) => ({
        name: art.source,
        url: art.link,
        source: art.source,
      }));
    } else {
      // Single article fallback
      sources = [
        {
          name: article.source,
          url: article.link,
          source: article.source,
        },
      ];
    }

    // Remove duplicates based on URL
    const uniqueSources = sources.filter(
      (source, index, self) =>
        index === self.findIndex((s) => s.url === source.url)
    );

    if (uniqueSources.length === 0) {
      sourcesListElement.innerHTML = "<p>No sources available</p>";
      return;
    }

    const sourcesHtml = uniqueSources
      .map((source) => {
        const domain = this.extractDomain(source.url);
        const icon = source.name.charAt(0).toUpperCase();

        return `
        <a href="${Utils.escapeHtml(
          source.url
        )}" target="_blank" rel="noopener noreferrer" class="news-source-link" 
           data-source-name="${Utils.escapeHtml(
             source.name
           )}" data-source-url="${Utils.escapeHtml(source.url)}">
          <div class="source-icon">${icon}</div>
          <div class="source-info">
            <div class="source-name">${Utils.escapeHtml(source.name)}</div>
            <div class="source-url">${Utils.escapeHtml(domain)}</div>
          </div>
          <i class="fas fa-external-link-alt external-icon"></i>
        </a>
      `;
      })
      .join("");

    sourcesListElement.innerHTML = sourcesHtml;

    // Add event delegation for source link clicks with error handling
    // Remove any existing listeners first to prevent duplicates
    if (this.sourceLinkClickHandler) {
      sourcesListElement.removeEventListener(
        "click",
        this.sourceLinkClickHandler
      );
    }

    // Create a bound handler and store reference for removal
    this.sourceLinkClickHandler = this.handleSourceLinkClick.bind(this);
    sourcesListElement.addEventListener("click", this.sourceLinkClickHandler);
  }

  async handleSourceLinkClick(event) {
    const link = event.target.closest(".news-source-link");
    if (!link) return;

    event.preventDefault();

    const url = link.dataset.sourceUrl;
    const sourceName = link.dataset.sourceName;

    console.log(`🔗 Attempting to open source link: ${sourceName} -> ${url}`);

    // Check if we're in Electron environment
    if (window.airisAPI && window.airisAPI.openExternalUrl) {
      try {
        const result = await window.airisAPI.openExternalUrl(url);

        if (result.success) {
          console.log(
            `✅ Successfully opened ${sourceName} link in external browser`
          );
        } else {
          console.warn(`❌ Failed to open ${sourceName} link: ${result.error}`);
          this.handleFailedLinkOpen(url, sourceName);
        }
      } catch (error) {
        console.error(`❌ Error using Electron API for ${sourceName}:`, error);
        this.handleFailedLinkOpen(url, sourceName);
      }
    } else {
      // Fallback for non-Electron environments (web browser)
      console.log(
        `🌐 Using fallback method for ${sourceName} (not in Electron)`
      );
      try {
        const newWindow = window.open(url, "_blank", "noopener,noreferrer");

        // Immediate check for popup blocking
        if (!newWindow) {
          console.warn(
            `❌ Popup blocked for ${sourceName}, trying alternative method...`
          );
          this.handleFailedLinkOpen(url, sourceName);
          return;
        }

        // Check if window was immediately closed (indicates failure)
        if (newWindow.closed) {
          console.warn(
            `❌ Window immediately closed for ${sourceName}, trying alternative method...`
          );
          this.handleFailedLinkOpen(url, sourceName);
          return;
        }

        console.log(`✅ Successfully opened ${sourceName} link`);
      } catch (error) {
        console.error(`❌ Error opening ${sourceName} link:`, error);
        this.handleFailedLinkOpen(url, sourceName);
      }
    }
  }

  async handleFailedLinkOpen(url, sourceName) {
    // Show user notification with options
    const message = `Unable to open ${sourceName} link directly. Would you like to copy the URL to clipboard?`;

    if (confirm(message)) {
      // Copy URL to clipboard
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard
          .writeText(url)
          .then(() => {
            alert(
              `✅ ${sourceName} URL copied to clipboard!\n\nURL: ${url}\n\nYou can now paste this in your browser.`
            );
          })
          .catch(() => {
            this.showManualCopyDialog(url, sourceName);
          });
      } else {
        this.showManualCopyDialog(url, sourceName);
      }
    } else {
      // Try using Electron API as alternative
      if (window.airisAPI && window.airisAPI.openExternalUrl) {
        if (confirm(`Try opening ${sourceName} using system browser?`)) {
          try {
            const result = await window.airisAPI.openExternalUrl(url);
            if (result.success) {
              console.log(
                `✅ Successfully opened ${sourceName} using system browser`
              );
            } else {
              alert(`Failed to open ${sourceName}: ${result.error}`);
            }
          } catch (error) {
            console.error(
              `Error using system browser for ${sourceName}:`,
              error
            );
            alert(`Failed to open ${sourceName} using system browser.`);
          }
        }
      } else {
        // Last resort: try opening in same tab (for web environments)
        if (confirm(`Try opening ${sourceName} in the same tab?`)) {
          window.location.href = url;
        }
      }
    }
  }

  showManualCopyDialog(url, sourceName) {
    // Fallback: show URL in a dialog for manual copying
    const dialog = `${sourceName} URL:\n\n${url}\n\nPlease copy this URL manually and paste it in your browser.`;
    alert(dialog);
  }

  findClusterForArticle(article) {
    // Find the cluster that corresponds to this article
    if (!this.currentNewsData || !this.currentNewsData.clustered_articles) {
      return null;
    }

    // Try to match by title since that's what we're using as the unified title
    return this.currentNewsData.clustered_articles.find(
      (cluster) => cluster.unified_title === article.title
    );
  }

  extractDomain(url) {
    try {
      return new URL(url).hostname;
    } catch (error) {
      return url;
    }
  }

  async updateSchedulerStatus() {
    try {
      const response = await window.apiService.api.get(
        "/api/finance-news/scheduler/status"
      );
      if (response.data.status === "success") {
        const scheduler = response.data.scheduler;
        const hintElement = document.querySelector(".news-refresh-hint span");

        if (
          hintElement &&
          scheduler.is_running &&
          scheduler.next_fetch_in_minutes !== null
        ) {
          const t = window.languageService
            ? window.languageService.t.bind(window.languageService)
            : (key) => key;
          const nextUpdate = scheduler.next_fetch_in_minutes;

          if (nextUpdate <= 0) {
            hintElement.textContent = t("autoUpdateInfo").replace(
              "45 minutes",
              "updating now"
            );
          } else if (nextUpdate < 60) {
            hintElement.textContent = t("autoUpdateInfo").replace(
              "45 minutes",
              `${nextUpdate} minutes`
            );
          } else {
            hintElement.textContent = t("autoUpdateInfo");
          }
        }
      }
    } catch (error) {
      // Silently fail - not critical
      console.debug("Could not fetch scheduler status:", error.message);
    }
  }

  updateDynamicTexts() {
    if (!window.languageService) return;

    const t = window.languageService.t.bind(window.languageService);

    // Update suggestion chips
    const chips = document.querySelectorAll(".suggestion-chip");
    chips.forEach((chip, index) => {
      const chipKeys = [
        "suggestedQuestions.latestReport",
        "suggestedQuestions.analyzeTrends",
        "suggestedQuestions.expenseSummary",
      ];
      if (chipKeys[index]) {
        chip.textContent = t(chipKeys[index]);
      }
    });

    // Update upload progress stages
    this.updateProgressStage = (
      iconElement,
      stageElement,
      iconClass,
      stageText
    ) => {
      iconElement.className = `${iconClass} progress-icon`;

      // Use translation for stage text
      let translatedText = stageText;
      if (stageText.includes("Preparing")) translatedText = t("preparing");
      else if (stageText.includes("Reading")) translatedText = t("readingFile");
      else if (stageText.includes("Uploading")) translatedText = t("uploading");
      else if (stageText.includes("Processing with AI"))
        translatedText = t("processingWithAI");
      else if (stageText.includes("complete"))
        translatedText = t("uploadComplete");
      else if (stageText.includes("failed")) translatedText = t("uploadFailed");

      stageElement.textContent = translatedText;
    };

    // Update status texts
    const statusTexts = document.querySelectorAll(".status-text");
    statusTexts.forEach((status) => {
      if (status.textContent.includes("Loading")) {
        status.textContent = t("loading");
      } else if (status.textContent.includes("Connecting")) {
        status.textContent = t("connecting");
      }
    });

    // Update empty states
    this.updateEmptyStates();

    // Update news refresh button text
    const refreshButton = document.getElementById("refresh-news");
    if (refreshButton && !refreshButton.disabled) {
      refreshButton.innerHTML = `<i class="fas fa-sync-alt"></i> ${t(
        "refresh"
      )}`;
    }

    // Refresh current tab content with new language
    if (this.currentTab === "files") {
      this.loadFileLibrary();
    } else if (this.currentTab === "news") {
      this.loadFinanceNews();
    }
  }

  updateEmptyStates() {
    if (!window.languageService) return;

    const t = window.languageService.t.bind(window.languageService);

    // Update file empty state
    const fileEmptyState = document.querySelector("#files-grid .empty-state");
    if (fileEmptyState) {
      const heading = fileEmptyState.querySelector("h3");
      const paragraph = fileEmptyState.querySelector("p");
      const button = fileEmptyState.querySelector("button");

      if (heading) heading.textContent = t("noDocuments");
      if (paragraph) paragraph.textContent = t("uploadToGetStarted");
      if (button) button.textContent = t("uploadFilesBtn");
    }
  }

  // Document Verification functionality
  setupVerificationEventListeners() {
    const verificationUploadArea = document.getElementById(
      "verification-upload-area"
    );
    const verificationFileInput = document.getElementById(
      "verification-file-input"
    );
    const verificationBrowseBtn = document.getElementById(
      "verification-browse-files"
    );
    const verifyDocumentBtn = document.getElementById("verify-document-btn");
    const verifyAnotherBtn = document.getElementById("verify-another-document");
    const downloadReportBtn = document.getElementById(
      "download-verification-report"
    );

    if (verificationUploadArea) {
      // Drag and drop functionality
      verificationUploadArea.addEventListener(
        "dragover",
        this.handleVerificationDragOver.bind(this)
      );
      verificationUploadArea.addEventListener(
        "dragleave",
        this.handleVerificationDragLeave.bind(this)
      );
      verificationUploadArea.addEventListener(
        "drop",
        this.handleVerificationDrop.bind(this)
      );
      verificationUploadArea.addEventListener("click", () =>
        verificationFileInput?.click()
      );
    }

    if (verificationBrowseBtn) {
      verificationBrowseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        verificationFileInput?.click();
      });
    }

    if (verificationFileInput) {
      verificationFileInput.addEventListener(
        "change",
        this.handleVerificationFileSelect.bind(this)
      );
    }

    if (verifyDocumentBtn) {
      verifyDocumentBtn.addEventListener(
        "click",
        this.startDocumentVerification.bind(this)
      );
    }

    if (verifyAnotherBtn) {
      verifyAnotherBtn.addEventListener(
        "click",
        this.resetVerificationInterface.bind(this)
      );
    }

    if (downloadReportBtn) {
      downloadReportBtn.addEventListener(
        "click",
        this.downloadVerificationReport.bind(this)
      );
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
    const allowedTypes = [
      ".pdf",
      ".jpg",
      ".jpeg",
      ".png",
      ".tiff",
      ".tif",
      ".bmp",
    ];
    const fileExtension = "." + file.name.split(".").pop().toLowerCase();

    if (!allowedTypes.includes(fileExtension)) {
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showNotification(
        `${t("unsupportedFileType")}: ${fileExtension}. ${t(
          "verificationSupportedFormats"
        )}`,
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
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showNotification(t("pleaseSelectFile"), "warning");
      return;
    }

    const verificationType =
      document.getElementById("verification-type")?.value || "auto";
    const verifyBtn = document.getElementById("verify-document-btn");
    const resultsContainer = document.getElementById("verification-results");

    try {
      // Disable button and show loading state
      if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.innerHTML =
          '<i class="fas fa-spinner fa-spin"></i> <span>Verifying...</span>';
      }

      // Show progress indicator
      this.showVerificationProgress("Starting verification...");

      // Call verification API
      const result = await window.apiService.verifyDocument(
        this.selectedVerificationFile,
        verificationType,
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

        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        this.showNotification(t("verificationCompleted"), "success");
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error("Verification failed:", error);
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showNotification(
        `${t("verificationFailed")}: ${error.message}`,
        "error"
      );

      this.hideVerificationProgress();
    } finally {
      // Re-enable button
      if (verifyBtn) {
        verifyBtn.disabled = false;
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        verifyBtn.innerHTML = `<i class="fas fa-shield-alt"></i> <span>${t(
          "verifyDocument"
        )}</span>`;
      }
    }
  }

  showVerificationProgress(message) {
    const uploadSection = document.querySelector(
      ".verification-upload-section"
    );
    if (!uploadSection) return;

    // Remove existing progress indicator
    const existingProgress = uploadSection.querySelector(
      ".verification-progress"
    );
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
      statusBadge.textContent =
        result.status || window.languageService?.get("unknown") || "Unknown";
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
      const color =
        score >= 0.8 ? "#22c55e" : score >= 0.6 ? "#f59e0b" : "#ef4444";

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
      detectedType.textContent =
        result.verification_type ||
        window.languageService?.get("unknown") ||
        "Unknown";
    }

    if (finalStatus) {
      finalStatus.textContent =
        result.status || window.languageService?.get("unknown") || "Unknown";
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
      fraud_analysis: "Fraud Analysis",
    };

    Object.entries(stages).forEach(([stageName, stageData]) => {
      const stageCard = this.createStageCard(
        stageNames[stageName] || stageName,
        stageData
      );
      stagesGrid.appendChild(stageCard);
    });
  }

  createStageCard(stageName, stageData) {
    const card = document.createElement("div");
    card.className = "stage-card";

    // Determine stage status
    let stageStatus = "warning";
    let statusIcon = "fas fa-exclamation-triangle";

    if (
      stageData.passed ||
      stageData.valid ||
      stageData.consistent ||
      stageData.risk_level === "low"
    ) {
      stageStatus = "passed";
      statusIcon = "fas fa-check";
    } else if (stageData.failed || stageData.risk_level === "high") {
      stageStatus = "failed";
      statusIcon = "fas fa-times";
    }

    // Get stage score
    const score =
      stageData.score || stageData.confidence || stageData.quality_score || 0;
    const percentage = Math.round(score * 100);

    // Get stage details
    const issues = stageData.issues || stageData.indicators || [];
    const details = Array.isArray(issues)
      ? issues.join(", ")
      : stageData.assessment || stageData.reasoning || "No details available";

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
      issuesList.innerHTML = allIssues
        .map(
          (issue) => `
        <div class="issue-item">
          <i class="fas fa-exclamation-triangle"></i>
          <span class="issue-text">${Utils.escapeHtml(issue)}</span>
        </div>
      `
        )
        .join("");
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
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        uploadText.textContent = t("verificationDragDrop");
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
    const verificationContainer = document.querySelector(
      ".verification-container"
    );
    if (verificationContainer) {
      verificationContainer.scrollIntoView({ behavior: "smooth" });
    }
  }

  downloadVerificationReport() {
    if (!this.currentVerificationResult) {
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showNotification(t("noVerificationDataToDownload"), "warning");
      return;
    }

    // Create a comprehensive report
    const report = {
      document_name: this.selectedVerificationFile?.name || "Unknown Document",
      verification_timestamp: new Date().toISOString(),
      verification_result: this.currentVerificationResult,
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

    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;
    this.showNotification(t("reportDownloaded"), "success");
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
          this.selectedFiles = this.allFiles.map((file) => file.name);
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

    filesList.innerHTML = this.allFiles
      .map((file) => {
        const isSelected = this.selectedFiles.includes(file.name);
        const fileExtension = file.name.split(".").pop().toLowerCase();
        const fileIcon = this.getFileIcon(fileExtension);
        const fileSize = this.formatFileSize(file.size);

        return `
        <div class="file-selection-item ${
          isSelected ? "selected" : ""
        }" data-filename="${file.name}">
          <div class="file-checkbox ${isSelected ? "checked" : ""}">
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
      })
      .join("");
  }

  getFileIcon(extension) {
    const iconMap = {
      pdf: "fas fa-file-pdf",
      docx: "fas fa-file-word",
      doc: "fas fa-file-word",
      xlsx: "fas fa-file-excel",
      xls: "fas fa-file-excel",
      txt: "fas fa-file-alt",
      jpg: "fas fa-file-image",
      jpeg: "fas fa-file-image",
      png: "fas fa-file-image",
      gif: "fas fa-file-image",
      bmp: "fas fa-file-image",
      tiff: "fas fa-file-image",
    };
    return iconMap[extension] || "fas fa-file";
  }

  formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
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
    this.selectedFiles = [...this.allFiles.map((file) => file.name)];
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
    const fileItems = document.querySelectorAll(".file-selection-item");

    fileItems.forEach((item) => {
      const fileName = item.dataset.filename;
      const isSelected = this.selectedFiles.includes(fileName);
      const checkbox = item.querySelector(".file-checkbox");

      if (isSelected) {
        item.classList.add("selected");
        checkbox.classList.add("checked");
      } else {
        item.classList.remove("selected");
        checkbox.classList.remove("checked");
      }
    });
  }

  updateFileSelectionButton() {
    const button = document.getElementById("file-selection-btn");
    if (!button) return;

    const selectedCount = this.selectedFiles.length;
    const totalCount = this.allFiles.length;

    if (selectedCount === 0) {
      button.classList.remove("has-selection");
      button.removeAttribute("data-count");
      button.title = "Select files to include";
    } else if (selectedCount === totalCount) {
      button.classList.add("has-selection");
      button.setAttribute("data-count", "All");
      button.title = `All ${totalCount} files selected`;
    } else {
      button.classList.add("has-selection");
      button.setAttribute("data-count", selectedCount);
      button.title = `${selectedCount} of ${totalCount} files selected`;
    }
  }

  insertPrompt(type) {
    const chatInput = document.getElementById("chat-input");
    if (!chatInput) return;

    let prompt = "";
    const selectedFilesList =
      this.selectedFiles.length > 0
        ? `Selected files: ${this.selectedFiles.join(", ")}\n\n`
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

  // Upload file with progress tracking
  async uploadFileWithProgress(file, fileIndex) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append("file", file);

      // Update progress bar during upload
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          this.updateFileUploadProgress(fileIndex, percentComplete);
        }
      });

      // Handle successful upload
      xhr.addEventListener("load", () => {
        try {
          const response = JSON.parse(xhr.responseText);
          this.updateFileUploadProgress(fileIndex, 100);
          resolve(response);
        } catch (error) {
          reject(new Error("Invalid response format"));
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
      xhr.open("POST", "http://localhost:8000/upload");
      xhr.send(formData);
    });
  }

  // Update file upload progress
  updateFileUploadProgress(fileIndex, percentage) {
    const filePreview = document.querySelector(
      `[data-file-index="${fileIndex}"]`
    );
    if (filePreview) {
      const progressFill = filePreview.querySelector(".upload-progress-fill");
      const progressText = filePreview.querySelector(".upload-progress-text");

      if (progressFill) {
        progressFill.style.width = `${percentage}%`;
      }

      if (progressText) {
        progressText.textContent = `${percentage}%`;
      }
    }
  }

  // Update file upload status (success/failure)
  updateFileUploadStatus(fileIndex, success, errorMessage = "") {
    const filePreview = document.querySelector(
      `[data-file-index="${fileIndex}"]`
    );
    if (filePreview) {
      const uploadStatus = filePreview.querySelector(".upload-status");
      const progressContainer = filePreview.querySelector(
        ".upload-progress-container"
      );

      if (success) {
        uploadStatus.textContent = "✓ Uploaded";
        uploadStatus.className = "upload-status";
        uploadStatus.style.color = "var(--accent-success, #10b981)";
      } else {
        uploadStatus.textContent = `❌ ${
          errorMessage || window.languageService?.get("failed") || "Failed"
        }`;
        uploadStatus.className = "upload-status";
        uploadStatus.style.color = "var(--error-color, #ef4444)";
      }

      // Hide progress bar after completion
      if (progressContainer) {
        progressContainer.style.display = "none";
      }
    }
  }

  // Update files header after all uploads complete
  updateFilesHeader(uploadedCount) {
    const latestMessage = document.querySelector(
      ".chat-message:last-child .uploaded-files-header"
    );
    if (latestMessage) {
      latestMessage.textContent = `📎 Files (${uploadedCount})`;
    }
  }

  // Credit Calculator Methods
  calculateLoan() {
    try {
      // Get input values
      const loanAmountInput = document.getElementById("loan-amount");
      const loanTermInput = document.getElementById("loan-term");
      const interestRateInput = document.getElementById("interest-rate");

      if (!loanAmountInput || !loanTermInput || !interestRateInput) {
        throw new Error("Gerekli form elemanları bulunamadı");
      }

      // Parse and validate inputs
      let loanAmount = this.parseNumber(loanAmountInput.value);
      let loanTerm = parseInt(loanTermInput.value);
      let interestRate = this.parseNumber(interestRateInput.value);

      // Validation with specific error messages
      if (isNaN(loanAmount) || loanAmount <= 0) {
        loanAmountInput.focus();
        throw new Error("Kredi tutarı 0'dan büyük geçerli bir sayı olmalıdır");
      }
      if (loanAmount > 100000000) {
        // 100 million limit
        loanAmountInput.focus();
        throw new Error("Kredi tutarı çok yüksek (maksimum 100.000.000 TL)");
      }
      if (isNaN(loanTerm) || loanTerm <= 0) {
        loanTermInput.focus();
        throw new Error("Kredi vadesi 0'dan büyük geçerli bir sayı olmalıdır");
      }
      if (loanTerm > 360) {
        // 30 years max
        loanTermInput.focus();
        throw new Error("Kredi vadesi çok uzun (maksimum 360 ay)");
      }
      if (isNaN(interestRate) || interestRate < 0) {
        interestRateInput.focus();
        throw new Error("Faiz oranı 0 veya pozitif bir sayı olmalıdır");
      }
      if (interestRate > 100) {
        interestRateInput.focus();
        throw new Error("Faiz oranı %100'den küçük olmalıdır");
      }

      // Convert annual interest rate to monthly rate
      // r = Annual Rate / 12 / 100 (as shown in the formula image)
      const r = interestRate / 100;

      // Calculate monthly payment using the exact annuity formula from the image
      // A = P × [r(1+r)^n] / [(1+r)^n - 1]
      let monthlyPayment;
      if (r === 0) {
        // If no interest, simple division
        monthlyPayment = loanAmount / loanTerm;
      } else {
        // Apply the exact annuity formula
        const onePlusR = 1 + r; // (1+r)
        const powerTerm = Math.pow(onePlusR, loanTerm); // (1+r)^n
        const numerator = r * powerTerm; // r(1+r)^n
        const denominator = powerTerm - 1; // (1+r)^n - 1

        monthlyPayment = loanAmount * (numerator / denominator);
      }

      // Calculate total payment
      const totalPayment = monthlyPayment * loanTerm;

      // Calculate total interest
      const totalInterest = totalPayment - loanAmount;

      // Display results
      this.displayCalculationResults({
        monthlyPayment,
        totalPayment,
        totalInterest,
        principal: loanAmount,
        termMonths: loanTerm,
        annualRate: interestRate,
      });

      // Show success notification
      this.showNotification("Hesaplama başarıyla tamamlandı", "success");
    } catch (error) {
      this.showNotification(error.message, "error");
    }
  }

  displayCalculationResults(results) {
    const resultsContainer = document.getElementById("calculator-results");
    const monthlyPaymentEl = document.getElementById("monthly-payment");
    const totalPaymentEl = document.getElementById("total-payment");
    const totalInterestEl = document.getElementById("total-interest");

    if (resultsContainer) {
      resultsContainer.style.display = "block";
    }

    if (monthlyPaymentEl) {
      monthlyPaymentEl.textContent = this.formatCurrency(
        results.monthlyPayment
      );
    }

    if (totalPaymentEl) {
      totalPaymentEl.textContent = this.formatCurrency(results.totalPayment);
    }

    if (totalInterestEl) {
      totalInterestEl.textContent = this.formatCurrency(results.totalInterest);
    }

    // Smooth scroll to results within the calculator container
    setTimeout(() => {
      const calculatorContainer = document.querySelector(
        ".calculator-container"
      );
      if (resultsContainer && calculatorContainer) {
        const containerRect = calculatorContainer.getBoundingClientRect();
        const resultsRect = resultsContainer.getBoundingClientRect();
        const scrollTop =
          calculatorContainer.scrollTop +
          (resultsRect.top - containerRect.top) -
          20;

        calculatorContainer.scrollTo({
          top: scrollTop,
          behavior: "smooth",
        });
      }
    }, 100);
  }

  resetCalculator() {
    // Clear input fields
    const loanAmountInput = document.getElementById("loan-amount");
    const loanTermInput = document.getElementById("loan-term");
    const interestRateInput = document.getElementById("interest-rate");

    if (loanAmountInput) loanAmountInput.value = "";
    if (loanTermInput) loanTermInput.value = "";
    if (interestRateInput) interestRateInput.value = "";

    // Hide results
    const resultsContainer = document.getElementById("calculator-results");
    if (resultsContainer) {
      resultsContainer.style.display = "none";
    }
  }

  // Helper method to parse numbers with Turkish and English number formats
  parseNumber(value) {
    if (typeof value !== "string") {
      return parseFloat(value) || 0;
    }

    // Handle empty string
    if (!value.trim()) {
      return 0;
    }

    // Remove spaces and handle both Turkish (,) and English (.) decimal separators
    // If the string contains both . and ,, assume . is thousands separator and , is decimal
    if (value.includes(".") && value.includes(",")) {
      // Turkish format: 1.000.000,50
      return parseFloat(value.replace(/\./g, "").replace(",", ".")) || 0;
    } else if (value.includes(",") && !value.includes(".")) {
      // Only comma, treat as decimal separator: 1000,50
      return parseFloat(value.replace(",", ".")) || 0;
    } else {
      // English format or integer: 1000000.50 or 1000000
      return parseFloat(value.replace(/\s/g, "")) || 0;
    }
  }

  // Helper method to format currency
  formatCurrency(amount) {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  // News Chat Methods
  initializeNewsChat(article) {
    this.currentNewsArticle = article;
    this.newsChatHistory = [];

    // Initialize chat input handlers
    this.initializeNewsChatInputs();

    // Reset chat interface
    this.resetNewsChatInterface();
  }

  initializeNewsChatInputs() {
    const chatInput = document.getElementById("news-chat-input");
    const chatSendBtn = document.getElementById("news-chat-send");
    const chatInputMessages = document.getElementById(
      "news-chat-input-messages"
    );
    const chatSendBtnMessages = document.getElementById(
      "news-chat-send-messages"
    );

    if (chatInput && chatSendBtn) {
      chatInput.addEventListener("input", () => {
        chatSendBtn.disabled = !chatInput.value.trim();
      });

      chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey && chatInput.value.trim()) {
          e.preventDefault();
          this.sendNewsChatMessage(chatInput.value.trim());
        }
      });

      chatSendBtn.addEventListener("click", () => {
        if (chatInput.value.trim()) {
          this.sendNewsChatMessage(chatInput.value.trim());
        }
      });
    }

    if (chatInputMessages && chatSendBtnMessages) {
      chatInputMessages.addEventListener("input", () => {
        chatSendBtnMessages.disabled = !chatInputMessages.value.trim();
      });

      chatInputMessages.addEventListener("keypress", (e) => {
        if (
          e.key === "Enter" &&
          !e.shiftKey &&
          chatInputMessages.value.trim()
        ) {
          e.preventDefault();
          this.sendNewsChatMessage(chatInputMessages.value.trim());
        }
      });

      chatSendBtnMessages.addEventListener("click", () => {
        if (chatInputMessages.value.trim()) {
          this.sendNewsChatMessage(chatInputMessages.value.trim());
        }
      });
    }
  }

  resetNewsChatInterface() {
    const inputContainer = document.getElementById("news-chat-input-container");
    const messagesContainer = document.getElementById("news-chat-messages");
    const messagesList = document.getElementById(
      "news-chat-messages-container"
    );

    if (inputContainer) inputContainer.style.display = "block";
    if (messagesContainer) messagesContainer.style.display = "none";
    if (messagesList) messagesList.innerHTML = "";

    // Clear Q&A container and blocks
    const qaContainer = document.getElementById("news-qa-container");
    if (qaContainer) {
      qaContainer.remove();
    }

    // Restore fixed positioning when Q&A container is removed
    const chatContainer = document.getElementById("news-chat-input-container");
    const detail = document.getElementById("news-detail");
    const articleElement = document.querySelector(".news-detail-article");

    if (chatContainer && detail) {
      chatContainer.classList.add("news-chat-fixed");
      detail.classList.add("news-chat-fixed-active");
    }

    // Restore padding for fixed input
    if (articleElement) {
      articleElement.style.paddingBottom = "";
    }

    // Reset Q&A mode state
    this.newsQAStarted = false;
  }

  async sendNewsChatMessage(message) {
    // Clear input
    const chatInput = document.getElementById("news-chat-input");
    const chatInputMessages = document.getElementById(
      "news-chat-input-messages"
    );

    if (chatInput) chatInput.value = "";
    if (chatInputMessages) chatInputMessages.value = "";

    // Disable send buttons
    const chatSendBtn = document.getElementById("news-chat-send");
    const chatSendBtnMessages = document.getElementById(
      "news-chat-send-messages"
    );

    if (chatSendBtn) chatSendBtn.disabled = true;
    if (chatSendBtnMessages) chatSendBtnMessages.disabled = true;

    const isFirst = !this.newsQAStarted;

    // Show chat interface if this is the first message
    if (isFirst) {
      this.showNewsChatInterface();

      // Mark Q&A mode started so next messages append
      this.newsQAStarted = true;

      // Create a container for Q&A blocks after the original article content
      const qaContainerId = "news-qa-container";
      let qaContainer = document.getElementById(qaContainerId);
      if (!qaContainer) {
        qaContainer = document.createElement("div");
        qaContainer.id = qaContainerId;
        qaContainer.className = "news-qa-container";

        // Add a divider and header before Q&A section
        qaContainer.innerHTML = `
          <hr class="news-qa-divider" />
          <div class="news-qa-header">
            <h3>
              <i class="fas fa-comments"></i>
              Haberle İlgili Sorular
            </h3>
            <p>AI ile haber hakkında soru sorabilir ve detaylı bilgi alabilirsiniz</p>
          </div>
        `;

        // Insert after the sources section or at the end of the article
        const sourcesSection = document.querySelector(
          ".news-detail-sources-section"
        );
        const article = document.querySelector(".news-detail-article");

        if (sourcesSection && article) {
          // Insert after sources section
          sourcesSection.parentNode.insertBefore(
            qaContainer,
            sourcesSection.nextSibling
          );
        } else if (article) {
          // Insert at the end of article
          article.appendChild(qaContainer);
        }

        // Remove fixed positioning from chat input when Q&A container is created
        const chatContainer = document.getElementById(
          "news-chat-input-container"
        );
        const detail = document.getElementById("news-detail");
        const articleElement = document.querySelector(".news-detail-article");

        if (chatContainer && detail) {
          chatContainer.classList.remove("news-chat-fixed");
          detail.classList.remove("news-chat-fixed-active");
        }

        // Remove extra padding from article when Q&A is active
        if (articleElement) {
          articleElement.style.paddingBottom = "0";
        }
      }
    }

    // Show typing indicator
    this.showNewsChatTyping();

    // Create Q&A block for this conversation
    let qaContentId = null;
    const mount = document.getElementById("news-qa-container");
    if (mount) {
      qaContentId = `news-qa-content-${Date.now()}`;
      const block = document.createElement("div");
      block.className = "news-qa-block";

      block.innerHTML = `
        <div class="message user-message">
          <div class="message-avatar">
            <i class="fas fa-user"></i>
          </div>
          <div class="message-content">
            <div class="message-text">${Utils.escapeHtml(message)}</div>
            <div class="message-time">${new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}</div>
          </div>
        </div>
        <div class="message assistant-message">
          <div class="message-avatar">
            <i class="fas fa-robot"></i>
          </div>
          <div class="message-content">
            <div class="message-text" id="${qaContentId}">
              <div class="news-qa-thinking">
                <span>AI yanıt hazırlıyor...</span>
                <div class="typing-dots">
                  <div class="typing-dot"></div>
                  <div class="typing-dot"></div>
                  <div class="typing-dot"></div>
                </div>
              </div>
            </div>
            <div class="message-time">${new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}</div>
          </div>
        </div>
      `;
      mount.appendChild(block);

      // No automatic scrolling - let user control scroll position
    }

    try {
      // Send to backend
      const response = await this.sendNewsQuery(message);

      if (response && response.response) {
        // Update the Q&A block with the response
        if (qaContentId) {
          const contentEl = document.getElementById(qaContentId);
          if (contentEl) {
            contentEl.innerHTML = this.formatNewsChatMessage(response.response);
          }
        }
      } else {
        // Update Q&A block with error
        if (qaContentId) {
          const contentEl = document.getElementById(qaContentId);
          if (contentEl) {
            contentEl.innerHTML = `Üzgünüm, isteğinizi işlerken bir hata oluştu. Lütfen tekrar deneyin.`;
          }
        }
      }
    } catch (error) {
      console.error("News chat error:", error);

      // Update Q&A block with error
      if (qaContentId) {
        const contentEl = document.getElementById(qaContentId);
        if (contentEl) {
          contentEl.innerHTML = `Üzgünüm, isteğinizi işlerken bir hata oluştu. Lütfen tekrar deneyin.`;
        }
      }
    } finally {
      this.hideNewsChatTyping();

      // Remove all thinking indicators
      document
        .querySelectorAll(".news-qa-thinking")
        .forEach((el) => el.remove());

      // Re-enable send buttons
      if (chatSendBtn) chatSendBtn.disabled = false;
      if (chatSendBtnMessages) chatSendBtnMessages.disabled = false;
    }
  }

  showNewsChatInterface() {
    const inputContainer = document.getElementById("news-chat-input-container");
    const messagesContainer = document.getElementById("news-chat-messages");

    // Keep input visible persistently; hide old messages container since we use Q&A blocks
    if (inputContainer) inputContainer.style.display = "block";
    if (messagesContainer) messagesContainer.style.display = "none";
  }

  addNewsChatMessage(role, content) {
    const messagesContainer = document.getElementById(
      "news-chat-messages-container"
    );
    if (!messagesContainer) return;

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}-message`;

    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    if (role === "user") {
      messageDiv.innerHTML = `
        <div class="message-avatar">
          <i class="fas fa-user"></i>
        </div>
        <div class="message-content">
          <div class="message-text">${this.formatNewsChatMessage(content)}</div>
          <div class="message-time">${time}</div>
        </div>
      `;
    } else if (role === "assistant") {
      messageDiv.innerHTML = `
        <div class="message-avatar">
          <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
          <div class="message-text">${this.formatNewsChatMessage(content)}</div>
          <div class="message-time">${time}</div>
        </div>
      `;
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Add to history
    this.newsChatHistory.push({ role, content, timestamp: new Date() });
  }

  formatNewsChatMessage(content) {
    // Enhanced markdown formatting
    let formatted = content;

    // Convert bold text (**text**)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Convert italic text (*text*)
    formatted = formatted.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Convert headers (# Header) - must be done before line break conversion
    formatted = formatted.replace(/^### (.*$)/gm, "<h3>$1</h3>");
    formatted = formatted.replace(/^## (.*$)/gm, "<h2>$1</h2>");
    formatted = formatted.replace(/^# (.*$)/gm, "<h1>$1</h1>");

    // Convert numbered lists (1. item)
    formatted = formatted.replace(/^(\d+)\.\s+(.*$)/gm, "<li>$2</li>");
    formatted = formatted.replace(/(<li>.*<\/li>)/s, "<ol>$1</ol>");

    // Convert bullet lists (- item or * item)
    formatted = formatted.replace(/^[-*]\s+(.*$)/gm, "<li>$1</li>");
    formatted = formatted.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

    // Convert links
    formatted = formatted.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    // Convert line breaks last (after all other formatting)
    formatted = formatted.replace(/\n/g, "<br>");

    return formatted;
  }

  showNewsChatTyping() {
    const messagesContainer = document.getElementById(
      "news-chat-messages-container"
    );
    if (!messagesContainer) return;

    const typingDiv = document.createElement("div");
    typingDiv.className = "message assistant-message";
    typingDiv.id = "news-chat-typing";

    typingDiv.innerHTML = `
      <div class="message-avatar">
        <i class="fas fa-robot"></i>
      </div>
      <div class="message-content">
        <div class="message-text">
          <span>AI is thinking</span>
          <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        </div>
      </div>
    `;

    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  hideNewsChatTyping() {
    const typingDiv = document.getElementById("news-chat-typing");
    if (typingDiv) {
      typingDiv.remove();
    }
  }

  async sendNewsQuery(message) {
    try {
      const apiService = window.apiService;
      if (!apiService) {
        throw new Error("API service not available");
      }

      // Prepare news context
      const newsContext = this.prepareNewsContext();

      // Send query to backend
      const response = await apiService.sendNewsChatQuery(message, newsContext);
      return response;
    } catch (error) {
      console.error("Error sending news query:", error);
      throw error;
    }
  }

  prepareNewsContext() {
    if (!this.currentNewsArticle) return {};

    const clusterData = this.findClusterForArticle(this.currentNewsArticle);

    return {
      title: this.currentNewsArticle.title,
      summary:
        this.currentNewsArticle.summary ||
        this.currentNewsArticle.unified_description ||
        "",
      content: this.currentNewsArticle.content || "",
      source: this.currentNewsArticle.source,
      sources: clusterData?.sources || this.currentNewsArticle.sources || [],
      published: this.currentNewsArticle.published,
      url: this.currentNewsArticle.url,
      cluster_data: clusterData || null,
    };
  }
}

// Export for global access
window.UIComponents = UIComponents;

/**
 * UI Components for AIris Electron App
 * Handles all user interface interactions and component management
 */

class UIComponents {
  constructor() {
    this.currentTab = "chat";
    this.chatHistory = [];
    this.uploadedFiles = [];
    this.chatUploadedFiles = [];
    this.isProcessing = false;
    this.isDarkMode = false;
    this.webSearchEnabled = Utils.isWebSearchEnabled();

    this.newsRefreshInterval = null;
    this.lastNewsUpdate = null;

    this.currentSessionId = null;
    this.chatSessions = [];

    this.selectedFiles = [];
    this.allFiles = [];
    this.fileSelectionModal = null;
    this.hasInitializedFiles = false;

    // Profile modal state
    this.selectedProfileFiles = []; // Sadece profile modal için
    this.profileModal = null;

    this.init();
    if (window.languageService) {
      window.languageService.subscribe(() => this.updateDynamicTexts());
    }
  }

  init() {
    this.setupEventListeners();
    this.initializeComponents();
    this.loadAndSelectAllFiles();
    this.setupFileSearch();

    this.loadProfiles();

    // Profile modal setup
    this.setupProfileModal();
    this.setupProfileSelect();
    this.setupSidebarToggle();
    this.initSidebar();
    this.setupInputResize();

    const webSearchToggle = document.getElementById("web-search-toggle");
    if (webSearchToggle && this.webSearchEnabled) webSearchToggle.classList.add("active");

    if (window.languageService) {
      const languageSetting = document.getElementById("language-setting");
      if (languageSetting) languageSetting.value = window.languageService.getCurrentLanguage();
      window.languageService.updatePageTexts();
    }
  }
setupInputResize() {
    const textarea = document.getElementById('chat-input');
    if (!textarea) return;

    const adjustHeight = () => {
        // 1. Önce yüksekliği "tek satır" boyutuna (24px) sabitle.
        // 'auto' kullanmak bazen titremeye veya yanlış hesaplamaya (48px'e atlamaya) neden olur.
        textarea.style.height = '24px';

        // 2. Şimdi içeriğin gerçekte ne kadar yer kapladığını ölç
        let newHeight = textarea.scrollHeight;

        // 3. Eğer scrollHeight 24px'ten büyükse (yani yazı 2. satıra taştıysa) büyüt
        // (Kırılganlık payı için > 24 yerine > 25 diyebiliriz ama > 24 genelde yeterlidir)
        if (newHeight > 24) {
            
            if (newHeight > 96) {
                textarea.style.height = '96px';
                textarea.style.overflowY = 'auto';
            } else {
                textarea.style.height = newHeight + 'px';
                textarea.style.overflowY = 'hidden';
            }
            
        } else {
            // Eğer yazı tek satıra sığıyorsa, 24px olarak kalsın
            // (Yukarıda zaten 24px'e eşitlemiştik, burada overflow'u gizlemek yeterli)
            textarea.style.overflowY = 'hidden';
        }
    };

    textarea.addEventListener('input', adjustHeight);

    // Başlangıçta bir kez çalıştır
    adjustHeight();
}


initSidebar() {
  const navItems = document.querySelectorAll('.nav-item:not(.collapsible)');
  const collapsible = document.querySelector('.nav-item.collapsible');
  const subMenu = document.querySelector('.sub-menu');
  const subItems = document.querySelectorAll('.sub-item');
  const balanceSections = document.querySelectorAll('.tab-content[id$="-tab"]');

  // İlk yüklemede tüm aktiflikleri temizle
  navItems.forEach(item => item.classList.remove('active'));
  subItems.forEach(item => item.classList.remove('active'));
  if(collapsible) collapsible.classList.remove('active');
  balanceSections.forEach(sec => sec.classList.remove('active'));

  // Sayfa açıldığında chat nav varsayılan aktif olsun
  const chatNav = document.querySelector('.nav-item[data-tab="chat"]');
  if (chatNav) {
    chatNav.classList.add('active');
    const chatTab = document.getElementById('chat-tab');
    if (chatTab) chatTab.classList.add('active');
  }

  // Nav item click
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(i => i.classList.remove('active'));
      subItems.forEach(i => i.classList.remove('active'));
      if(collapsible) collapsible.classList.remove('active');
      balanceSections.forEach(sec => sec.classList.remove('active'));

      item.classList.add('active');

      // Sidebar açıkken subMenu kapat
      if (subMenu && !document.querySelector('.sidebar.collapsed')) {
        subMenu.classList.remove('open');
        subMenu.style.maxHeight = null;
      }

      // Tab göster
      const tabId = item.dataset.tab + '-tab';
      const tab = document.getElementById(tabId);
      if (tab) tab.classList.add('active');
    });
  });

  // Collapsible tıklama
  if (collapsible && subMenu) {
    collapsible.addEventListener('click', () => {
      const isCollapsed = document.querySelector('.sidebar.collapsed');

      // Sidebar açık → normal toggle
      if(!isCollapsed) {
        subMenu.classList.toggle('open');
        subMenu.style.maxHeight = subMenu.classList.contains('open')
          ? subMenu.scrollHeight + 'px'
          : null;
      } else {
        // Sidebar kapalı → floating submenu sadece burada açılır
        this.setupFloatingSubmenu(collapsible, subMenu);
      }

      // Collapsible kendisi tıklanabilir: active yap
      navItems.forEach(i => i.classList.remove('active'));
      subItems.forEach(i => i.classList.remove('active'));
      collapsible.classList.add('active');

      // Tab göster
      const tabId = collapsible.dataset.page.replace('#','') + '-tab';
      const tab = document.getElementById(tabId);
      if(tab) {
        balanceSections.forEach(sec => sec.classList.remove('active'));
        tab.classList.add('active');
      }
    });
  }

  // Sub-item tıklama
  subItems.forEach(item => {
    item.addEventListener('click', () => {
      const isCollapsed = document.querySelector('.sidebar.collapsed');

      // Aktiflikleri temizle
      navItems.forEach(i => i.classList.remove('active'));
      subItems.forEach(i => i.classList.remove('active'));
      if(collapsible) collapsible.classList.remove('active');
      balanceSections.forEach(sec => sec.classList.remove('active'));

      item.classList.add('active');

      // Tab aç
      const sectionId = item.dataset.page.replace('#', '') + '-tab';
      const section = document.getElementById(sectionId);
      if (section) section.classList.add('active');

      if (!isCollapsed) {
        // Sidebar açık → subMenu açık kalsın
        if (subMenu) {
          subMenu.classList.add('open');
          subMenu.style.maxHeight = subMenu.scrollHeight + 'px';
        }
      } else {
        // Sidebar kapalı → floating submenu zaten DOM’da yok
        if (subMenu) {
          subMenu.classList.remove('open');
          subMenu.style.maxHeight = null;
        }
      }

      location.hash = item.dataset.page;
    });
  });
}

// Floating submenu sidebar kapalıyken açmak için
setupFloatingSubmenu(collapsible, subMenu) {
  // Sadece sidebar kapalıysa çalışmalı
  if (!document.querySelector('.sidebar.collapsed')) return;

  // Önce varsa eski floating submenuyi kaldır
  const existing = document.querySelector('.floating-sub-menu');
  if(existing) existing.remove();

  // Yeni floating submenu klonla
  const clone = subMenu.cloneNode(true);
  clone.classList.add('floating-sub-menu');
  clone.style.position = 'absolute';
  clone.style.zIndex = 4000;
  clone.style.display = 'flex';
  clone.style.flexDirection = 'column';
  clone.style.maxHeight = '500px';
  clone.style.top = collapsible.offsetTop + 'px';
  clone.style.left = (collapsible.offsetWidth + 8) + 'px';
  document.querySelector('.sidebar').appendChild(clone);

  // Hover efektleri için mouseleave
  clone.addEventListener('mouseleave', () => {
    clone.remove();
  });

  // Floating submenu içindeki sub-item click
  clone.querySelectorAll('.sub-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item, .sub-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      collapsible.classList.add('active');

      // Tab göster
      const sectionId = item.dataset.page.replace('#','') + '-tab';
      document.querySelectorAll('.tab-content').forEach(sec => sec.classList.remove('active'));
      const tab = document.getElementById(sectionId);
      if(tab) tab.classList.add('active');

      clone.remove();
      location.hash = item.dataset.page;
    });
  });
}












 setupSidebarToggle() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.toggle-btn');
    // Sub-menu ve collapsible elemanlarını da seçelim
    const subMenu = document.querySelector('.sub-menu');
    const collapsible = document.querySelector('.nav-item.collapsible');

    if (!sidebar || !toggleBtn) return;

    // LocalStorage kontrolü (Mevcut kodun)
    const savedState = localStorage.getItem('sidebarState');
    if (savedState === 'expanded') {
        sidebar.classList.add('expanded');
        sidebar.classList.remove('collapsed');
    } else {
        sidebar.classList.add('collapsed');
        sidebar.classList.remove('expanded');
    }

    toggleBtn.addEventListener('click', () => {
        const isCollapsed = sidebar.classList.contains('collapsed');

        if (isCollapsed) {
            // --- SIDEBAR AÇILIYOR (Collapsed -> Expanded) ---
            sidebar.classList.remove('collapsed');
            sidebar.classList.add('expanded');
            localStorage.setItem('sidebarState', 'expanded');
            
            // İsteğe bağlı: Sidebar açıldığında sub-menu kapalı gelsin istersen buraya dokunma.
            // Eğer sidebar açılınca son durumu hatırlasın istersen burada işlem gerekir ama genelde kapalı gelmesi daha temizdir.
            
        } else {
            // --- SIDEBAR KAPANIYOR (Expanded -> Collapsed) ---
            sidebar.classList.remove('expanded');
            sidebar.classList.add('collapsed');
            localStorage.setItem('sidebarState', 'collapsed');

            // --- EKLENEN KISIM: İÇERİDE AÇIK KALAN MENÜYÜ KAPAT ---
            // Sidebar küçüldüğünde, içerideki sub-menu hala "açık" (max-height değerli) kalmamalı.
            if (subMenu && subMenu.classList.contains('open')) {
                subMenu.classList.remove('open');
                subMenu.style.maxHeight = null; // Inline stili temizle
            }

            // Collapsible butonunun 'active' durumunu da kaldırmak isteyebilirsin
            // Böylece sidebar kapalıyken ikon seçili (mavi/aktif) görünmez.
            if (collapsible) {
                collapsible.classList.remove('active');
            }
        }
    });
}

  // ---------------- Profile Modal ----------------
  loadProfiles() {
    const storedProfiles = localStorage.getItem("savedProfiles");
    this.allProfiles = storedProfiles ? JSON.parse(storedProfiles) : [];
  }

  setupProfileModal() {
    this.profileModal = document.getElementById("create-profile-selection");
    if (!this.allProfiles) this.allProfiles = [];
    this.setupProfileSelect();

    // Butonlar
    document.getElementById("open-profile-popup")?.addEventListener("click", () => this.showProfileModal());
    document.getElementById("close-profile-selection")?.addEventListener("click", () => this.hideProfileModal());
    document.getElementById("cancel-profile-popup")?.addEventListener("click", () => this.hideProfileModal());
    document.getElementById("save-profile-popup")?.addEventListener("click", () => this.saveProfiles());

    document.getElementById("select-all-profile-files")?.addEventListener("click", () => this.selectAllProfiles());
    document.getElementById("deselect-all-profile-files")?.addEventListener("click", () => this.deselectAllProfiles());

    // Arama input
    const input = document.getElementById("file-profile-selection-search");
    const clearBtn = document.getElementById("file-profile-selection-search-clear");

    input?.addEventListener("input", (e) => this.renderProfileFiles(e.target.value.trim().toLowerCase()));
    input?.addEventListener("keypress", (e) => { if (e.key === "Escape") this.clearProfileSearch(); });
    clearBtn?.addEventListener("click", () => this.clearProfileSearch());

    // Escape tuşu modal kapatma
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.profileModal.classList.contains("show")) this.hideProfileModal();
    });

    // İlk render
    this.renderProfileFiles();
  }

  showProfileModal() {
    if (!this.profileModal) return;
    this.profileModal.classList.add("show");

    // Dosyaları modalda göster
    this.renderProfileFiles();
  }

  hideProfileModal() {
    if (!this.profileModal) return;
    this.profileModal.classList.remove("show");
  }

  renderProfileFiles(filter = "") {
    const container = document.getElementById("files-profile-list");
    if (!container || !this.allFiles) return;

    let visibleFiles = filter
      ? this.allFiles.filter(f => f.name.toLowerCase().includes(filter))
      : this.allFiles;

    // Seçili dosyaları en üste taşı
    visibleFiles.sort((a, b) => {
      const aSelected = this.selectedProfileFiles.includes(a.name);
      const bSelected = this.selectedProfileFiles.includes(b.name);
      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      return 0;
    });

    container.innerHTML = visibleFiles.map(file => `
    <div class="file-selection-item profile-item ${this.selectedProfileFiles.includes(file.name) ? "selected" : ""}" data-name="${file.name}">
      <div class="file-checkbox ${this.selectedProfileFiles.includes(file.name) ? "checked" : ""}">
        <i class="fas fa-check"></i>
      </div>
      <div class="file-item-icon ${file.name.split(".").pop().toLowerCase()}">
        <i class="${this.getFileIcon(file.name.split(".").pop())}"></i>
      </div>
      <div class="file-item-info">
        <div class="file-item-name" title="${file.name}">${file.name}</div>
        <div class="file-item-size">${this.formatFileSize(file.size)}</div>
      </div>
    </div>
  `).join("");

    // Click eventleri
    container.querySelectorAll(".profile-item").forEach(item => {
      const name = item.dataset.name;
      const checkbox = item.querySelector(".file-checkbox");

      item.onclick = () => this.toggleProfileFile(name);
      checkbox.onclick = (e) => { e.stopPropagation(); this.toggleProfileFile(name); };
    });
  }

  toggleProfileFile(name) {
    const index = this.selectedProfileFiles.indexOf(name);
    if (index > -1) this.selectedProfileFiles.splice(index, 1);
    else this.selectedProfileFiles.push(name);

    this.renderProfileFiles(document.getElementById("file-profile-selection-search")?.value?.trim().toLowerCase() || "");
  }

  selectAllProfiles() {
    const filter = document.getElementById("file-profile-selection-search")?.value?.trim().toLowerCase() || "";
    const visibleFiles = filter
      ? this.allFiles.filter(f => f.name.toLowerCase().includes(filter))
      : this.allFiles;

    this.selectedProfileFiles = visibleFiles.map(f => f.name);
    this.renderProfileFiles(filter);
  }

  deselectAllProfiles() {
    const filter = document.getElementById("file-profile-selection-search")?.value?.trim().toLowerCase() || "";
    const visibleFiles = filter
      ? this.allFiles.filter(f => f.name.toLowerCase().includes(filter))
      : this.allFiles;

    this.selectedProfileFiles = this.selectedProfileFiles.filter(name => !visibleFiles.some(f => f.name === name));
    this.renderProfileFiles(filter);
  }


  saveProfiles() {
    const profileNameInput = document.getElementById("profile-name");
    const fileList = document.getElementById("files-profile-list");

    try {
      if (!this.selectedProfileFiles || this.selectedProfileFiles.length === 0) {
        if (fileList) fileList.scrollIntoView({ behavior: "smooth", block: "center" });
        return Utils.showSnackbar(window.languageService.t("noFilesSelected"), "error");
      }

      const profileName = profileNameInput.value.trim();
      if (!profileName) {
        profileNameInput.focus();
        return Utils.showSnackbar(window.languageService.t("profileNameRequired"), "warning");
      }

      const exists = this.allProfiles.some(p => p.name.toLowerCase() === profileName.toLowerCase());
      if (exists) {
        profileNameInput.select();
        profileNameInput.focus();
        return Utils.showSnackbar(window.languageService.t("profileNameExists"), "error");
      }

      const newProfile = {
        name: profileName,
        files: [...this.selectedProfileFiles],
      };

      this.allProfiles.push(newProfile);
      localStorage.setItem("savedProfiles", JSON.stringify(this.allProfiles));
      this.updateProfileSelectOptions();

      Utils.showSnackbar(window.languageService.t("profileSaved"), "success");

      this.selectedProfileFiles = [];
      profileNameInput.value = "";
      this.hideProfileModal();
    } catch (err) {
      console.error("SaveProfiles Error:", err);
      Utils.showSnackbar(window.languageService.t("unknownError"), "error");
    }
  }











  setupProfileSelect() {
    const select = document.getElementById("file-profile-select");
    if (!select) return;

    // Dropdown seçeneklerini güncelle
    this.updateProfileSelectOptions();

    // Profil seçildiğinde
    select.addEventListener("change", () => {
      const selectedProfileName = select.value;
      if (!selectedProfileName) {
        this.selectedFiles = [];
      } else {
        const profile = this.allProfiles.find(p => p.name === selectedProfileName);
        if (profile) {
          this.selectedFiles = [...profile.files]; // profile’dan gelen dosyalar seçili olacak
        }
      }

      // File selection modal'ı güncelle
      this.renderFileSelectionList();
      this.updateFileSelectionButton();
    });
  }


  updateProfileSelectOptions() {
    const select = document.getElementById("file-profile-select");
    if (!select) return;

    // Önce tüm seçenekleri temizle
    select.innerHTML = `<option value="" data-i18n="selectProfile">Select Profile</option>`;

    this.allProfiles.forEach(profile => {
      const opt = document.createElement("option");
      opt.value = profile.name;
      opt.textContent = profile.name;
      select.appendChild(opt);
    });
  }



  clearProfileSearch() {
    const input = document.getElementById("file-profile-selection-search");
    if (input) input.value = "";
    this.renderProfileFiles();
    input?.focus();
  }

  // -------------------------------------------------



  async loadAndSelectAllFiles() {
    try {
      // Fetch files from API
      const result = await window.apiService.getFiles();

      if (result.success && result.files) {
        this.allFiles = result.files;
        // Only select all files on the very first initialization
        if (!this.hasInitializedFiles) {
          this.selectedFiles = this.allFiles.map((file) => file.name);
          this.hasInitializedFiles = true; // Mark as initialized
          // Update button display
          this.updateFileSelectionButton();
        }
      }
    } catch (error) {
      console.error("Error loading files for selection:", error);
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

    // Drag and drop for entire chat container
    const chatContainer = document.querySelector(".chat-container");
    if (chatContainer) {
      chatContainer.addEventListener("dragover", (e) =>
        this.handleChatAreaDragOver(e)
      );
      chatContainer.addEventListener("dragleave", (e) =>
        this.handleChatAreaDragLeave(e)
      );
      chatContainer.addEventListener("drop", (e) => this.handleChatAreaDrop(e));
      chatContainer.addEventListener("dragenter", (e) =>
        this.handleChatAreaDragEnter(e)
      );
    }

    // File attachment button (paperclip)
    // Dropdown açıp kapatma
    const fileAttachmentBtn = document.getElementById("file-attachment-btn");
    const dropdown = document.getElementById("file-dropdown");

    fileAttachmentBtn.addEventListener("click", (e) => {
      e.stopPropagation(); // dışarı taşmasın
      dropdown.style.display =
        dropdown.style.display === "block" ? "none" : "block";
    });

    // Menü dışına tıklayınca kapansın
    document.addEventListener("click", () => {
      dropdown.style.display = "none";
    });

    // Normal attach seçeneği
    const normalAttachBtn = document.getElementById("normal-file");

    normalAttachBtn.addEventListener("click", () => {
      chatFileInput?.click();  // ❗ ESKİ davranış buraya taşındı
      dropdown.style.display = "none";
    });

    // Photo-less mode seçeneği
    const photoLessBtn = document.getElementById("photoless-mode");

    photoLessBtn.addEventListener("click", () => {
      // Language
      const lang = window.languageService?.getCurrentLanguage() || "tr";

      // Photoless mod durumunu global bir değişkene kaydedelim
      window.isPhotoLessMode = true;

      let msg = lang === "en"
        ? "Files will be processed without photos."
        : "Dosya fotoğrafları kullanılmadan işlenecektir.";

      Utils.showSnackbar(msg, "info", 4000);

      // Dosya seçimi aç
      const chatFileInput = document.getElementById("chat-file-input");
      chatFileInput?.click();

      // Dropdown kapat
      dropdown.style.display = "none";
    });



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

    // Event delegation for dynamic buttons and universal link interceptor
    document.addEventListener("click", (e) => {
      // Universal link interceptor - catch ALL links and open externally
      if (e.target.tagName === "A" || e.target.closest("a")) {
        const link =
          e.target.tagName === "A" ? e.target : e.target.closest("a");

        // Only intercept links with href attributes
        if (link.href) {
          // Do NOT intercept application-generated download links or blob URLs
          // - Anchors with download attribute should be allowed to proceed
          // - blob: URLs are handled by the browser/Electron automatically
          const hasDownloadAttr = link.hasAttribute("download");
          const isBlobUrl = link.href.startsWith("blob:");
          if (hasDownloadAttr || isBlobUrl) {
            return; // allow default behavior
          }

          e.preventDefault();
          e.stopPropagation();

          console.log(`🔗 Intercepted link: ${link.href}`);

          // Check if this is a news source link
          const isNewsSourceLink = link.classList.contains("news-source-link");
          if (isNewsSourceLink) {
            const sourceName = link.dataset.sourceName || "news source";
            console.log(`📰 Opening news source: ${sourceName}`);
          }

          // Special handling for download links
          if (
            link.href.includes("/api/created-documents/") ||
            link.href.includes("/api/files/")
          ) {
            const t = window.languageService
              ? window.languageService.t.bind(window.languageService)
              : (key) => key;

            let filename = "";
            try {
              const urlParts = link.href.split("/");
              if (link.href.includes("/api/created-documents/")) {
                filename = decodeURIComponent(
                  urlParts[urlParts.indexOf("created-documents") + 1]
                );
              } else if (link.href.includes("/api/files/")) {
                filename = decodeURIComponent(
                  urlParts[urlParts.indexOf("files") + 1]
                );
              }
            } catch (err) {
              console.warn("Could not extract filename from URL:", link.href);
            }

            if (filename) {
              this.showNotification(
                `${t("downloadingFile")} ${filename}...`,
                "info"
              );
            }
          }

          // Use Electron API if available, otherwise fallback to window.open
          if (window.airisAPI && window.airisAPI.openExternalUrl) {
            window.airisAPI
              .openExternalUrl(link.href)
              .then((result) => {
                if (result.success) {
                  console.log(
                    `✅ Successfully opened link externally: ${link.href}`
                  );
                } else {
                  console.warn(
                    "Failed to open link via Electron API:",
                    result.error
                  );
                  // Fallback to window.open
                  window.open(link.href, "_blank", "noopener,noreferrer");
                }
              })
              .catch((error) => {
                console.error("Error using Electron API:", error);
                // Fallback to window.open
                window.open(link.href, "_blank", "noopener,noreferrer");
              });
          } else {
            // Fallback for non-Electron environments
            console.log(`🌐 Opening link with window.open: ${link.href}`);
            window.open(link.href, "_blank", "noopener,noreferrer");
          }

          return;
        }
      }

      if (e.target.classList.contains("cta-button") && e.target.dataset.tab) {
        this.switchTab(e.target.dataset.tab);
      }

      // Handle news item clicks (hero variants and regular items)
      const newsItem = e.target.closest(
        ".news-item, .news-hero, .news-hero-left, .news-hero-right"
      );
      if (newsItem && newsItem.dataset.articleIndex !== undefined) {
        const articleIndex = parseInt(newsItem.dataset.articleIndex);
        this.showNewsDetail(articleIndex);
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

      // News article clicks are now handled above with hero support

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
          this.selectedFiles.length > 0 ? this.selectedFiles : null
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

      // Debug: Log the original content
      console.log("Original content:", processedContent);

      // Process mathematical expressions first, before markdown parsing
      processedContent = Utils.processMathExpressions(processedContent);

      // Debug: Log content after math processing
      console.log("After math processing:", processedContent);

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

      // Debug: Log final parsed content
      console.log("Final parsed content:", parsedContent);

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
            `Type: ${chart.chart_type.charAt(0).toUpperCase() +
            chart.chart_type.slice(1)
            }`
          );
        }
        if (chart.period) {
          chartInfo.push(
            `Period: ${chart.period.charAt(0).toUpperCase() + chart.period.slice(1)
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
        `Adding ${(images || []).length} images and ${(generatedFiles || []).length
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
        <span style="font-size: 1em; opacity: 0.9;">${(images || []).length + (generatedFiles || []).length
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
        // Chat loaded successfully - no notification needed
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

        // Chat session deleted successfully - no notification needed
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
      // New chat started - no notification needed
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
          <button class="chat-session-delete" data-session-id="${session.session_id
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
    const addedCount = this.addFilesToChat(files);

    // Files added to chat - no notification needed for drag & drop
  }

  handleChatFileSelect(e) {
    const files = Array.from(e.target.files);
    this.addFilesToChat(files, true); // Show notification for manual file selection
    e.target.value = ""; // Clear input
  }

  addFilesToChat(files, showNotification = false) {
    if (!this.chatUploadedFiles) {
      this.chatUploadedFiles = [];
    }

    const validFiles = files.filter((file) => Utils.validateFile(file));

    validFiles.forEach((file) => {
      // Check if file already exists
      if (!this.chatUploadedFiles.find((f) => f.name === file.name)) {
        this.chatUploadedFiles.push(file);
      }
    });

    this.updateChatFilesPreview();

    // Only show notification for manual file selection (not drag & drop)
    if (showNotification && validFiles.length > 0) {
      // Show minimal feedback for manual file selection
      console.log(`${validFiles.length} file(s) attached to chat`);
    }

    return validFiles.length;
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
    this.addFilesToChat(files, true); // Show notification for manual file selection
  }

  handleChatInputDragOver(event) {
    event.preventDefault();
    event.stopPropagation();

    // Set dropEffect to indicate files can be dropped
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "copy";
    }

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

    // Handle files if any
    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      const files = Array.from(event.dataTransfer.files);
      const addedCount = this.addFilesToChat(files);

      // Files added to chat - no notification needed for drag & drop
    }
  }

  // Chat area drag and drop handlers (for entire chat container)
  handleChatAreaDragEnter(event) {
    event.preventDefault();
    event.stopPropagation();

    // Show drag overlay immediately when entering
    this.showChatDragOverlay();
  }

  handleChatAreaDragOver(event) {
    event.preventDefault();
    event.stopPropagation();

    // Set dropEffect to indicate files can be dropped
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "copy";
    }

    // Show drag overlay (in case dragenter was missed)
    this.showChatDragOverlay();
  }

  handleChatAreaDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();

    // Only hide if leaving the chat container entirely
    const chatContainer = document.querySelector(".chat-container");
    if (!chatContainer.contains(event.relatedTarget)) {
      this.hideChatDragOverlay();
    }
  }

  handleChatAreaDrop(event) {
    event.preventDefault();
    event.stopPropagation();

    // Hide drag overlay
    this.hideChatDragOverlay();

    // Handle files if any
    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      const files = Array.from(event.dataTransfer.files);
      const addedCount = this.addFilesToChat(files);

      // Files added to chat - no notification needed for drag & drop
    }
  }

  // Chat drag overlay management
  showChatDragOverlay() {
    let overlay = document.getElementById("chat-drag-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "chat-drag-overlay";
      overlay.className = "chat-drag-overlay";
      overlay.innerHTML = `
        <div class="drag-overlay-content">
          <div class="drag-overlay-icon">
            <i class="fas fa-cloud-upload-alt"></i>
          </div>
          <div class="drag-overlay-text">
            <h3 data-i18n="dropFilesToChat">Drop files to chat</h3>
            <p data-i18n="dropFilesDescription">Drop your files here to add them to the conversation</p>
          </div>
        </div>
      `;

      const chatContainer = document.querySelector(".chat-container");
      if (chatContainer) {
        chatContainer.appendChild(overlay);

        // Update translations for the newly added overlay
        if (window.languageService) {
          window.languageService.updatePageTexts();
        }
      }
    }
    overlay.classList.add("visible");
  }

  hideChatDragOverlay() {
    const overlay = document.getElementById("chat-drag-overlay");
    if (overlay) {
      overlay.classList.remove("visible");
      // Remove after animation
      setTimeout(() => {
        if (overlay.parentNode) {
          overlay.remove();
        }
      }, 300);
    }
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
        statusText = `Uploaded`;
        statusClass = "success";
        break;
      case "error":
        statusText = errorMessage || "Upload failed";
        statusClass = "error";
        break;
    }

    const messageElement = document.createElement("div");
    messageElement.className = `file-status-message ${statusClass}`;
    messageElement.innerHTML = `
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
        statusText = `Uploaded`;
        statusClass = "success";
        break;
      case "error":
        statusText = errorMessage || "Upload failed";
        statusClass = "error";
        break;
    }

    // Update the message
    statusMessage.className = `file-status-message ${statusClass}`;
    statusMessage.innerHTML = `
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
      const response = await fetch("http://localhost:8001/api/files");
      if (!response.ok) throw new Error("Failed to fetch file list");
      const data = await response.json();
      this.allFiles = data.files || [];

      // İlk listeleme
      this.displayFilteredFiles();

      // 🔍 Arama olayları
      const searchInput = document.getElementById("file-tab-search");
      const clearBtn = document.getElementById("file-tab-search-clear");

      if (searchInput) {
        searchInput.addEventListener("input", () => {
          this.displayFilteredFiles(searchInput.value.trim().toLowerCase());
        });
      }

      if (clearBtn) {
        clearBtn.addEventListener("click", () => {
          searchInput.value = "";
          this.displayFilteredFiles();
        });
      }
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

  displayFilteredFiles(searchTerm = "") {
    const fileLibrary = document.getElementById("files-grid");
    if (!fileLibrary) return;
    fileLibrary.innerHTML = "";

    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    const filteredFiles = this.allFiles.filter((f) =>
      f.name.toLowerCase().includes(searchTerm)
    );

    if (filteredFiles.length === 0) {
      fileLibrary.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-folder-open"></i>
        <h3>${t("noDocuments")}</h3>
        <p>${t("uploadToGetStarted")}</p>
      </div>`;
      return;
    }

    filteredFiles.forEach((file) => {
      const safeName = Utils.escapeHtml(file.name);
      const previewId = `preview-${safeName.replace(/[^a-zA-Z0-9]/g, "_")}`;

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
            <div class="file-card-name">${safeName}</div>
            <div class="file-card-details">${Utils.formatFileSize(
        file.size
      )} • ${Utils.formatDate(file.created_at)}</div>
          </div>
        </div>
        <div class="file-card-actions">
          <button class="file-action-btn delete-btn" data-filename="${safeName}" title="Delete file">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
      <div class="file-card-preview" id="${previewId}">
        <div class="preview-loading">
          <i class="fas fa-spinner fa-spin"></i>
          <span data-i18n="previewLoading">Loading preview...</span>
        </div>
      </div>
    `;

      // 📂 Dosyaya tıklayınca aç
      fileItem.addEventListener("click", (e) => {
        if (
          !e.target.closest(".file-card-actions") &&
          !e.target.closest(".file-card-preview")
        ) {
          this.openFile(file.name);
        }
      });

      fileLibrary.appendChild(fileItem);

      // ✅ Önizlemeyi yükle
      this.loadFilePreview(file.name);
    });
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
          // File opened successfully - no notification needed
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

        // Use consistent external opening logic
        if (window.airisAPI && window.airisAPI.openExternalUrl) {
          window.airisAPI.openExternalUrl(downloadUrl).catch(() => {
            window.open(downloadUrl, "_blank", "noopener,noreferrer");
          });
        } else {
          window.open(downloadUrl, "_blank", "noopener,noreferrer");
        }

        // File download started - no notification needed
      } catch (downloadError) {
        console.error("Download failed:", downloadError);

        // Last resort: Try to get file info
        const response = await fetch(
          `http://localhost:8001/api/files/${encodeURIComponent(fileName)}`
        );
        if (response.ok) {
          const fileInfo = await response.json();
          // File info displayed - no notification needed
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
          // File opened successfully - no notification needed
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

        // Use consistent external opening logic
        if (window.airisAPI && window.airisAPI.openExternalUrl) {
          window.airisAPI.openExternalUrl(downloadUrl).catch(() => {
            window.open(downloadUrl, "_blank", "noopener,noreferrer");
          });
        } else {
          window.open(downloadUrl, "_blank", "noopener,noreferrer");
        }

        // File download started - no notification needed
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
          // File info displayed - no notification needed
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
      // File deletion in progress - no notification needed

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
        // File deleted successfully - no notification needed
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
      // File deletion in progress - no notification needed

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
        // Document deleted successfully - no notification needed
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
                <button class="action-btn" onclick="window.uiComponents.downloadFile('${file.id
      }')" title="${t("downloadFile")}">
                    <i class="fas fa-download"></i>
                </button>
                <button class="action-btn delete" onclick="window.uiComponents.deleteFile('${file.id
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
    // Settings saved successfully - no notification needed
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
            <i class="fas fa-${type === "success"
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

    // Create Perplexity-style alternating layout
    // Pattern: Hero Right -> 3 items -> Hero Left -> Hero Right -> 3 items -> ...
    let html = "";
    let articleIndex = 0;
    let isHeroRight = true; // Start with right

    while (articleIndex < articlesWithIndices.length) {
      // Add a hero item
      const heroArticle = articlesWithIndices[articleIndex];
      if (heroArticle) {
        const heroType = isHeroRight ? "right" : "left";
        html += this.createHeroNewsItem(heroArticle, heroType);
        articleIndex++;
        isHeroRight = !isHeroRight; // Alternate for next hero
      }

      // Add 3 secondary items if available
      const secondaryArticles = articlesWithIndices.slice(
        articleIndex,
        articleIndex + 3
      );
      if (secondaryArticles.length > 0) {
        const secondaryHtml = secondaryArticles
          .map((article) => this.createNewsItem(article))
          .join("");
        html += `<div class="news-secondary">${secondaryHtml}</div>`;
        articleIndex += secondaryArticles.length;
      }
    }

    newsGrid.innerHTML = html;
  }

  createHeroNewsItem(article, heroType = "right") {
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

    // Create image HTML for hero
    let imageHtml = "";
    let imageSrc = "";

    if (article.image_url) {
      imageSrc = article.image_url;
    } else if (
      article.available_images &&
      article.available_images.length > 0
    ) {
      imageSrc = article.available_images[0].url;
    }

    if (imageSrc) {
      imageHtml = `
        <div class="news-hero-image">
          <img src="${Utils.escapeHtml(imageSrc)}"
               alt="${Utils.escapeHtml(article.title)}"
               loading="lazy"
               onerror="this.style.display='none'"
          />
        </div>
      `;
    }

    const heroClass = `news-hero news-hero-${heroType}`;

    return `
      <div class="${heroClass}" data-article-index="${article.index || 0}">
        ${imageHtml}
        <div class="news-hero-content">
          <h2 class="news-hero-title">${Utils.escapeHtml(article.title)}</h2>
          <p class="news-hero-description">${this.cleanDescriptionForCard(
      article.summary || ""
    )}</p>
          <div class="news-hero-meta">
            <span class="news-hero-sources">
              <i class="fas fa-building"></i>
              ${Utils.escapeHtml(article.source)}
            </span>
            <span class="news-hero-time">${timeAgo}</span>
          </div>
        </div>
      </div>
    `;
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
        <div class="news-item-image">
          <img src="${Utils.escapeHtml(imageSrc)}"
               alt="${imageAlt}"
               loading="lazy"
               onerror="this.style.display='none'"
          />
        </div>
      `;
    }

    return `
      <div class="news-item" data-article-index="${article.index || 0}">
        ${imageHtml}
        <div class="news-content">
          <h3 class="news-title">${Utils.escapeHtml(article.title)}</h3>
          <p class="news-description">${this.cleanDescriptionForCard(
      article.summary || ""
    )}</p>
          <div class="news-meta">
            <span class="news-sources">
              <i class="fas fa-building"></i>
              ${Utils.escapeHtml(article.source)}
            </span>
            <span class="news-time">${timeAgo}</span>
          </div>
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
    const marketColumn = document.querySelector(".market-column");

    if (!newsGrid || !newsDetail) return;

    // Hide news grid and market column, show detail view
    newsGrid.style.display = "none";
    if (marketColumn) {
      marketColumn.style.display = "none";
    }
    newsDetail.style.display = "flex";

    // Scroll to top of the news tab container when showing news details
    const newsTab = document.getElementById("news-tab");
    if (newsTab) {
      newsTab.scrollTo({ top: 0, behavior: "instant" });
    }

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
    const stockDetail = document.getElementById("stock-detail");
    const marketColumn = document.querySelector(".market-column");

    if (!newsGrid || !newsDetail) return;

    // Check if we're in Q&A mode
    if (this.newsQAStarted && this.currentNewsArticle) {
      // If in Q&A mode, reset to original article view first, then hide detail
      this.resetNewsDetailToOriginal();
      // Continue to hide the detail view after reset
    }

    // Show news grid and market column, hide detail views
    newsDetail.style.display = "none";
    if (stockDetail) stockDetail.style.display = "none";
    newsGrid.style.display = "grid";
    if (marketColumn) {
      marketColumn.style.display = "block";
    }

    // Scroll to top of the news tab container when returning to news feed
    const newsTab = document.getElementById("news-tab");
    if (newsTab) {
      newsTab.scrollTo({ top: 0, behavior: "instant" });
    }

    // Note: No need to clean up source link listeners anymore
    // as they're handled by the universal link interceptor

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

  cleanDescriptionForCard(description) {
    if (!description) return "";

    // Remove template expressions like {{IMAGE_LEAD}}, {{IMAGE_MID_1}}, etc.
    let cleaned = description.replace(/\{\{[^}]+\}\}/g, "");

    // Convert markdown-style bold formatting (** or ****)
    cleaned = cleaned.replace(/\*{2,4}([^*]+)\*{2,4}/g, "<strong>$1</strong>");

    // Convert markdown-style italic formatting (single *)
    cleaned = cleaned.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Clean up extra whitespace and line breaks for card display
    cleaned = cleaned.replace(/\s+/g, " ").trim();

    return cleaned;
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

    // Note: Source links are now handled by the universal link interceptor

    // Note: Source link clicks are now handled by the universal link interceptor
    // No need for separate event handler as it causes duplicate opens
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

  // Map backend verification type keys to i18n keys
  getVerificationTypeI18nKey(type) {
    const mapping = {
      bank_statement: "bankStatement",
      tax_declaration: "taxDeclaration",
      // Keep others as-is
    };
    return mapping[type] || type;
  }

  updateVerificationTypeSelect(types) {
    const select = document.getElementById("verification-type");
    if (!select || !types) return;

    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    // Preserve current selection
    const previousValue = select.value;

    // Ensure Auto Detect option exists and is translated
    let autoOption = select.querySelector('option[value="auto"]');
    if (!autoOption) {
      autoOption = document.createElement("option");
      autoOption.value = "auto";
    }
    autoOption.setAttribute("data-i18n", "autoDetect");
    autoOption.textContent = t("autoDetect");

    // Clear and re-append auto option
    select.innerHTML = "";
    select.appendChild(autoOption);

    // Normalize types into a string array
    const typeList = Array.isArray(types) ? types : Object.keys(types);

    // Add options for each verification type using translations
    typeList.forEach((type) => {
      if (type === "auto") return;
      const i18nKey = this.getVerificationTypeI18nKey(type);
      const option = document.createElement("option");
      option.value = type;
      option.setAttribute("data-i18n", i18nKey);
      option.textContent = t(i18nKey) || type;
      select.appendChild(option);
    });

    // Restore previous selection if still available
    if (
      previousValue &&
      Array.from(select.options).some((o) => o.value === previousValue)
    ) {
      select.value = previousValue;
    }
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
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        uploadText.textContent = `${t("selected")}: ${file.name}`;
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
        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        verifyBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> <span>${t(
          "verifying"
        )}</span>`;
      }

      // Show progress indicator
      const t = window.languageService
        ? window.languageService.t.bind(window.languageService)
        : (key) => key;
      this.showVerificationProgress(t("startingVerification"));

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
          // Remove scrollIntoView to prevent content shifting
          // resultsContainer.scrollIntoView({ behavior: "smooth" });
        }

        const t = window.languageService
          ? window.languageService.t.bind(window.languageService)
          : (key) => key;
        // Verification completed successfully - no notification needed
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

    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    if (detectedType) {
      const docType = result.verification_type || "unknown";
      const i18nKey = this.getVerificationTypeI18nKey(docType);
      // Try to translate using mapped key, fall back to original key, then raw text
      const translatedType = t(i18nKey) || t(docType) || docType;
      detectedType.textContent = translatedType;
    }

    if (finalStatus) {
      finalStatus.textContent = result.status || t("unknown");
      finalStatus.className = `detail-value ${result.status}`;
    }

    if (fraudRisk) {
      const stages = result.stages || {};

      // Support multiple possible keys for fraud analysis stage (EN/TR)
      const fraudStage =
        stages.fraud_analysis ||
        stages["sahtekarlık analizi"] ||
        stages["sahtekarlik analizi"] ||
        stages["fraud analysis"] ||
        stages.fraud ||
        null;

      let fraudLevel = (fraudStage && fraudStage.risk_level) || "unknown";

      // Normalize to EN keys for class names; translate text for UI
      let normalized = String(fraudLevel).toLowerCase();
      if (normalized === "düşük") normalized = "low";
      if (normalized === "yüksek") normalized = "high";
      if (normalized === "orta") normalized = "medium";

      const translatedLevel = t(normalized) || fraudLevel;
      fraudRisk.textContent = translatedLevel;
      fraudRisk.className = `detail-value risk-${normalized}`;
    }
  }

  updateVerificationStages(stages) {
    const stagesGrid = document.getElementById("verification-stages-grid");
    if (!stagesGrid) return;

    stagesGrid.innerHTML = "";

    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    const stageNames = {
      quality_control: t("qualityControl"),
      classification: t("documentClassification"),
      text_extraction: t("textExtraction"),
      template_validation: t("templateValidation"),
      data_consistency: t("dataConsistency"),
      fraud_analysis: t("fraudAnalysis"),
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
    // console.log(stageName);
    // console.log(stageData.passed, stageData.valid, stageData.consistent, stageData.risk_level, stageData.failed, stageData.score, stageData.confidence, stageData.quality_score);
    if (
      stageData.passed ||
      stageData.valid ||
      stageData.consistent ||
      stageData.risk_level === "low" ||
      stageData.risk_level === "düşük"
    ) {
      stageStatus = "passed";
      statusIcon = "fas fa-check";
    } else if (
      stageData.failed ||
      stageData.risk_level === "high" ||
      stageData.risk_level === "yüksek"
    ) {
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
      : stageData.assessment ||
      stageData.reasoning ||
      (window.languageService
        ? window.languageService.t("noDetailsAvailable")
        : "No details available");

    const t = window.languageService
      ? window.languageService.t.bind(window.languageService)
      : (key) => key;

    card.innerHTML = `
      <div class="stage-header">
        <div class="stage-name">${stageName}</div>
        <div class="stage-status ${stageStatus}">
          <i class="${statusIcon}"></i>
        </div>
      </div>
      <div class="stage-details">${Utils.escapeHtml(details)}</div>
      <div class="stage-score">
        <span class="stage-score-label">${t("score")}</span>
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

    // Scroll back to top - removed to prevent content shifting
    // const verificationContainer = document.querySelector(
    //   ".verification-container"
    // );
    // if (verificationContainer) {
    //   verificationContainer.scrollIntoView({ behavior: "smooth" });
    // }
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
    // Report downloaded successfully - no notification needed
  }

  // Initialize verification when tab loads
  async loadVerificationTab() {
    if (!this.verificationInitialized) {
      this.setupVerificationEventListeners();
      await this.loadVerificationTypes();
      this.verificationInitialized = true;
    }
  }

  setupFileSearch() {
    const input = document.getElementById("file-selection-search");
    const clearBtn = document.getElementById("file-selection-search-clear");

    if (!input) return;

    input.addEventListener("input", (e) => {
      this.fileSelectionFilter = e.target.value.trim().toLowerCase();
      this.renderFileSelectionList();
    });

    input.addEventListener("keypress", (e) => {
      if (e.key === "Escape") this.clearFileSearch();
    });

    clearBtn?.addEventListener("click", () => this.clearFileSearch());
  }

  clearFileSearch() {
    const input = document.getElementById("file-selection-search");
    if (input) input.value = "";
    this.fileSelectionFilter = "";
    this.renderFileSelectionList();
    input?.focus();
  }

  // File Selection Modal Methods
  async showFileSelectionModal() {
    const modal = document.getElementById("file-selection-modal");
    if (!modal) return;

    this.fileSelectionModal = modal;

    // Load files if not already loaded
    await this.loadFilesForSelection();

    // Show modal
    modal.classList.add("show");

    // Update display
    this.updateFileSelectionDisplay();
  }

  hideFileSelectionModal() {
    const modal = document.getElementById("file-selection-modal");
    if (modal) modal.classList.remove("show");
    this.fileSelectionModal = null;
  }

  async loadFilesForSelection() {
    const filesList = document.getElementById("files-selection-list");
    if (!filesList) return;

    filesList.innerHTML = `
        <div class="loading-files">
            <i class="fas fa-spinner fa-spin"></i>
            <span>Loading files...</span>
        </div>`;

    try {
      const result = await window.apiService.getFiles();

      if (result.success && result.files) {
        this.allFiles = result.files;
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
            </div>`;
    }
  }

  renderFileSelectionList() {
    const filesList = document.getElementById("files-selection-list");
    if (!filesList || !this.allFiles) return;

    const q = this.fileSelectionFilter;

    let visibleFiles = q
      ? this.allFiles.filter(f => f.name.toLowerCase().includes(q))
      : this.allFiles;

    // Seçili dosyaları en üste taşı
    visibleFiles.sort((a, b) => {
      const aSelected = this.selectedFiles.includes(a.name);
      const bSelected = this.selectedFiles.includes(b.name);

      if (aSelected && !bSelected) return -1; // a seçiliyse b'nin üstüne al
      if (!aSelected && bSelected) return 1;  // b seçiliyse a'nın üstüne al
      return 0; // ikisi de aynı seçili durumdaysa sıralamayı bozma
    });



    filesList.innerHTML = visibleFiles.map(file => {
      const isSelected = this.selectedFiles.includes(file.name);
      const fileExtension = file.name.split(".").pop().toLowerCase();
      const fileIcon = this.getFileIcon(fileExtension);
      const fileSize = this.formatFileSize(file.size);

      return `
        <div class="file-selection-item ${isSelected ? "selected" : ""}" data-filename="${file.name}">
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
        </div>`;
    }).join("");

    // Click eventlerini bağla (item veya checkbox farketmez)
    const items = filesList.querySelectorAll(".file-selection-item");
    items.forEach(item => {
      const fileName = item.dataset.filename;
      const checkbox = item.querySelector(".file-checkbox");

      // Container click
      item.onclick = (e) => {
        e.stopPropagation(); // çakışmaları önle
        this.toggleFileSelection(fileName);
      };

      // Checkbox click
      checkbox.onclick = (e) => {
        e.stopPropagation(); // parent click ile çakışmayı önle
        this.toggleFileSelection(fileName);
      };
    });
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

    if (index > -1) this.selectedFiles.splice(index, 1);
    else this.selectedFiles.push(fileName);

    // Listeyi yeniden render et ve seçili dosyaları en üste taşı
    this.renderFileSelectionList();
    this.updateFileSelectionButton();
  }

  selectAllFiles() {
    const q = this.fileSelectionFilter;
    const visibleFiles = q
      ? this.allFiles.filter(f => f.name.toLowerCase().includes(q))
      : this.allFiles;

    const visibleNames = visibleFiles.map(f => f.name);

    const set = new Set(this.selectedFiles);
    visibleNames.forEach(n => set.add(n));
    this.selectedFiles = Array.from(set);

    this.updateFileSelectionDisplay();
    this.updateFileSelectionButton();
  }

  deselectAllFiles() {
    const q = this.fileSelectionFilter;
    const visibleFiles = q
      ? this.allFiles.filter(f => f.name.toLowerCase().includes(q))
      : this.allFiles;

    const visibleNames = visibleFiles.map(f => f.name);

    this.selectedFiles = this.selectedFiles.filter(n => !visibleNames.includes(n));

    this.updateFileSelectionDisplay();
    this.updateFileSelectionButton();
  }

  updateFileSelectionDisplay() {
    const fileItems = document.querySelectorAll(".file-selection-item");

    fileItems.forEach(item => {
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
      button.classList.remove("all-selected");
      button.removeAttribute("data-count");
      button.title = "Select files to include";
    } else if (selectedCount === totalCount) {
      button.classList.add("has-selection");
      button.classList.add("all-selected");
      button.setAttribute("data-count", totalCount);
      button.title = `All ${totalCount} files selected`;
    } else {
      button.classList.add("has-selection");
      button.classList.remove("all-selected");
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
        uploadStatus.textContent = `❌ ${errorMessage || window.languageService?.get("failed") || "Failed"
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

      // Calculation completed successfully - no notification needed
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

    // Process mathematical expressions first
    formatted = Utils.processMathExpressions(formatted);

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

  // Stock Detail functionality
  async showStockDetail(symbol) {
    const newsGrid = document.getElementById("news-grid");
    const stockDetail = document.getElementById("stock-detail");
    const marketColumn = document.querySelector(".market-column");

    if (!newsGrid || !stockDetail) return;

    // Track which stock is currently active to avoid race conditions
    this.currentStockSymbol = symbol;

    // Hide news grid and market column, show stock detail
    newsGrid.style.display = "none";
    if (marketColumn) {
      marketColumn.style.display = "none";
    }
    stockDetail.style.display = "flex";

    // Scroll to top of the news tab container when showing stock details
    const newsTab = document.getElementById("news-tab");
    if (newsTab) {
      newsTab.scrollTo({ top: 0, behavior: "instant" });
    }

    // Set up back button handler
    const backButton = document.getElementById("stock-detail-back");
    if (backButton) {
      backButton.onclick = () => this.hideStockDetail();
    }

    // Set up stock search functionality
    this.setupStockSearch();

    // Load stock data and populate the detail view using current interval
    const activeIntervalBtn = document.querySelector(".interval-btn.active");
    const interval = activeIntervalBtn
      ? activeIntervalBtn.dataset.interval
      : "1M";
    const limit = this.computeLimitFromInterval(interval);
    await this.loadStockDetailData(symbol, limit);

    // Bind once: interval buttons and mover tabs
    if (!this.intervalButtonsBound) {
      this.setupIntervalButtons();
      this.intervalButtonsBound = true;
    }
    if (!this.moverTabsBound) {
      this.setupMarketMoverTabs();
      this.moverTabsBound = true;
    }
  }

  hideStockDetail() {
    const newsGrid = document.getElementById("news-grid");
    const stockDetail = document.getElementById("stock-detail");
    const marketColumn = document.querySelector(".market-column");

    if (!newsGrid || !stockDetail) return;

    // Show news grid and market column, hide stock detail
    stockDetail.style.display = "none";
    newsGrid.style.display = "grid";
    if (marketColumn) {
      marketColumn.style.display = "block";
    }

    // Scroll to top of the news tab container when returning to news feed
    const newsTab = document.getElementById("news-tab");
    if (newsTab) {
      newsTab.scrollTo({ top: 0, behavior: "instant" });
    }
  }

  async loadStockDetailData(symbol, limit = 7) {
    // Skip duplicate requests for the same params
    if (
      this.isLoadingStockDetail &&
      this.lastStockSymbol === symbol &&
      this.lastStockLimit === limit
    ) {
      return;
    }
    this.isLoadingStockDetail = true;
    try {
      // Show loading state
      this.showStockLoadingState();

      // Get stock data from API
      const api = new APIService();
      const response = await api.getMarketEod(symbol, limit);

      if (
        response.data &&
        response.data.data &&
        response.data.data.length > 0
      ) {
        const stockData = response.data.data;
        await this.populateStockDetail(symbol, stockData);
      } else {
        this.showStockErrorState(symbol);
      }
      this.lastStockSymbol = symbol;
      this.lastStockLimit = limit;
    } catch (error) {
      console.error("Error loading stock detail:", error);
      this.showStockErrorState(symbol);
    } finally {
      this.isLoadingStockDetail = false;
    }
  }

  computeLimitFromInterval(interval) {
    const today = new Date();
    switch ((interval || "").toUpperCase()) {
      case "1M":
        return 30;
      case "6M":
        return 180;
      case "YTD": {
        const start = new Date(today.getFullYear(), 0, 1);
        const diffMs = today - start;
        return Math.max(1, Math.ceil(diffMs / (1000 * 60 * 60 * 24)) + 1);
      }
      case "1Y":
        return 365;
      case "MAX":
        return 10000;
      default:
        return 30;
    }
  }

  isIndexSymbol(symbol) {
    // Common index symbols and patterns
    const indexPatterns = [
      /^XU\d+/i, // Turkish indices (XU100, XU030, etc.)
      /^BIST\d+/i, // BIST indices
      /^\^/, // Yahoo Finance index format (^GSPC, ^DJI, etc.)
      /^SPX$/i, // S&P 500
      /^DJI$/i, // Dow Jones
      /^IXIC$/i, // NASDAQ
      /^RUT$/i, // Russell 2000
      /^VIX$/i, // Volatility Index
      /^FTSE/i, // FTSE indices
      /^DAX$/i, // DAX
      /^CAC$/i, // CAC 40
      /^NIKKEI/i, // Nikkei
      /INDEX$/i, // Generic index suffix
    ];

    // Check if symbol matches any index pattern
    return indexPatterns.some((pattern) => pattern.test(symbol));
  }

  showStockLoadingState() {
    const companyName = document.getElementById("stock-company-name");
    const symbol = document.getElementById("stock-symbol");
    const currentPrice = document.getElementById("stock-current-price");
    const priceChange = document.getElementById("stock-price-change");
    const priceTime = document.getElementById("stock-price-time");
    const chart = document.getElementById("stock-chart");

    if (companyName) companyName.textContent = "Loading...";
    if (symbol) symbol.textContent = "";
    if (currentPrice) currentPrice.textContent = "--";
    if (priceChange) priceChange.textContent = "";
    if (priceTime) priceTime.textContent = "";
    if (chart) {
      chart.innerHTML = `
        <div class="chart-loading">
          <div class="loading-spinner"></div>
          <p>Loading chart...</p>
        </div>
      `;
    }
  }

  showStockErrorState(symbol) {
    const companyName = document.getElementById("stock-company-name");
    const symbolEl = document.getElementById("stock-symbol");
    const currentPrice = document.getElementById("stock-current-price");
    const priceChange = document.getElementById("stock-price-change");
    const priceTime = document.getElementById("stock-price-time");
    const chart = document.getElementById("stock-chart");

    if (companyName) companyName.textContent = "Error loading data";
    if (symbolEl) symbolEl.textContent = symbol;
    if (currentPrice) currentPrice.textContent = "--";
    if (priceChange) priceChange.textContent = "";
    if (priceTime) priceTime.textContent = "";
    if (chart) {
      chart.innerHTML = `
        <div class="chart-loading">
          <p>Error loading chart data</p>
        </div>
      `;
    }
  }

  async populateStockDetail(symbol, stockData) {
    // Sort data by date (newest first)
    const sortedData = [...stockData].sort(
      (a, b) => new Date(b.date) - new Date(a.date)
    );
    const latest = sortedData[0];
    const earliest = sortedData[sortedData.length - 1];
    const previous = sortedData[1];

    // Calculate change from earliest to latest within interval
    const change = latest.close - (earliest ? earliest.close : latest.close);
    const changePercent =
      earliest && earliest.close ? (change / earliest.close) * 100 : 0;
    const isPositive = change >= 0;

    // Populate header information
    const companyName = document.getElementById("stock-company-name");
    const symbolEl = document.getElementById("stock-symbol");
    const currentPrice = document.getElementById("stock-current-price");
    const priceChange = document.getElementById("stock-price-change");
    const priceTime = document.getElementById("stock-price-time");

    if (companyName) companyName.textContent = this.getCompanyName(symbol);
    if (symbolEl) symbolEl.textContent = symbol;
    if (currentPrice)
      currentPrice.textContent = `₺${latest.close?.toLocaleString("tr-TR")}`;
    if (priceChange) {
      priceChange.textContent = `${isPositive ? "+" : ""}₺${change.toFixed(
        2
      )} (${isPositive ? "+" : ""}${changePercent.toFixed(2)}%)`;
      priceChange.className = `stock-price-change ${isPositive ? "positive" : "negative"
        }`;
    }
    if (priceTime) {
      const date = new Date(latest.date);
      const currentLanguage = window.languageService.getCurrentLanguage();

      let formattedDate;
      if (currentLanguage === "tr") {
        // Turkish locale
        formattedDate = date.toLocaleDateString("tr-TR", {
          month: "short",
          day: "numeric",
        });
      } else {
        // Default English locale
        formattedDate = date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
      }

      priceTime.textContent = `${window.languageService.get(
        "atClose"
      )}: ${formattedDate}`;
    }

    // Populate financial metrics
    this.populateFinancialMetrics(latest, previous);

    // Populate company details (only for individual stocks, not indices)
    const companyDetailsSection = document.querySelector(
      ".stock-company-details"
    );
    if (this.isIndexSymbol(symbol)) {
      // Hide company details section for indices
      if (companyDetailsSection) {
        companyDetailsSection.style.display = "none";
      }
    } else {
      // Show company details section for individual stocks
      if (companyDetailsSection) {
        companyDetailsSection.style.display = "block";
      }
      await this.populateCompanyDetails(symbol);
    }

    // Create and display chart
    this.createStockChart(sortedData);

    // Populate market movers once per session
    if (!this.marketMoversData) {
      await this.fetchAndRenderMarketMovers();
    }
  }

  getCompanyName(symbol) {
    const companyNames = {
      "TUPRS.IS": "Türkiye Petrol Rafinerileri A.Ş.",
      "AKBNK.IS": "Akbank T.A.Ş.",
      "GARAN.IS": "Garanti BBVA",
      "ISCTR.IS": "Türkiye İş Bankası A.Ş.",
      "THYAO.IS": "Türk Hava Yolları A.O.",
      "BIMAS.IS": "BİM Birleşik Mağazalar A.Ş.",
      "EREGL.IS": "Ereğli Demir ve Çelik Fabrikaları T.A.Ş.",
      "FROTO.IS": "Ford Otomotiv Sanayi A.Ş.",
      "KCHOL.IS": "Koç Holding A.Ş.",
      "SAHOL.IS": "Hacı Ömer Sabancı Holding A.Ş.",
      "XU030.IS": "BIST 30",
      "XU100.IS": "BIST 100",
    };
    return companyNames[symbol] || symbol;
  }

  populateFinancialMetrics(latest, previous) {
    const metricsContainer = document.getElementById("financial-metrics");
    if (!metricsContainer) return;

    const previousClose = previous.close ? previous.close.toFixed(2) : "--";
    const open = latest.open ? latest.open.toFixed(2) : "--";
    const dayRange = `${Math.min(latest.low, latest.high).toFixed(
      2
    )} - ${Math.max(latest.low, latest.high).toFixed(2)}`;
    const volume = latest.volume
      ? latest.volume.toLocaleString("tr-TR")
      : previous
        ? previous.volume.toLocaleString("tr-TR")
        : "--";

    metricsContainer.innerHTML = `
      <div class="financial-metric">
        <span class="financial-metric-label">${languageService.get(
      "prevClose"
    )}</span>
        <span class="financial-metric-value">₺${previousClose}</span>
      </div>
      <div class="financial-metric">
        <span class="financial-metric-label">${languageService.get(
      "open"
    )}</span>
        <span class="financial-metric-value">₺${open}</span>
      </div>
      <div class="financial-metric">
        <span class="financial-metric-label">${languageService.get(
      "dayRange"
    )}</span>
        <span class="financial-metric-value">₺${dayRange}</span>
      </div>
      <div class="financial-metric">
        <span class="financial-metric-label">${languageService.get(
      "volume"
    )}</span>
        <span class="financial-metric-value">${volume}</span>
      </div>
    `;
  }

  async populateCompanyDetails(symbol) {
    const detailsContainer = document.getElementById("company-details");
    if (!detailsContainer) return;

    // Don't fetch company details for indices
    if (this.isIndexSymbol(symbol)) {
      detailsContainer.innerHTML = `
        <div class="company-detail">
          <span class="company-detail-label">Index Information</span>
          <span class="company-detail-value">This is a market index, not an individual company.</span>
        </div>
      `;
      return;
    }

    // Show loading placeholder immediately
    detailsContainer.innerHTML = `
      <div class="company-detail"><span class="company-detail-label">${languageService.get(
      "fulltimeEmployees"
    )}</span><span class="company-detail-value">${languageService.get(
      "loading"
    )}</span></div>
      <div class="company-detail"><span class="company-detail-label">${languageService.get(
      "sector"
    )}</span><span class="company-detail-value">${languageService.get(
      "loading"
    )}</span></div>
      <div class="company-detail"><span class="company-detail-label">${languageService.get(
      "industry"
    )}</span><span class="company-detail-value">${languageService.get(
      "loading"
    )}</span></div>
      <div class="company-detail"><span class="company-detail-label">${languageService.get(
      "country"
    )}</span><span class="company-detail-value">TR</span></div>
      <div class="company-detail"><span class="company-detail-label">${languageService.get(
      "exchange"
    )}</span><span class="company-detail-value">${languageService.get(
      "istanbulStockExchange"
    )}</span></div>
      <div class="company-description"><p class="description-text">Fetching description…</p></div>
    `;

    // Debounce duplicate requests
    if (this.isLoadingCompanyInfo && this.lastCompanyInfoSymbol === symbol) {
      return;
    }
    this.isLoadingCompanyInfo = true;
    try {
      // Fetch company info from API
      const api = new APIService();
      const response = await api.getCompanyInfo(symbol);
      const companyData = response.data?.data || {};

      // Extract data with fallbacks, use Turkish versions if language is Turkish
      const currentLang = languageService.getCurrentLanguage();
      const fulltimeEmployees = companyData.fulltime_employees || "--";
      const sector =
        currentLang === "tr"
          ? companyData.sector_tr || companyData.sector || "--"
          : companyData.sector || "--";
      const industry =
        currentLang === "tr"
          ? companyData.industry_tr || companyData.industry || "--"
          : companyData.industry || "--";
      const description =
        currentLang === "tr"
          ? companyData.description_tr || companyData.description || ""
          : companyData.description || "";

      console.log(currentLang, sector, industry, description);
      // Create description HTML with read more using CSS clamp
      let descriptionHtml = "";
      if (description) {
        const isLong = description.length > 240;
        descriptionHtml = `
          <div class="company-description">
            <p class="description-text ${isLong ? "" : "expanded"
          }">${description}</p>
            ${isLong
            ? '<button class="read-more-btn" id="company-read-more">Read More</button>'
            : ""
          }
          </div>
        `;
      } else {
        descriptionHtml =
          '<div class="company-description"><p class="description-text expanded">No description available.</p></div>';
      }

      // If user navigated to another stock while waiting, abort update
      if (this.currentStockSymbol !== symbol) {
        return;
      }

      detailsContainer.innerHTML = `
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "fulltimeEmployees"
      )}</span>
          <span class="company-detail-value">${fulltimeEmployees}</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "sector"
      )}</span>
          <span class="company-detail-value">${sector}</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "industry"
      )}</span>
          <span class="company-detail-value">${industry}</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "country"
      )}</span>
          <span class="company-detail-value">TR</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "exchange"
      )}</span>
          <span class="company-detail-value">${languageService.get(
        "istanbulStockExchange"
      )}</span>
        </div>
        ${descriptionHtml}
      `;

      // Wire up Read More toggle without duplicating text
      const readMoreBtn = document.getElementById("company-read-more");
      if (readMoreBtn) {
        readMoreBtn.addEventListener("click", () => {
          const p = readMoreBtn.previousElementSibling;
          if (p && p.classList.contains("description-text")) {
            p.classList.add("expanded");
            readMoreBtn.remove();
          }
        });
      }
      this.lastCompanyInfoSymbol = symbol;
    } catch (error) {
      console.error("Error fetching company info:", error);
      // Fallback to default display
      detailsContainer.innerHTML = `
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "fulltimeEmployees"
      )}</span>
          <span class="company-detail-value">--</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "sector"
      )}</span>
          <span class="company-detail-value">--</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "industry"
      )}</span>
          <span class="company-detail-value">--</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "country"
      )}</span>
          <span class="company-detail-value">--</span>
        </div>
        <div class="company-detail">
          <span class="company-detail-label">${languageService.get(
        "exchange"
      )}</span>
          <span class="company-detail-value">--</span>
        </div>
        <div class="company-description">
          <p class="description-text">No description available.</p>
        </div>
      `;
    } finally {
      this.isLoadingCompanyInfo = false;
    }
  }

  createStockChart(data) {
    const chartContainer = document.getElementById("stock-chart");
    if (!chartContainer) return;

    // Create a simple line chart using SVG
    const width = 800;
    const height = 400;
    const padding = 60; // Increased padding for axis labels
    const bottomPadding = 80; // Extra padding for x-axis labels

    // Sort data by date (oldest first for chart)
    const sortedData = [...data].reverse();
    const prices = sortedData.map((d) => d.close);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;

    // Add some margin to price range for better visualization
    const priceMargin = priceRange * 0.05;
    const adjustedMinPrice = minPrice - priceMargin;
    const adjustedMaxPrice = maxPrice + priceMargin;
    const adjustedPriceRange = adjustedMaxPrice - adjustedMinPrice;

    // Create points for the line
    const chartWidth = width - 2 * padding;
    const chartHeight = height - padding - bottomPadding;

    const points = sortedData.map((d, i) => {
      const x = padding + (i / (sortedData.length - 1)) * chartWidth;
      const y =
        padding +
        ((adjustedMaxPrice - d.close) / adjustedPriceRange) * chartHeight;
      return { x, y, data: d };
    });

    // Generate axis labels
    const { xAxisLabels, yAxisLabels } = this.generateAxisLabels(
      sortedData,
      adjustedMinPrice,
      adjustedMaxPrice,
      chartWidth,
      chartHeight,
      padding,
      bottomPadding
    );

    // Create path data
    let pathData = `M ${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      pathData += ` L ${points[i].x},${points[i].y}`;
    }

    // Determine color based on trend
    const firstPrice = prices[0];
    const lastPrice = prices[prices.length - 1];
    const isPositive = lastPrice >= firstPrice;
    const color = isPositive ? "#10b981" : "#ef4444";

    chartContainer.innerHTML = `
      <div class="chart-tooltip" id="chart-tooltip">
        <div class="tooltip-price">--</div>
        <div class="tooltip-date">--</div>
      </div>
      <div class="chart-tooltip" id="range-tooltip">
        <div class="tooltip-price" id="range-price">--</div>
        <div class="tooltip-date" id="range-dates">--</div>
      </div>
      <svg id="stock-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="display: block; width: 100%; height: 100%;">
        <defs>
          <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style="stop-color:${color};stop-opacity:0.3" />
            <stop offset="100%" style="stop-color:${color};stop-opacity:0" />
          </linearGradient>
        </defs>
        
        <!-- Grid lines and axes -->
        <g class="chart-grid" stroke="#e5e7eb" stroke-width="0.5" opacity="0.6">
          ${yAxisLabels
        .map(
          (label) => `
            <line x1="${padding}" y1="${label.y}" x2="${padding + chartWidth
            }" y2="${label.y}" />
          `
        )
        .join("")}
          ${xAxisLabels
        .map(
          (label) => `
            <line x1="${label.x}" y1="${padding}" x2="${label.x}" y2="${padding + chartHeight
            }" />
          `
        )
        .join("")}
        </g>
        
        <!-- Y-axis labels (prices) -->
        <g class="y-axis-labels" font-family="system-ui, -apple-system, sans-serif" font-size="11" fill="#6b7280">
          ${yAxisLabels
        .map(
          (label) => `
            <text x="${padding - 8}" y="${label.y + 3}" text-anchor="end">${label.text
            }</text>
          `
        )
        .join("")}
        </g>
        
        <!-- X-axis labels (dates) -->
        <g class="x-axis-labels" font-family="system-ui, -apple-system, sans-serif" font-size="11" fill="#6b7280">
          ${xAxisLabels
        .map(
          (label) => `
            <text x="${label.x}" y="${padding + chartHeight + 20
            }" text-anchor="middle">${label.text}</text>
          `
        )
        .join("")}
        </g>
        
        <!-- Main chart area -->
        <g class="chart-area">
          <path d="${pathData}" stroke="${color}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="${pathData} L ${points[points.length - 1].x},${padding + chartHeight
      } L ${points[0].x},${padding + chartHeight} Z" fill="url(#chartGradient)"/>
        </g>
        
        <!-- Interactive elements -->
        <g id="hover-group">
          <line id="hover-line" x1="0" y1="${padding}" x2="0" y2="${padding + chartHeight
      }" stroke="#6b7280" stroke-opacity="0.9" stroke-width="1.5" stroke-dasharray="4,3" style="display:none" />
          <circle id="hover-dot" r="3" fill="${color}" stroke="#fff" stroke-width="1.5" style="display:none" />
        </g>
        <rect id="selection-rect" x="0" y="${padding}" width="0" height="${chartHeight}" fill="#3b82f6" opacity="0.15" style="display:none" />
        <rect id="hover-capture" x="${padding}" y="${padding}" width="${chartWidth}" height="${chartHeight}" fill="transparent" />
      </svg>
    `;

    // Interactivity: tooltip and crosshair
    const svg = chartContainer.querySelector("#stock-svg");
    const capture = chartContainer.querySelector("#hover-capture");
    const hoverLine = chartContainer.querySelector("#hover-line");
    const hoverDot = chartContainer.querySelector("#hover-dot");
    const tooltip = chartContainer.querySelector("#chart-tooltip");

    const bisect = (mouseX) => {
      // Convert mouseX to index by nearest point
      let nearestIndex = 0;
      let minDx = Infinity;
      for (let i = 0; i < points.length; i++) {
        const dx = Math.abs(points[i].x - mouseX);
        if (dx < minDx) {
          minDx = dx;
          nearestIndex = i;
        }
      }
      return nearestIndex;
    };

    const formatDate = (d) => {
      try {
        const dt = new Date(d.date || d.time || d.datetime || d.Date || d.DATE);
        return dt.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        });
      } catch {
        return "";
      }
    };

    const showAtIndex = (idx) => {
      const pt = points[idx];
      const d = sortedData[idx];
      hoverLine.setAttribute("x1", pt.x);
      hoverLine.setAttribute("x2", pt.x);
      hoverDot.setAttribute("cx", pt.x);
      hoverDot.setAttribute("cy", pt.y);
      hoverLine.style.display = "block";
      hoverDot.style.display = "block";
      tooltip.style.display = "block";
      const price = (d.close ?? d.Close ?? d.c)?.toLocaleString("tr-TR", {
        maximumFractionDigits: 2,
        minimumFractionDigits: 2,
      });
      tooltip.querySelector(".tooltip-price").textContent = `₺${price}`;
      tooltip.querySelector(".tooltip-date").textContent = formatDate(d);
      // Position tooltip relative to chart container
      const chartRect = chartContainer.getBoundingClientRect();
      const tx = (pt.x / width) * chartRect.width;
      const ty = (pt.y / height) * chartRect.height;
      tooltip.style.left = `${tx}px`;
      tooltip.style.top = `${ty}px`;
    };

    let isSelecting = false;
    let startIdx = null;
    const selectionRect = chartContainer.querySelector("#selection-rect");
    const rangeTooltip = chartContainer.querySelector("#range-tooltip");

    const updateRange = (i1, i2) => {
      const a = Math.min(i1, i2);
      const b = Math.max(i1, i2);
      const p1 = points[a];
      const p2 = points[b];
      selectionRect.setAttribute("x", p1.x);
      selectionRect.setAttribute("width", Math.max(1, p2.x - p1.x));
      selectionRect.style.display = "block";

      const d1 = sortedData[a];
      const d2 = sortedData[b];
      const change = d2.close - d1.close;
      const pct = d1.close ? (change / d1.close) * 100 : 0;
      const priceStr = `₺${change.toFixed(2)} (${pct >= 0 ? "+" : ""
        }${pct.toFixed(2)}%)`;
      rangeTooltip.querySelector("#range-price").textContent = priceStr;
      rangeTooltip.querySelector("#range-dates").textContent = `${formatDate(
        d1
      )} → ${formatDate(d2)}`;
      // Position tooltip near end point relative to chart container
      const chartRect = chartContainer.getBoundingClientRect();
      const tx = (p2.x / width) * chartRect.width;
      const ty = (p2.y / height) * chartRect.height;
      rangeTooltip.style.left = `${tx}px`;
      rangeTooltip.style.top = `${ty}px`;
      rangeTooltip.style.display = "block";
    };

    capture.addEventListener("mousemove", (e) => {
      const bbox = svg.getBoundingClientRect();
      const mouseX = ((e.clientX - bbox.left) / bbox.width) * width;
      const idx = bisect(mouseX);
      if (isSelecting && startIdx !== null) {
        updateRange(startIdx, idx);
      } else {
        showAtIndex(idx);
      }
    });

    capture.addEventListener("mouseleave", () => {
      hoverLine.style.display = "none";
      hoverDot.style.display = "none";
      tooltip.style.display = "none";
      if (!isSelecting) {
        selectionRect.style.display = "none";
        rangeTooltip.style.display = "none";
      }
    });

    capture.addEventListener("mousedown", (e) => {
      const bbox = svg.getBoundingClientRect();
      const mouseX = ((e.clientX - bbox.left) / bbox.width) * width;
      startIdx = bisect(mouseX);
      isSelecting = true;

      // Reset selection rectangle position before showing
      const startPoint = points[startIdx];
      selectionRect.setAttribute("x", startPoint.x);
      selectionRect.setAttribute("width", 0);
      selectionRect.style.display = "block";

      // Don't show range tooltip yet, wait for movement
      rangeTooltip.style.display = "none";
    });

    window.addEventListener("mouseup", () => {
      if (isSelecting) {
        isSelecting = false;
        // Hide selection when mouse is released
        selectionRect.style.display = "none";
        rangeTooltip.style.display = "none";
      }
    });
  }

  generateAxisLabels(
    sortedData,
    minPrice,
    maxPrice,
    chartWidth,
    chartHeight,
    padding,
    bottomPadding
  ) {
    const priceRange = maxPrice - minPrice;

    // Generate Y-axis labels (prices)
    const yAxisLabels = [];
    const numYTicks = 6;
    for (let i = 0; i <= numYTicks; i++) {
      const ratio = i / numYTicks;
      const price = maxPrice - ratio * priceRange;
      const y = padding + ratio * chartHeight;

      yAxisLabels.push({
        y: y,
        text: `₺${price.toFixed(2)}`,
        value: price,
      });
    }

    // Generate X-axis labels (dates)
    const xAxisLabels = [];
    const dataLength = sortedData.length;

    if (dataLength <= 2) {
      // If very few data points, show all
      sortedData.forEach((d, i) => {
        const x = padding + (i / (dataLength - 1)) * chartWidth;
        xAxisLabels.push({
          x: x,
          text: this.formatDateForAxis(d),
          data: d,
        });
      });
    } else {
      // Show smart intervals based on data length
      let numXTicks;
      if (dataLength <= 7) {
        numXTicks = dataLength;
      } else if (dataLength <= 30) {
        numXTicks = Math.min(6, Math.ceil(dataLength / 5));
      } else if (dataLength <= 90) {
        numXTicks = 6;
      } else {
        numXTicks = 8;
      }

      for (let i = 0; i < numXTicks; i++) {
        const dataIndex =
          i === numXTicks - 1
            ? dataLength - 1
            : Math.floor((i * (dataLength - 1)) / (numXTicks - 1));
        const x = padding + (dataIndex / (dataLength - 1)) * chartWidth;
        const d = sortedData[dataIndex];

        xAxisLabels.push({
          x: x,
          text: this.formatDateForAxis(d),
          data: d,
          index: dataIndex,
        });
      }
    }

    return { xAxisLabels, yAxisLabels };
  }

  formatDateForAxis(dataPoint) {
    try {
      const date = new Date(
        dataPoint.date ||
        dataPoint.time ||
        dataPoint.datetime ||
        dataPoint.Date ||
        dataPoint.DATE
      );

      // Format based on current language
      const currentLang = languageService.getCurrentLanguage();
      const locale = currentLang === "tr" ? "tr-TR" : "en-US";

      // Use shorter format for axis labels
      return date.toLocaleDateString(locale, {
        month: "short",
        day: "numeric",
      });
    } catch {
      return "--";
    }
  }

  async fetchAndRenderMarketMovers(limit = 30, chartNum = 8) {
    const moversContainer = document.getElementById("market-movers-content");
    if (!moversContainer) return;

    try {
      const symbols = [
        "AEFES.IS",
        "AKBNK.IS",
        "ASELS.IS",
        "ASTOR.IS",
        "BIMAS.IS",
        "CIMSA.IS",
        "EKGYO.IS",
        "ENKAI.IS",
        "EREGL.IS",
        "FROTO.IS",
        "GARAN.IS",
        "GUBRF.IS",
        "ISCTR.IS",
        "KCHOL.IS",
        "KOZAL.IS",
        "KRDMD.IS",
        "MGROS.IS",
        "PETKM.IS",
        "PGSUS.IS",
        "SAHOL.IS",
        "SASA.IS",
        "SISE.IS",
        "TAVHL.IS",
        "TCELL.IS",
        "THYAO.IS",
        "TOASO.IS",
        "TTKOM.IS",
        "TUPRS.IS",
        "ULKER.IS",
        "YKBNK.IS",
      ];

      const api = new APIService();
      const resp = await api.getGainersLosersActive(symbols, limit, chartNum);
      const data = resp.data?.data || { gainers: [], losers: [], active: [] };
      this.marketMoversData = data;

      // Default render gainers tab
      this.renderMarketMovers("gainers");
    } catch (err) {
      console.error("Failed to load market movers", err);
      moversContainer.innerHTML = `<div class="text-muted">Unable to load market movers.</div>`;
    }
  }

  renderMarketMovers(tab = "gainers") {
    const moversContainer = document.getElementById("market-movers-content");
    if (!moversContainer || !this.marketMoversData) return;

    const list = this.marketMoversData[tab] || [];
    moversContainer.innerHTML = list
      .map((item) => {
        const positive = item.change_percent >= 0;
        const formatted = `${positive ? "+" : ""}${item.change_percent.toFixed(
          2
        )}%`;
        return `
        <div class="mover-item" data-symbol="${item.symbol}">
          <span class="mover-symbol">${item.symbol}</span>
          <span class="mover-change ${positive ? "positive" : "negative"
          }">${formatted}</span>
        </div>
      `;
      })
      .join("");

    // Click to open stock detail
    moversContainer.onclick = (e) => {
      const row = e.target.closest(".mover-item");
      if (row && row.dataset.symbol) {
        this.showStockDetail(row.dataset.symbol);
      }
    };
  }

  setupIntervalButtons() {
    const intervalButtons = document.querySelectorAll(".interval-btn");
    intervalButtons.forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        intervalButtons.forEach((b) => b.classList.remove("active"));
        const target = e.currentTarget;
        target.classList.add("active");
        const interval = target.dataset.interval;
        const limit = this.computeLimitFromInterval(interval);
        if (this.currentStockSymbol) {
          await this.loadStockDetailData(this.currentStockSymbol, limit);
        }
      });
    });
  }

  setupMarketMoverTabs() {
    const moverTabs = document.querySelectorAll(".mover-tab");
    moverTabs.forEach((tab) => {
      tab.addEventListener("click", (e) => {
        moverTabs.forEach((t) => t.classList.remove("active"));
        const target = e.currentTarget;
        target.classList.add("active");
        const tabKey = target.dataset.tab || "gainers";
        this.renderMarketMovers(tabKey);
      });
    });
  }

  // Stock Search functionality
  setupStockSearch() {
    const searchInput = document.getElementById("stock-search-input");
    const searchDropdown = document.getElementById("stock-search-dropdown");

    if (!searchInput || !searchDropdown) return;

    // Avoid setting up multiple times
    if (searchInput.dataset.searchSetup) return;
    searchInput.dataset.searchSetup = "true";

    let searchTimeout;
    let highlightedIndex = -1;
    let searchResults = [];

    // Handle input changes
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.trim();

      // Clear previous timeout
      clearTimeout(searchTimeout);

      if (query.length < 1) {
        this.hideSearchDropdown();
        return;
      }

      // Debounce search requests
      searchTimeout = setTimeout(async () => {
        await this.performStockSearch(query);
      }, 300);
    });

    // Handle keyboard navigation
    searchInput.addEventListener("keydown", (e) => {
      const items = searchDropdown.querySelectorAll(".stock-search-item");

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
          this.updateSearchHighlight(items, highlightedIndex);
          break;

        case "ArrowUp":
          e.preventDefault();
          highlightedIndex = Math.max(highlightedIndex - 1, -1);
          this.updateSearchHighlight(items, highlightedIndex);
          break;

        case "Enter":
          e.preventDefault();
          if (highlightedIndex >= 0 && items[highlightedIndex]) {
            const symbol = items[highlightedIndex].dataset.symbol;
            this.selectStock(symbol);
          }
          break;

        case "Escape":
          this.hideSearchDropdown();
          searchInput.blur();
          break;
      }
    });

    // Handle clicks outside to close dropdown
    document.addEventListener("click", (e) => {
      if (
        !searchInput.contains(e.target) &&
        !searchDropdown.contains(e.target)
      ) {
        this.hideSearchDropdown();
      }
    });

    // Reset highlight index when dropdown content changes
    const observer = new MutationObserver(() => {
      highlightedIndex = -1;
    });
    observer.observe(searchDropdown, { childList: true });
  }

  async performStockSearch(query) {
    const searchDropdown = document.getElementById("stock-search-dropdown");
    if (!searchDropdown) return;

    try {
      // Show loading state
      searchDropdown.innerHTML = `
        <div class="stock-search-no-results">
          <i class="fas fa-spinner fa-spin"></i> ${languageService.get(
        "loading"
      )}
        </div>
      `;
      searchDropdown.classList.add("show");

      // Call the API
      const api = new APIService();
      const response = await api.searchSymbols(query);

      console.log("Search response:", response); // Debug log

      // The API method returns response.data directly, so the symbols are in response.symbols or response.data
      let symbols = null;
      if (response) {
        symbols = response.symbols || response.data || [];
      }

      if (symbols && symbols.length > 0) {
        this.renderSearchResults(symbols);
      } else {
        this.renderNoResults();
      }
    } catch (error) {
      console.error("Stock search error:", error);
      this.renderSearchError();
    }
  }

  renderSearchResults(symbols) {
    const searchDropdown = document.getElementById("stock-search-dropdown");
    if (!searchDropdown) return;

    const resultsHtml = symbols
      .map((symbol) => {
        // Handle both simple strings and objects
        const symbolCode = typeof symbol === "string" ? symbol : symbol.symbol;
        const displayName =
          typeof symbol === "object" && symbol.name ? symbol.name : symbolCode;

        return `
        <div class="stock-search-item" data-symbol="${symbolCode}">
          <div class="stock-search-item-symbol">${symbolCode}</div>
          <div class="stock-search-item-name">${displayName}</div>
        </div>
      `;
      })
      .join("");

    searchDropdown.innerHTML = resultsHtml;
    searchDropdown.classList.add("show");

    // Add click handlers
    searchDropdown.querySelectorAll(".stock-search-item").forEach((item) => {
      item.addEventListener("click", () => {
        const symbol = item.dataset.symbol;
        this.selectStock(symbol);
      });
    });
  }

  renderNoResults() {
    const searchDropdown = document.getElementById("stock-search-dropdown");
    if (!searchDropdown) return;

    searchDropdown.innerHTML = `
      <div class="stock-search-no-results">
        ${languageService.get("noResultsFound")}
      </div>
    `;
    searchDropdown.classList.add("show");
  }

  renderSearchError() {
    const searchDropdown = document.getElementById("stock-search-dropdown");
    if (!searchDropdown) return;

    searchDropdown.innerHTML = `
      <div class="stock-search-no-results">
        <i class="fas fa-exclamation-triangle"></i> ${languageService.get(
      "error"
    )}
      </div>
    `;
    searchDropdown.classList.add("show");
  }

  updateSearchHighlight(items, highlightedIndex) {
    items.forEach((item, index) => {
      if (index === highlightedIndex) {
        item.classList.add("highlighted");
      } else {
        item.classList.remove("highlighted");
      }
    });
  }

  hideSearchDropdown() {
    const searchDropdown = document.getElementById("stock-search-dropdown");
    if (searchDropdown) {
      searchDropdown.classList.remove("show");
    }
  }

  async selectStock(symbol) {
    const searchInput = document.getElementById("stock-search-input");

    // Update search input with selected symbol
    if (searchInput) {
      searchInput.value = symbol;
    }

    // Hide dropdown
    this.hideSearchDropdown();

    // Load the selected stock data
    if (symbol !== this.currentStockSymbol) {
      this.currentStockSymbol = symbol;

      // Load stock data with current interval
      const activeIntervalBtn = document.querySelector(".interval-btn.active");
      const interval = activeIntervalBtn
        ? activeIntervalBtn.dataset.interval
        : "1M";
      const limit = this.computeLimitFromInterval(interval);
      await this.loadStockDetailData(symbol, limit);
    }
  }
}

// Export for global access
window.UIComponents = UIComponents;

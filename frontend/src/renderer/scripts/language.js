// Language Service for AIris UI
class LanguageService {
  constructor() {
    this.currentLanguage = 'en';
    this.translations = {};
    this.observers = [];
    
    this.loadTranslations();
    this.loadSavedLanguage();
  }

  loadTranslations() {
    this.translations = {
      en: {
        // Header
        appTitle: 'AIris Desktop - AI-Powered Financial Document Processing',
        logoText: 'AIris',
        logoSubtitle: 'Financial AI',
        webSearch: 'Web Search',
        ragFusion: 'RAG Fusion',
        toggleTheme: 'Toggle theme',
        connecting: 'Connecting...',
        connected: 'Connected',
        disconnected: 'Disconnected',
        live: 'LIVE',
        loading: 'Loading...',

        // Navigation
        chat: 'Chat',
        uploadFiles: 'Upload Files',
        myFiles: 'My Files',
        createdDocuments: 'Created Documents',
        financeNews: 'Finance News',
        analytics: 'Analytics',
        settings: 'Settings',

        // Chat Section
        aiFinancialAssistant: 'AI Financial Assistant',
        askQuestions: 'Ask questions about your financial documents and get AI-powered insights',
        history: 'History',
        newChat: 'New Chat',
        chatHistory: 'Chat History',
        close: 'Close',
        loadingChatHistory: 'Loading chat history...',
        welcomeToAiris: 'Welcome to AIris!',
        welcomeMessage: "I'm your AI financial assistant. Upload some documents and start asking questions about your financial data.",
        suggestedQuestions: {
          latestReport: "What's in my latest report?",
          analyzeTrends: 'Analyze financial trends',
          expenseSummary: 'Summary of expenses'
        },
        chatPlaceholder: 'Ask a question about your financial documents...',

        // Upload Section
        uploadDocuments: 'Upload Documents',
        uploadForAnalysis: 'Upload financial documents for AI analysis',
        dragDropFiles: 'Drag & Drop Files Here',
        or: 'or',
        browseFiles: 'browse files',
        supportedFormats: 'Supported: PDF, DOCX, XLSX, Images',
        uploadFilesAction: 'Upload Files',

        // Files Section
        documentLibrary: 'Document Library',
        manageDocuments: 'Manage your uploaded financial documents',
        noDocuments: 'No documents yet',
        uploadToGetStarted: 'Upload some documents to get started',
        
        // Created Documents Section
        createdDocumentsLibrary: 'Created Documents Library',
        manageCreatedDocuments: 'View and manage AI-generated financial documents',
        noCreatedDocuments: 'No created documents yet',
        askAiToCreateDocuments: 'Ask the AI to create financial reports and documents',
        startChatBtn: 'Start Chat',
        uploadFilesBtn: 'Upload Files',
        deleteFile: 'Delete file',

        // Finance News Section
        financeNewsTitle: 'Finance News',
        latestFinancialNews: 'Latest financial news and market updates',
        refresh: 'Refresh',
        loadingNews: 'Loading latest finance news...',
        lastUpdated: 'Last updated',
        readMore: 'Read More',

        // Analytics Section
        systemAnalytics: 'System Analytics',
        monitorPerformance: 'Monitor system performance and usage statistics',
        apiRequests: 'API Requests',
        totalRequests: 'Total Requests',
        responseTime: 'Response Time',
        average: 'Average',
        documents: 'Documents',
        processed: 'Processed',
        systemHealth: 'System Health',
        status: 'Status',
        recentActivity: 'Recent Activity',
        loadingActivity: 'Loading activity...',
        noActivity: 'No recent activity',
        healthy: 'Healthy',
        offline: 'Offline',
        idle: 'Idle',

        // Settings Section
        settingsTitle: 'Settings',
        configureApp: 'Configure your AIris desktop application',
        backendConfiguration: 'Backend Configuration',
        apiBaseUrl: 'API Base URL',
        requestTimeout: 'Request Timeout (ms)',
        interfacePreferences: 'Interface Preferences',
        theme: 'Theme',
        language: 'Language',
        autoScrollChat: 'Auto-scroll chat',
        about: 'About',
        version: 'Version',
        platform: 'Platform',
        
        // Theme options
        auto: 'Auto',
        light: 'Light',
        dark: 'Dark',

        // Language options
        english: 'English',
        turkish: 'Türkçe',

        // Upload Progress
        preparing: 'Preparing...',
        preparingFile: 'Preparing file...',
        readingFile: 'Reading file...',
        uploading: 'Uploading...',
        processingWithAI: 'Processing with AI...',
        uploadComplete: 'Upload complete!',
        uploadFailed: 'Upload failed',
        retry: 'Retry',
        complete: 'Complete',
        error: 'Error',
        avgSpeed: 'Avg',
        completedIn: 'Completed in',
        errorOccurred: 'Error occurred',

        // File Previews
        previewLoading: 'Loading preview...',
        previewUnavailable: 'Preview unavailable',
        previewError: 'Preview error',
        previewNotAvailable: 'Preview not available',

        // Notifications
        fileUploadedSuccessfully: 'File uploaded successfully',
        fileDeletedSuccessfully: 'File deleted successfully',
        failedToDeleteFile: 'Failed to delete file',
        failedToUploadFile: 'Failed to upload file',
        connectionLost: 'Connection lost',
        connectionRestored: 'Connection restored',

        // Common
        yes: 'Yes',
        no: 'No',
        cancel: 'Cancel',
        confirm: 'Confirm',
        delete: 'Delete',
        save: 'Save',
        apply: 'Apply',
        reset: 'Reset',

        // File deletion confirmation
        deleteConfirmation: 'Are you sure you want to delete "{filename}"?\\n\\nThis will permanently remove the file and all its data from the vector store.',
        
        // File size units
        bytes: 'B',
        kilobytes: 'KB',
        megabytes: 'MB',
        gigabytes: 'GB',

        // Time units
        seconds: 's',
        minutes: 'm',
        hours: 'h',
        days: 'd',

        // Error messages
        networkError: 'Network error',
        serverError: 'Server error',
        unknownError: 'Unknown error',
        fileNotFound: 'File not found',
        accessDenied: 'Access denied',

        // Welcome and initialization messages
        welcomeAssistantMessage: "Hello! I'm your AI financial document assistant. Upload your documents and ask me questions about them.",
        
        // Settings messages
        settingsSavedSuccessfully: 'Settings saved successfully!',
        
        // News messages
        loadingLatestNews: 'Loading latest finance news...',
        failedToLoadNews: 'Failed to load news',
        unableToFetchNews: 'Unable to fetch finance news. Please try again.',
        lastUpdatedAt: 'Last updated:',
        failedToUpdate: 'Failed to update',
        
        // Analytics messages
        notAvailable: 'N/A',
        unknown: 'Unknown',
        
        // Time format
        minutesAgo: 'm ago',
        hoursAgo: 'h ago',
        daysAgo: 'd ago',
        
        // Action buttons
        retryAction: 'Retry',
        
        // File operations
        areYouSureDelete: 'Are you sure you want to delete this file?',
        
        // Chat messages
        sorryError: 'Sorry, I couldn\'t process your request:',
        apologizeResponse: 'I apologize, but I couldn\'t generate a proper response.',
        sorryEncounteredError: 'Sorry, I encountered an error processing your request. Please try again.',
        requestTookTooLong: 'The request took too long. The AI service might be busy. Please try again.',
        connectionErrorCheck: 'Connection error. Please check your internet connection and try again.',
        
        // File upload messages  
        downloadingFile: 'Downloading',
        openedFile: 'Opened',
        unableToOpenDirectly: 'Unable to open directly',
        failedToOpenFile: 'Failed to open. Please try again.',
        deletingFile: 'Deleting file...',
        
        // File library messages
        uploadedOn: 'Uploaded',
        downloadFile: 'Download file',
        deleteFile: 'Delete file',
        refresh: 'Refresh',
        
        // Error states
        errorLoadingFiles: 'Error loading files',
        failedToLoadFiles: 'Failed to load files. Please try again later.',

        // Document Verification Section
        documentVerification: 'Document Verification',
        documentVerificationTitle: 'Document Verification',
        verifyDocumentsDesc: 'Upload documents to verify their authenticity and detect potential fraud',
        verificationDragDrop: 'Drop Document to Verify',
        verificationSupportedFormats: 'Supported: PDF, JPG, PNG, TIFF, BMP',
        documentType: 'Document Type',
        autoDetect: 'Auto Detect',
        invoice: 'Invoice (Fatura)',
        receipt: 'Receipt (Fiş/Makbuz)',
        bankStatement: 'Bank Statement',
        payslip: 'Payslip (Maaş Bordrosu)',
        contract: 'Contract (Sözleşme)',
        taxDeclaration: 'Tax Declaration',
        other: 'Other',
        verifyDocument: 'Verify Document',
        verificationResults: 'Verification Results',
        confidence: 'Confidence',
        verificationStatus: 'Status',
        fraudRisk: 'Fraud Risk',
        verificationStages: 'Verification Stages',
        issuesFound: 'Issues Found',
        downloadReport: 'Download Report',
        verifyAnother: 'Verify Another Document',
        verificationCompleted: 'Verification completed successfully',
        verificationFailed: 'Document verification failed',
        pleaseSelectFile: 'Please select a file to verify',
        unsupportedFileType: 'Unsupported file type',
        noVerificationDataToDownload: 'No verification data available to download',
        reportDownloaded: 'Verification report downloaded successfully',
        wolframMathVerification: 'Wolfram Alpha Mathematical Verification',
        wolframMathVerificationDesc: 'Enable advanced mathematical verification for calculations, fraud detection, and currency validation',

        // File Selection
        selectFiles: 'Select Files',
        selectAll: 'Select All',
        deselectAll: 'Deselect All',
        writeReport: 'Write Report',
        analyzeData: 'Analyze Data',
        summarize: 'Summarize',
        loadingFiles: 'Loading files...',
        noFilesAvailable: 'No files available. Upload some files first.',
        filesSelected: 'files selected',
        allFilesSelected: 'All files selected'
      },

      tr: {
        // Header
        appTitle: 'AIris Masaüstü - AI Destekli Finansal Belge İşleme',
        logoText: 'AIris',
        logoSubtitle: 'Finansal AI',
        webSearch: 'Web Arama',
        wolframAlpha: 'Wolfram Alpha',
        ragFusion: 'RAG Fusion',
        toggleTheme: 'Tema değiştir',
        connecting: 'Bağlanıyor...',
        connected: 'Bağlandı',
        disconnected: 'Bağlantı kesildi',
        live: 'CANLI',
        loading: 'Yükleniyor...',

        // Navigation
        chat: 'Sohbet',
        uploadFiles: 'Dosya Yükle',
        myFiles: 'Dosyalarım',
        createdDocuments: 'Oluşturulan Belgeler',
        financeNews: 'Finans Haberleri',
        analytics: 'Analitik',
        settings: 'Ayarlar',

        // Chat Section
        aiFinancialAssistant: 'AI Finansal Asistan',
        askQuestions: 'Finansal belgeleriniz hakkında sorular sorun ve AI destekli öngörüler alın',
        history: 'Geçmiş',
        newChat: 'Yeni Sohbet',
        chatHistory: 'Sohbet Geçmişi',
        close: 'Kapat',
        loadingChatHistory: 'Sohbet geçmişi yükleniyor...',
        welcomeToAiris: 'AIris\'e Hoş Geldiniz!',
        welcomeMessage: 'Ben sizin AI finansal asistanınızım. Bazı belgeler yükleyin ve finansal verileriniz hakkında sorular sormaya başlayın.',
        suggestedQuestions: {
          latestReport: 'Son raporumda neler var?',
          analyzeTrends: 'Finansal trendleri analiz et',
          expenseSummary: 'Gider özeti'
        },
        chatPlaceholder: 'Finansal belgeleriniz hakkında bir soru sorun...',

        // Upload Section
        uploadDocuments: 'Belge Yükle',
        uploadForAnalysis: 'AI analizi için finansal belgeler yükleyin',
        dragDropFiles: 'Dosyaları Buraya Sürükleyip Bırakın',
        or: 'veya',
        browseFiles: 'dosyalara göz atın',
        supportedFormats: 'Desteklenen: PDF, DOCX, XLSX, Resimler',
        uploadFilesAction: 'Dosyaları Yükle',

        // Files Section
        documentLibrary: 'Belge Kütüphanesi',
        manageDocuments: 'Yüklediğiniz finansal belgeleri yönetin',
        noDocuments: 'Henüz belge yok',
        uploadToGetStarted: 'Başlamak için bazı belgeler yükleyin',
        
        // Created Documents Section  
        createdDocumentsLibrary: 'Oluşturulan Belgeler Kütüphanesi',
        manageCreatedDocuments: 'AI tarafından oluşturulan finansal belgeleri görüntüleyin ve yönetin',
        noCreatedDocuments: 'Henüz oluşturulan belge yok',
        askAiToCreateDocuments: 'AI\'dan finansal raporlar ve belgeler oluşturmasını isteyin',
        startChatBtn: 'Sohbeti Başlat',
        uploadFilesBtn: 'Dosya Yükle',
        deleteFile: 'Dosyayı sil',

        // Finance News Section
        financeNewsTitle: 'Finans Haberleri',
        latestFinancialNews: 'En son finansal haberler ve piyasa güncellemeleri',
        refresh: 'Yenile',
        loadingNews: 'En son finans haberleri yükleniyor...',
        lastUpdated: 'Son güncelleme',
        readMore: 'Devamını Oku',

        // Analytics Section
        systemAnalytics: 'Sistem Analitikleri',
        monitorPerformance: 'Sistem performansını ve kullanım istatistiklerini izleyin',
        apiRequests: 'API İstekleri',
        totalRequests: 'Toplam İstek',
        responseTime: 'Yanıt Süresi',
        average: 'Ortalama',
        documents: 'Belgeler',
        processed: 'İşlendi',
        systemHealth: 'Sistem Sağlığı',
        status: 'Durum',
        recentActivity: 'Son Aktiviteler',
        loadingActivity: 'Aktiviteler yükleniyor...',
        noActivity: 'Son aktivite yok',
        healthy: 'Sağlıklı',
        offline: 'Çevrimdışı',
        idle: 'Boşta',

        // Settings Section
        settingsTitle: 'Ayarlar',
        configureApp: 'AIris masaüstü uygulamanızı yapılandırın',
        backendConfiguration: 'Backend Yapılandırması',
        apiBaseUrl: 'API Temel URL',
        requestTimeout: 'İstek Zaman Aşımı (ms)',
        interfacePreferences: 'Arayüz Tercihleri',
        theme: 'Tema',
        language: 'Dil',
        autoScrollChat: 'Sohbeti otomatik kaydır',
        about: 'Hakkında',
        version: 'Sürüm',
        platform: 'Platform',
        
        // Theme options
        auto: 'Otomatik',
        light: 'Açık',
        dark: 'Koyu',

        // Language options
        english: 'English',
        turkish: 'Türkçe',

        // Upload Progress
        preparing: 'Hazırlanıyor...',
        preparingFile: 'Dosya hazırlanıyor...',
        readingFile: 'Dosya okunuyor...',
        uploading: 'Yükleniyor...',
        processingWithAI: 'AI ile işleniyor...',
        uploadComplete: 'Yükleme tamamlandı!',
        uploadFailed: 'Yükleme başarısız',
        retry: 'Tekrar Dene',
        complete: 'Tamamlandı',
        error: 'Hata',
        avgSpeed: 'Ort',
        completedIn: 'Tamamlandı',
        errorOccurred: 'Hata oluştu',

        // File Previews
        previewLoading: 'Önizleme yükleniyor...',
        previewUnavailable: 'Önizleme mevcut değil',
        previewError: 'Önizleme hatası',
        previewNotAvailable: 'Önizleme mevcut değil',

        // Notifications
        fileUploadedSuccessfully: 'Dosya başarıyla yüklendi',
        fileDeletedSuccessfully: 'Dosya başarıyla silindi',
        failedToDeleteFile: 'Dosya silinemedi',
        failedToUploadFile: 'Dosya yüklenemedi',
        connectionLost: 'Bağlantı kesildi',
        connectionRestored: 'Bağlantı geri yüklendi',

        // Common
        yes: 'Evet',
        no: 'Hayır',
        cancel: 'İptal',
        confirm: 'Onayla',
        delete: 'Sil',
        save: 'Kaydet',
        apply: 'Uygula',
        reset: 'Sıfırla',

        // File deletion confirmation
        deleteConfirmation: '"{filename}" dosyasını silmek istediğinizden emin misiniz?\\n\\nBu işlem dosyayı ve tüm verilerini vektör deposundan kalıcı olarak kaldıracaktır.',
        
        // File size units
        bytes: 'B',
        kilobytes: 'KB',
        megabytes: 'MB',
        gigabytes: 'GB',

        // Time units
        seconds: 's',
        minutes: 'd',
        hours: 's',
        days: 'g',

        // Error messages
        networkError: 'Ağ hatası',
        serverError: 'Sunucu hatası',
        unknownError: 'Bilinmeyen hata',
        fileNotFound: 'Dosya bulunamadı',
        accessDenied: 'Erişim reddedildi',

        // Welcome and initialization messages
        welcomeAssistantMessage: 'Merhaba! Ben sizin AI finansal belge asistanınızım. Belgelerinizi yükleyin ve onlar hakkında sorular sorun.',
        
        // Settings messages
        settingsSavedSuccessfully: 'Ayarlar başarıyla kaydedildi!',
        
        // News messages
        loadingLatestNews: 'En son finans haberleri yükleniyor...',
        failedToLoadNews: 'Haberler yüklenemedi',
        unableToFetchNews: 'Finans haberleri alınamadı. Lütfen tekrar deneyin.',
        lastUpdatedAt: 'Son güncelleme:',
        failedToUpdate: 'Güncelleme başarısız',
        
        // Analytics messages
        notAvailable: 'Yok',
        unknown: 'Bilinmeyen',
        
        // Time format
        minutesAgo: 'dk önce',
        hoursAgo: 'sa önce',
        daysAgo: 'gün önce',
        
        // Action buttons
        retryAction: 'Tekrar Dene',
        
        // File operations
        areYouSureDelete: 'Bu dosyayı silmek istediğinizden emin misiniz?',
        
        // Chat messages
        sorryError: 'Üzgünüm, isteğinizi işleyemedim:',
        apologizeResponse: 'Özür dilerim, uygun bir yanıt oluşturamadım.',
        sorryEncounteredError: 'Üzgünüm, isteğinizi işlerken bir hatayla karşılaştım. Lütfen tekrar deneyin.',
        requestTookTooLong: 'İstek çok uzun sürdü. AI servisi meşgul olabilir. Lütfen tekrar deneyin.',
        connectionErrorCheck: 'Bağlantı hatası. Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.',
        
        // File upload messages  
        downloadingFile: 'İndiriliyor',
        openedFile: 'Açıldı',
        unableToOpenDirectly: 'Doğrudan açılamıyor',
        failedToOpenFile: 'Açılamadı. Lütfen tekrar deneyin.',
        deletingFile: 'Dosya siliniyor...',
        
        // File library messages
        uploadedOn: 'Yüklenme',
        downloadFile: 'Dosyayı indir',
        deleteFile: 'Dosyayı sil',
        refresh: 'Yenile',
        
        // Error states
        errorLoadingFiles: 'Dosyalar yüklenirken hata',
        failedToLoadFiles: 'Dosyalar yüklenemedi. Lütfen daha sonra tekrar deneyin.',

        // Document Verification Section
        documentVerification: 'Belge Doğrulama',
        documentVerificationTitle: 'Belge Doğrulama',
        verifyDocumentsDesc: 'Belgelerin orijinalliğini doğrulamak ve potansiyel sahtekarlığı tespit etmek için yükleyin',
        verificationDragDrop: 'Doğrulanacak Belgeyi Bırakın',
        verificationSupportedFormats: 'Desteklenen: PDF, JPG, PNG, TIFF, BMP',
        documentType: 'Belge Türü',
        autoDetect: 'Otomatik Tespit',
        invoice: 'Fatura',
        receipt: 'Fiş/Makbuz',
        bankStatement: 'Banka Ekstresi',
        payslip: 'Maaş Bordrosu',
        contract: 'Sözleşme',
        taxDeclaration: 'Vergi Beyannamesi',
        other: 'Diğer',
        verifyDocument: 'Belgeyi Doğrula',
        verificationResults: 'Doğrulama Sonuçları',
        confidence: 'Güven',
        verificationStatus: 'Durum',
        fraudRisk: 'Sahtekarlık Riski',
        verificationStages: 'Doğrulama Aşamaları',
        issuesFound: 'Bulunan Sorunlar',
        downloadReport: 'Raporu İndir',
        verifyAnother: 'Başka Belge Doğrula',
        verificationCompleted: 'Doğrulama başarıyla tamamlandı',
        verificationFailed: 'Belge doğrulama başarısız oldu',
        pleaseSelectFile: 'Lütfen doğrulanacak bir dosya seçin',
        unsupportedFileType: 'Desteklenmeyen dosya türü',
        noVerificationDataToDownload: 'İndirilecek doğrulama verisi mevcut değil',
        reportDownloaded: 'Doğrulama raporu başarıyla indirildi',
        wolframMathVerification: 'Wolfram Alpha Matematiksel Doğrulama',
        wolframMathVerificationDesc: 'Hesaplamalar, sahtekarlık tespiti ve para birimi doğrulaması için gelişmiş matematiksel doğrulamayı etkinleştir',

        // File Selection
        selectFiles: 'Dosya Seç',
        selectAll: 'Tümünü Seç',
        deselectAll: 'Seçimi Kaldır',
        writeReport: 'Rapor Yaz',
        analyzeData: 'Veri Analizi',
        summarize: 'Özetle',
        loadingFiles: 'Dosyalar yükleniyor...',
        noFilesAvailable: 'Dosya mevcut değil. Önce bazı dosyalar yükleyin.',
        filesSelected: 'dosya seçildi',
        allFilesSelected: 'Tüm dosyalar seçildi'
      }
    };
  }

  loadSavedLanguage() {
    const saved = localStorage.getItem('airis-language');
    if (saved && this.translations[saved]) {
      this.currentLanguage = saved;
    } else {
      // Auto-detect browser language
      const browserLang = navigator.language || navigator.userLanguage;
      if (browserLang.startsWith('tr')) {
        this.currentLanguage = 'tr';
      }
    }
  }

  setLanguage(language) {
    if (!this.translations[language]) {
      console.warn(`Language '${language}' not supported`);
      return;
    }

    this.currentLanguage = language;
    localStorage.setItem('airis-language', language);
    
    // Update document language
    document.documentElement.lang = language;
    
    // Notify observers
    this.notifyObservers();
  }

  getCurrentLanguage() {
    return this.currentLanguage;
  }

  get(key, replacements = {}) {
    const keys = key.split('.');
    let value = this.translations[this.currentLanguage];
    
    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        value = undefined;
        break;
      }
    }

    // Fallback to English if translation not found
    if (value === undefined) {
      let fallback = this.translations.en;
      for (const k of keys) {
        if (fallback && typeof fallback === 'object') {
          fallback = fallback[k];
        } else {
          fallback = key; // Return key if no translation found
          break;
        }
      }
      value = fallback;
    }

    // Replace placeholders
    if (typeof value === 'string' && Object.keys(replacements).length > 0) {
      Object.keys(replacements).forEach(placeholder => {
        value = value.replace(new RegExp(`{${placeholder}}`, 'g'), replacements[placeholder]);
      });
    }

    return value || key;
  }

  // Convenience method for translations
  t(key, replacements = {}) {
    return this.get(key, replacements);
  }

  // Subscribe to language changes
  subscribe(callback) {
    this.observers.push(callback);
    return () => {
      this.observers = this.observers.filter(obs => obs !== callback);
    };
  }

  notifyObservers() {
    this.observers.forEach(callback => callback(this.currentLanguage));
  }

  // Get available languages
  getAvailableLanguages() {
    return Object.keys(this.translations).map(code => ({
      code,
      name: this.translations[code].language || code
    }));
  }

  // Update all text elements with data-i18n attribute
  updatePageTexts() {
    document.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      const text = this.get(key);
      
      if (element.tagName === 'INPUT' && (element.type === 'text' || element.type === 'search')) {
        element.placeholder = text;
      } else if (element.tagName === 'TEXTAREA') {
        element.placeholder = text;
      } else {
        element.textContent = text;
      }
    });

    // Update title
    document.title = this.get('appTitle');
  }
}

// Create global language service instance
window.languageService = new LanguageService();

// Auto-update texts when language changes
window.languageService.subscribe(() => {
  window.languageService.updatePageTexts();
}); 
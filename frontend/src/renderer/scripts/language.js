// Language Service for AIris UI
class LanguageService {
  constructor() {
    this.currentLanguage = "en";
    this.translations = {};
    this.observers = [];

    this.loadTranslations();
    this.loadSavedLanguage();
  }

  loadTranslations() {
    this.translations = {
      en: {
        // Header
        appTitle: "AIris Desktop - AI-Powered Financial Document Processing",
        logoText: "AIris",
        logoSubtitle: "Financial AI",
        webSearch: "Web Search",
        toggleWebSearch: "Toggle web search",
        ragFusion: "RAG Fusion",
        toggleTheme: "Toggle theme",
        connecting: "Connecting...",
        connected: "Connected",
        disconnected: "Disconnected",
        loading: "Loading...",

        // Navigation
        chat: "Chat",
        uploadFiles: "Upload Files",
        myFiles: "My Files",
        createdDocuments: "Created Documents",
        interestCalculator: "Calculations",
        financeNews: "Finance News",
        financialAnalysis: "Financial Analysis",
        balance: "Balance",
        currentStatus: "Current Status",
        sales: "Sales",
        purchase: "Purchase",
        cash: "Cash",
        settings: "Settings",

        // Chat Section
        aiFinancialAssistant: "AIris Financial Assistant",
        askQuestions:
          "Ask questions about your financial documents and get AI-powered insights",
        history: "History",
        newChat: "New Chat",
        chatHistory: "Chat History",
        close: "Close",
        loadingChatHistory: "Loading chat history...",
        welcomeToAiris: "Welcome to AIris!",
        welcomeMessage:
          "I'm your AIris financial assistant. Upload some documents and start asking questions about your financial data.",
        suggestedQuestions: {
          latestReport: "What's in my latest report?",
          analyzeTrends: "Analyze financial trends",
          expenseSummary: "Summary of expenses",
        },
        chatPlaceholder: "Ask a question about your financial documents...",

        // Upload Section
        uploadDocuments: "Upload Documents",
        uploadForAnalysis: "Upload financial documents for AI analysis",
        dragDropFiles: "Drag & Drop Files Here",
        dropFilesToChat: "Drop files to chat",
        dropFilesDescription:
          "Drop your files here to add them to the conversation",
        or: "or",
        browseFiles: "browse files",
        supportedFormats: "Supported: PDF, DOCX, XLSX, Images",
        uploadFilesAction: "Upload Files",
        normalFile: "Normal File Attach",
        photolessMode: "Photo-less Mode",

        // Files Section
        documentLibrary: "Document Library",
        manageDocuments: "Manage your uploaded financial documents",
        noDocuments: "No documents yet",
        uploadToGetStarted: "Upload some documents to get started",

        // Created Documents Section
        createdDocumentsLibrary: "Created Documents Library",
        manageCreatedDocuments:
          "View and manage AI-generated financial documents",
        noCreatedDocuments: "No created documents yet",
        askAiToCreateDocuments:
          "Ask the AI to create financial reports and documents",
        startChatBtn: "Start Chat",
        uploadFilesBtn: "Upload Files",
        deleteFile: "Delete file",

        // Finance News Section
        financeNewsTitle: "Finance News",
        latestFinancialNews: "Latest financial news and market updates",
        refresh: "Refresh News",
        loadingNews: "Loading latest finance news...",
        lastUpdated: "Last updated",
        readMore: "Read More",
        backToNews: "Back to News",
        goBack: "Go back",
        sourcesTitle: "Sources",
        noNewsAvailable: "No news available",
        fetchLatestNews: "Fetch Latest News",
        getLatestNews: "Get Latest News",
        manualUpdateInfo: "Click refresh to get latest news",
        marketOutlook: "Market Outlook",

        // News Chat Section
        askAboutNews: "Ask about this news",
        chatDescription:
          "Ask questions about this news article and get AI-powered insights",
        askQuestionPlaceholder: "Ask follow up about this news...",
        followUpQuestionPlaceholder: "Ask a follow-up question...",

        // Settings Section
        settingsTitle: "Settings",
        configureApp: "Configure your AIris desktop application",
        backendConfiguration: "Server Configuration",
        apiBaseUrl: "Server Address",
        requestTimeout: "Request Timeout (seconds)",
        interfacePreferences: "Interface Preferences",
        theme: "Theme",
        language: "Language",
        autoScrollChat: "Auto-scroll chat",
        about: "About",
        version: "Version",
        platform: "Platform",

        // Theme options
        auto: "Auto",
        light: "Light",
        dark: "Dark",

        // Language options
        english: "English",
        turkish: "Türkçe",

        // Upload Progress
        preparing: "Preparing...",
        preparingFile: "Preparing file...",
        readingFile: "Reading file...",
        uploading: "Uploading...",
        processingWithAI: "Processing document...",
        uploadComplete: "Upload complete!",
        uploadFailed: "Upload failed",
        retry: "Retry",
        complete: "Complete",
        error: "Error",
        avgSpeed: "Avg",
        completedIn: "Completed in",
        errorOccurred: "Error occurred",

        // File Previews
        previewLoading: "Loading preview...",
        previewUnavailable: "Preview unavailable",
        previewError: "Preview error",
        previewNotAvailable: "Preview not available",

        // Notifications
        fileUploadedSuccessfully: "File uploaded",
        fileDeletedSuccessfully: "File deleted",
        failedToDeleteFile: "Failed to delete file",
        failedToUploadFile: "Failed to upload file",
        connectionLost: "Connection lost",
        connectionRestored: "Connection restored",

        // Common
        yes: "Yes",
        no: "No",
        cancel: "Cancel",
        confirm: "Confirm",
        delete: "Delete",
        save: "Save",
        apply: "Apply",
        reset: "Reset",

        // File deletion confirmation
        deleteConfirmation:
          'Are you sure you want to delete "{filename}"?\\n\\nThis will permanently remove the file and all its data from the document archive.',

        // File size units
        bytes: "B",
        kilobytes: "KB",
        megabytes: "MB",
        gigabytes: "GB",

        // Time units
        seconds: "s",
        minutes: "m",
        hours: "h",
        days: "d",

        // Error messages
        networkError: "Network error",
        serverError: "Server error",
        unknownError: "Unknown error",
        fileNotFound: "File not found",
        accessDenied: "Access denied",

        // Welcome and initialization messages
        welcomeAssistantMessage:
          "Hello! I'm your AI financial document assistant. Upload your documents and ask me questions about them.",

        // Settings messages
        settingsSavedSuccessfully: "Settings saved!",

        // News messages
        loadingLatestNews: "Loading latest finance news...",
        failedToLoadNews: "Failed to load news",
        unableToFetchNews: "Unable to fetch finance news. Please try again.",
        lastUpdatedAt: "Last updated:",
        failedToUpdate: "Failed to update",

        // Interest Calculator
        calculateLoanPayments: "Calculate your loan payments and total costs",
        loanAmount: "Loan Amount",
        loanTerm: "Loan Term (Months)",
        interestRate: "Interest Rate (%)",
        calculate: "Calculate",
        reset: "Reset",
        calculationResults: "Calculation Results",
        monthlyPayment: "Monthly Payment",
        totalPayment: "Total Payment",
        totalInterest: "Total Interest",
        yearlyInterestCost: "Yearly Cost",
        invalidInputs: "Please enter valid values",

        // Analytics messages
        notAvailable: "N/A",
        unknown: "Unknown",

        // Time format
        minutesAgo: "m ago",
        hoursAgo: "h ago",
        daysAgo: "d ago",

        // Action buttons
        retryAction: "Retry",

        // File operations
        areYouSureDelete: "Are you sure you want to delete this file?",

        // Chat messages
        sorryError: "Sorry, I couldn't process your request:",
        apologizeResponse:
          "I apologize, but I couldn't generate a proper response.",
        sorryEncounteredError:
          "Sorry, I encountered an error processing your request. Please try again.",
        requestTookTooLong:
          "The request took too long. The AI service might be busy. Please try again.",
        connectionErrorCheck:
          "Connection error. Please check your internet connection and try again.",

        // File upload messages
        downloadingFile: "Downloading",
        openedFile: "Opened",
        unableToOpenDirectly: "Unable to open directly",
        failedToOpenFile: "Failed to open. Please try again.",
        deletingFile: "Deleting file...",

        // File library messages
        uploadedOn: "Uploaded",
        downloadFile: "Download file",
        deleteFile: "Delete file",
        refresh: "Refresh News",

        // Error states
        errorLoadingFiles: "Error loading files",
        failedToLoadFiles: "Failed to load files. Please try again later.",

        // Document Verification Section
        documentVerification: "Document Verification",
        documentVerificationTitle: "Document Verification",
        verifyDocumentsDesc:
          "Upload documents to verify their authenticity and detect potential fraud",
        verificationDragDrop: "Drop Document to Verify",
        verificationSupportedFormats: "Supported: PDF, JPG, PNG, TIFF, BMP",
        documentType: "Document Type",
        autoDetect: "Auto Detect",
        invoice: "Invoice",
        receipt: "Receipt",
        bankStatement: "Bank Statement",
        payslip: "Payslip",
        contract: "Contract",
        taxDeclaration: "Tax Declaration",
        other: "Other",
        verifyDocument: "Verify Document",
        verificationResults: "Verification Results",
        confidence: "Confidence",
        verificationStatus: "Status",
        fraudRisk: "Fraud Risk",
        verificationStages: "Verification Stages",
        issuesFound: "Issues Found",
        downloadReport: "Download Report",
        verifyAnother: "Verify Another Document",
        verificationCompleted: "Verification completed",
        verificationFailed: "Document verification failed",
        pleaseSelectFile: "Please select a file to verify",
        unsupportedFileType: "Unsupported file type",
        noVerificationDataToDownload:
          "No verification data available to download",
        reportDownloaded: "Verification report downloaded",
        wolframMathVerification: "Wolfram Alpha Mathematical Verification",
        wolframMathVerificationDesc:
          "Enable advanced mathematical verification for calculations, fraud detection, and currency validation",
        // Verification stage names
        qualityControl: "Quality Control",
        documentClassification: "Document Classification",
        textExtraction: "Text Extraction",
        templateValidation: "Template Validation",
        dataConsistency: "Data Consistency",
        fraudAnalysis: "Fraud Analysis",
        // Verification status values
        verified: "Verified",
        reviewRequired: "Review Required",
        rejected: "Rejected",
        passed: "Passed",
        failed: "Failed",
        warning: "Warning",
        // Additional verification terms
        score: "Score",
        noDetailsAvailable: "No details available",
        verifying: "Verifying...",
        startingVerification: "Starting verification...",
        selected: "Selected",
        // Risk levels
        low: "Low",
        medium: "Medium",
        high: "High",
        // Quality levels
        good: "Good",
        fair: "Fair",
        poor: "Poor",
        // Document types
        announcement: "Announcement",
        expense_voucher: "Expense Voucher",

        // Calculator Section
        loanCalculatorTitle: "Loan Calculator",
        loanCalculatorDescription: "Calculate your loan payments and total costs",
        calculateLoanPayments: "Calculate your loan payments and total costs",
        loanAmount: "Loan Amount",
        loanTerm: "Loan Term (Months)",
        interestRate: "Interest Rate (%) - Monthly Interest",
        calculate: "Calculate",
        reset: "Reset",
        calculationResults: "Calculation Results",
        monthlyPayment: "Monthly Payment",
        totalPayment: "Total Payment",
        totalInterest: "Total Interest",
        yearlyInterestCost: "Yearly Cost",
        enterValidValues: "Please enter valid values",
        enterPositiveValues: "Please enter positive values",
        depositCalculatorTitle: "Deposit Return",
        depositCalculatorDescription:
          "Estimate the interest earned on a fixed-term deposit.",
        depositPrincipal: "Principal Amount",
        depositDays: "Term (Days)",
        depositAnnualRate: "Annual Interest Rate (%)",
        depositResults: "Deposit Results",
        depositInterest: "Interest Earned",
        depositFinalAmount: "Final Amount",
        compoundDepositTitle: "Compound Deposit",
        compoundDepositDescription:
          "Calculate compound interest across different compounding frequencies.",
        compoundDepositPrincipal: "Principal Amount",
        compoundDepositAnnualRate: "Annual Interest Rate (%)",
        compoundDepositTerm: "Term (Number of Periods)",
        compoundDepositFrequency: "Compounding Frequency",
        compoundDepositFrequencyDaily: "Daily",
        compoundDepositFrequencyMonthly: "Monthly",
        compoundDepositFrequencyYearly: "Yearly",
        compoundDepositResults: "Compound Deposit Results",
        compoundDepositInterest: "Interest Earned",
        compoundDepositFinalAmount: "Final Amount",
        presentValueCalculatorTitle: "Present Value",
        presentValueCalculatorDescription:
          "Discount a future amount to today's value.",
        presentValueFutureAmount: "Future Value",
        presentValueAnnualRate: "Annual Interest Rate (%)",
        presentValueYears: "Years",
        presentValueMonths: "Months",
        presentValueDays: "Days",
        presentValueResults: "Present Value Results",
        presentValueValue: "Present Value",
        futureValueCalculatorTitle: "Future Value",
        futureValueCalculatorDescription:
          "Project a current amount into the future.",
        futureValuePresentAmount: "Present Value",
        futureValueAnnualRate: "Annual Interest Rate (%)",
        futureValueYears: "Years",
        futureValueMonths: "Months",
        futureValueDays: "Days",
        futureValueResults: "Future Value Results",
        futureValueValue: "Future Value",
        futureValueAnnuityCalculatorTitle: "Future Value of Annuity",
        futureValueAnnuityCalculatorDescription:
          "Project a series of equal payments into the future.",
        futureValueAnnuityPayment: "Periodic Payment",
        futureValueAnnuityAnnualRate: "Annual Interest Rate (%)",
        futureValueAnnuityYears: "Years",
        futureValueAnnuityMonths: "Months",
        futureValueAnnuityDays: "Days",
        futureValueAnnuityResults: "Future Value Results",
        futureValueAnnuityValue: "Future Value",
        presentValueAnnuityCalculatorTitle: "Present Value of Annuity",
        presentValueAnnuityCalculatorDescription:
          "Discount a series of equal payments to today's value.",
        presentValueAnnuityPayment: "Periodic Payment",
        presentValueAnnuityAnnualRate: "Annual Interest Rate (%)",
        presentValueAnnuityYears: "Years",
        presentValueAnnuityMonths: "Months",
        presentValueAnnuityDays: "Days",
        presentValueAnnuityResults: "Present Value Results",
        presentValueAnnuityValue: "Present Value",
        simpleDeposit: "Simple Interest",
        compoundDeposit: "Compound Interest",
        presentValue: "Present Value",
        futureValue: "Future Value",
        presentValueAnnuity: "Present Value",
        futureValueAnnuity: "Future Value",

        // File Selection
        selectFiles: "Select Files",
        selectAll: "Select All",
        deselectAll: "Deselect All",
        writeReport: "Write Report",
        analyzeData: "Analyze Data",
        summarize: "Summarize",
        loadingFiles: "Loading files...",
        noFilesAvailable: "No files available. Upload some files first.",
        filesSelected: "files selected",
        allFilesSelected: "All files selected",
        save: "Save",
        cancel: "Cancel",
        createNewProfile: "Create New Profile",
        selectProfile: "Select Profile",
        noFilesSelected: "Please select at least one file.",
        profileNameRequired: "Please enter a profile name.",
        profileNameExists: "A profile with this name already exists.",
        profileSaved: "Profile saved successfully!",
        unknownError: "An unexpected error occurred. Please try again.",

        // Currency labels
        gold: "Gold",
        goldUsdPerOz: "Gold (USD/oz)",
        goldTryPerGram: "Gold (₺/g)",
        usdTry: "USD/TRY",
        eurTry: "EUR/TRY",
        usdEur: "USD/EUR",

        // Status labels
        cached: "Cached",
        live: "Live",
        error: "Error",
        offline: "Offline",
        processing: "Processing...",
        unknown: "Unknown",
        failed: "Failed",

        // Balance Calendar
        balanceCalendar: {
          navLabel: "Balance Calendar",
          title: "Balance of Payments",
          subtitle:
            "Track daily cash positions derived from processed Excel workbooks.",
          timeframeLabel: "Timeframe",
          timeframes: {
            last1Month: "Last 1 month",
            last3Months: "Last 3 months",
            last6Months: "Last 6 months",
            last9Months: "Last 9 months",
            last12Months: "Last 12 months",
          },
          refresh: "Refresh",
          processTitle: "Process Balance Document",
          processDescription:
            "Upload a balance of payments document (Excel, PDF, image, etc.). The parser extracts the ledger and the agent will normalize transactions automatically.",
          uploadButton: "Upload & Process",
          uploadNote:
            "Uses parser.py to extract ledger details before running the agent.",
          runAgent: "Run Agent",
          loading: undefined,
          selectDayPrompt: "Select a day to view transaction details.",
          noDocuments: "No balance documents found",
          fetchDocumentsError: "Failed to load documents",
          retry: "Retry",
          summaryPeriodLabel: "Period",
          latestActivity: "Latest activity: {date}",
          noActivity: "No activity recorded yet",
          totalIncome: "Total Income",
          totalExpense: "Total Expense",
          netChange: "Net Change",
          weekdays: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          legendTitle: "Net balance intensity",
          incomeLabel: "Income",
          expenseLabel: "Expense",
          netLabel: "Net",
          tooltipNoTransactions: "No transactions",
          dayNoTransactions: "No transactions recorded for this day.",
          transactionsLoadError: "Unable to load transactions",
          calendarLoadError: "Unable to load calendar",
          calendarFetchError: "Unable to fetch calendar data",
          selectFilePrompt: "Please upload a balance document first.",
          runningAgent: "Running agent...",
          agentRunFailed: "Agent run failed",
          agentRequestFailed: "Failed to run the agent.",
          agentSuccess: "Agent completed successfully.",
          unsupportedFileType: "Unsupported file type for balance processing.",
          uploadingFile: "Uploading {filename}...",
          uploadSuccess: "Uploaded {filename}. Running agent...",
          uploadFailed: "Failed to upload balance document.",
          transactionSingular: "{count} transaction",
          transactionPlural: "{count} transactions",
          direction: {
            income: "Income",
            expense: "Expense",
          },
        },

        // Navigation
        goToChat: "Go to Chat",

        // Stock/Company Details
        exchange: "Exchange",
        istanbulStockExchange: "Istanbul Stock Exchange",
        fulltimeEmployees: "Fulltime Employees",
        sector: "Sector",
        industry: "Industry",
        country: "Country",
        loading: "Loading...",
        companyInfo: "Company Info",
        prevClose: "Prev Close",
        open: "Open",
        dayRange: "Day Range",
        volume: "Volume",
        searchStocks: "Search stocks...",
        noResultsFound: "No results found",
        searchForStocks: "Search for stocks",
        atClose: "At close",
        searchFiles: "Search files...",
        profileName: "Profile Name",
        enterProfileName: "Enter profile name",
      },

      tr: {
        // Header
        appTitle: "AIris Masaüstü - AI Destekli Finansal Belge İşleme",
        logoText: "AIris",
        logoSubtitle: "Finansal AI",
        webSearch: "Web Arama",
        toggleWebSearch: "Web aramayı aç/kapat",
        wolframAlpha: "Wolfram Alpha",
        ragFusion: "RAG Fusion",
        toggleTheme: "Tema değiştir",
        connecting: "Bağlanıyor...",
        connected: "Bağlandı",
        disconnected: "Bağlantı kesildi",
        loading: "Yükleniyor...",

        // Navigation
        chat: "Sohbet",
        uploadFiles: "Dosya Yükle",
        myFiles: "Dosyalarım",
        createdDocuments: "Oluşturulan Belgeler",
        interestCalculator: "Hesaplamalar",
        financeNews: "Finans Haberleri",
        financialAnalysis: "Finansal Analiz",
        balance: "Ödemeler Dengesi",
        currentStatus: "Güncel Durum",
        sales: "Satış",
        purchase: "Alış",
        cash: "Nakit",

        settings: "Ayarlar",

        // Calculator Section
        loanCalculatorTitle: "Kredi Hesaplayıcı",
        loanCalculatorDescription:
          "Kredi ödemelerinizi ve toplam maliyetinizi hesaplayın",
        calculateLoanPayments:
          "Kredi ödemelerinizi ve toplam maliyetleri hesaplayın",
        loanAmount: "Kredi Tutarı",
        loanTerm: "Kredi Vadesi (Ay)",
        interestRate: "Faiz Oranı (%) - Aylık Faiz",
        calculate: "Hesapla",
        reset: "Sıfırla",
        calculationResults: "Hesaplama Sonuçları",
        monthlyPayment: "Aylık Ödeme",
        totalPayment: "Toplam Ödeme",
        totalInterest: "Toplam Faiz",
        yearlyInterestCost: "Yıllık Maliyet",
        enterValidValues: "Lütfen geçerli değerler giriniz",
        enterPositiveValues: "Lütfen pozitif değerler giriniz",
        depositCalculatorTitle: "Mevduat Getirisi",
        depositCalculatorDescription:
          "Vadeli mevduatınızın getirisini hesaplayın.",
        depositPrincipal: "Anapara Tutarı",
        depositDays: "Vade (Gün)",
        depositAnnualRate: "Yıllık Faiz Oranı (%)",
        depositResults: "Mevduat Sonuçları",
        depositInterest: "Kazanç",
        depositFinalAmount: "Vade Sonu Tutarı",
        compoundDepositTitle: "Bileşik Mevduat",
        compoundDepositDescription:
          "Farklı bileşik dönemleri için getiriyi hesaplayın.",
        compoundDepositPrincipal: "Anapara Tutarı",
        compoundDepositAnnualRate: "Yıllık Faiz Oranı (%)",
        compoundDepositTerm: "Vade (Dönem Sayısı)",
        compoundDepositFrequency: "Bileşik Frekansı",
        compoundDepositFrequencyDaily: "Günlük",
        compoundDepositFrequencyMonthly: "Aylık",
        compoundDepositFrequencyYearly: "Yıllık",
        compoundDepositResults: "Bileşik Mevduat Sonuçları",
        compoundDepositInterest: "Kazanç",
        compoundDepositFinalAmount: "Vade Sonu Tutarı",
        presentValueCalculatorTitle: "Bugünkü Değer",
        presentValueCalculatorDescription:
          "Gelecekteki bir tutarı bugünkü değere indirgeyin.",
        presentValueFutureAmount: "Gelecekteki Tutar",
        presentValueAnnualRate: "Yıllık Faiz Oranı (%)",
        presentValueYears: "Yıl",
        presentValueMonths: "Ay",
        presentValueDays: "Gün",
        presentValueResults: "Bugünkü Değer Sonuçları",
        presentValueValue: "Bugünkü Değer",
        futureValueCalculatorTitle: "Gelecek Değer",
        futureValueCalculatorDescription:
          "Bugünkü bir tutarı geleceğe projeksiyon yapın.",
        futureValuePresentAmount: "Bugünkü Tutar",
        futureValueAnnualRate: "Yıllık Faiz Oranı (%)",
        futureValueYears: "Yıl",
        futureValueMonths: "Ay",
        futureValueDays: "Gün",
        futureValueResults: "Gelecek Değer Sonuçları",
        futureValueValue: "Gelecek Değer",
        futureValueAnnuityCalculatorTitle: "Eşit Ödemelerin Gelecek Değeri",
        futureValueAnnuityCalculatorDescription:
          "Eşit ödemelerin gelecekteki toplam değerini hesaplayın.",
        futureValueAnnuityPayment: "Periyodik Ödeme",
        futureValueAnnuityAnnualRate: "Yıllık Faiz Oranı (%)",
        futureValueAnnuityYears: "Yıl",
        futureValueAnnuityMonths: "Ay",
        futureValueAnnuityDays: "Gün",
        futureValueAnnuityResults: "Gelecek Değer Sonuçları",
        futureValueAnnuityValue: "Gelecek Değer",
        presentValueAnnuityCalculatorTitle: "Eşit Ödemelerin Bugünkü Değeri",
        presentValueAnnuityCalculatorDescription:
          "Eşit ödemelerin bugünkü toplam değerini hesaplayın.",
        presentValueAnnuityPayment: "Periyodik Ödeme",
        presentValueAnnuityAnnualRate: "Yıllık Faiz Oranı (%)",
        presentValueAnnuityYears: "Yıl",
        presentValueAnnuityMonths: "Ay",
        presentValueAnnuityDays: "Gün",
        presentValueAnnuityResults: "Bugünkü Değer Sonuçları",
        presentValueAnnuityValue: "Bugünkü Değer",
        simpleDeposit: "Basit Faiz",
        compoundDeposit: "Bileşik Faiz",
        presentValue: "Bugünkü Değer",
        futureValue: "Gelecek Değer",
        presentValueAnnuity: "Bugünkü Değer",
        futureValueAnnuity: "Gelecek Değer",

        // Chat Section
        aiFinancialAssistant: "AIris Finansal Asistan",
        askQuestions:
          "Finansal belgeleriniz hakkında sorular sorun ve AI destekli öngörüler alın",
        history: "Geçmiş",
        newChat: "Yeni Sohbet",
        chatHistory: "Sohbet Geçmişi",
        close: "Kapat",
        loadingChatHistory: "Sohbet geçmişi yükleniyor...",
        welcomeToAiris: "AIris'e Hoş Geldiniz!",
        welcomeMessage:
          "Ben sizin AIris finansal asistanınızım. Bazı belgeler yükleyin ve finansal verileriniz hakkında sorular sormaya başlayın.",
        suggestedQuestions: {
          latestReport: "Son raporumda neler var?",
          analyzeTrends: "Finansal trendleri analiz et",
          expenseSummary: "Gider özeti",
        },
        chatPlaceholder: "Finansal belgeleriniz hakkında bir soru sorun...",

        // Upload Section
        uploadDocuments: "Belge Yükle",
        uploadForAnalysis: "AI analizi için finansal belgeler yükleyin",
        dragDropFiles: "Dosyaları Buraya Sürükleyip Bırakın",
        dropFilesToChat: "Dosyaları sohbete bırak",
        dropFilesDescription:
          "Konuşmaya eklemek için dosyalarınızı buraya bırakın",
        or: "veya",
        browseFiles: "dosyalara göz atın",
        supportedFormats: "Desteklenen: PDF, DOCX, XLSX, Resimler",
        uploadFilesAction: "Dosyaları Yükle",
        normalFile: "Normal Dosya Ekle",
        photolessMode: "Fotoğrafsız Mod",

        // Files Section
        documentLibrary: "Belge Kütüphanesi",
        manageDocuments: "Yüklediğiniz finansal belgeleri yönetin",
        noDocuments: "Henüz belge yok",
        uploadToGetStarted: "Başlamak için bazı belgeler yükleyin",

        // Created Documents Section
        createdDocumentsLibrary: "Oluşturulan Belgeler Kütüphanesi",
        manageCreatedDocuments:
          "AI tarafından oluşturulan finansal belgeleri görüntüleyin ve yönetin",
        noCreatedDocuments: "Henüz oluşturulan belge yok",
        askAiToCreateDocuments:
          "AI'dan finansal raporlar ve belgeler oluşturmasını isteyin",
        startChatBtn: "Sohbeti Başlat",
        uploadFilesBtn: "Dosya Yükle",
        deleteFile: "Dosyayı sil",

        // Finance News Section
        financeNewsTitle: "Finans Haberleri",
        latestFinancialNews:
          "En son finansal haberler ve piyasa güncellemeleri",
        refresh: "Haberleri Yenile",
        loadingNews: "En son finans haberleri yükleniyor...",
        lastUpdated: "Son güncelleme",
        readMore: "Devamını Oku",
        backToNews: "Haberlere Geri Dön",
        goBack: "Geri dön",
        sourcesTitle: "Kaynaklar",
        noNewsAvailable: "Haber bulunmuyor",
        fetchLatestNews: "Son Haberleri Getir",
        getLatestNews: "Son Haberleri Getir",
        manualUpdateInfo: "Yenile butonuna tıklayarak en son haberleri alın",
        marketOutlook: "Piyasa Görünümü",

        // News Chat Section
        askAboutNews: "Bu haber hakkında soru sor",
        chatDescription:
          "Bu haber makalesi hakkında sorular sorun ve AI destekli öngörüler alın",
        askQuestionPlaceholder: "Bu haber hakkında sorular sorun...",
        followUpQuestionPlaceholder: "Bir takip sorusu sorun...",

        // Settings Section
        settingsTitle: "Ayarlar",
        configureApp: "AIris masaüstü uygulamanızı yapılandırın",
        backendConfiguration: "Sunucu Yapılandırması",
        apiBaseUrl: "Sunucu Adresi",
        requestTimeout: "İstek Zaman Aşımı (saniye)",
        interfacePreferences: "Arayüz Tercihleri",
        theme: "Tema",
        language: "Dil",
        autoScrollChat: "Sohbeti otomatik kaydır",
        about: "Hakkında",
        version: "Sürüm",
        platform: "Platform",

        // Theme options
        auto: "Otomatik",
        light: "Açık",
        dark: "Koyu",

        // Language options
        english: "English",
        turkish: "Türkçe",

        // Upload Progress
        preparing: "Hazırlanıyor...",
        preparingFile: "Dosya hazırlanıyor...",
        readingFile: "Dosya okunuyor...",
        uploading: "Yükleniyor...",
        processingWithAI: "Belge işleniyor...",
        uploadComplete: "Yükleme tamamlandı!",
        uploadFailed: "Yükleme başarısız",
        retry: "Tekrar Dene",
        complete: "Tamamlandı",
        error: "Hata",
        avgSpeed: "Ort",
        completedIn: "Tamamlandı",
        errorOccurred: "Hata oluştu",

        // File Previews
        previewLoading: "Önizleme yükleniyor...",
        previewUnavailable: "Önizleme mevcut değil",
        previewError: "Önizleme hatası",
        previewNotAvailable: "Önizleme mevcut değil",

        // Notifications
        fileUploadedSuccessfully: "Dosya yüklendi",
        fileDeletedSuccessfully: "Dosya silindi",
        failedToDeleteFile: "Dosya silinemedi",
        failedToUploadFile: "Dosya yüklenemedi",
        connectionLost: "Bağlantı kesildi",
        connectionRestored: "Bağlantı geri yüklendi",

        // Common
        yes: "Evet",
        no: "Hayır",
        cancel: "İptal",
        confirm: "Onayla",
        delete: "Sil",
        save: "Kaydet",
        apply: "Uygula",
        reset: "Sıfırla",

        // File deletion confirmation
        deleteConfirmation:
          '"{filename}" dosyasını silmek istediğinizden emin misiniz?\\n\\nBu işlem dosyayı ve tüm verilerini belge arşivinden kalıcı olarak kaldıracaktır.',

        // File size units
        bytes: "B",
        kilobytes: "KB",
        megabytes: "MB",
        gigabytes: "GB",

        // Time units
        seconds: "s",
        minutes: "d",
        hours: "s",
        days: "g",

        // Error messages
        networkError: "Ağ hatası",
        serverError: "Sunucu hatası",
        unknownError: "Bilinmeyen hata",
        fileNotFound: "Dosya bulunamadı",
        accessDenied: "Erişim reddedildi",

        // Welcome and initialization messages
        welcomeAssistantMessage:
          "Merhaba! Ben sizin AI finansal belge asistanınızım. Belgelerinizi yükleyin ve onlar hakkında sorular sorun.",

        // Settings messages
        settingsSavedSuccessfully: "Ayarlar kaydedildi!",

        // News messages
        loadingLatestNews: "En son finans haberleri yükleniyor...",
        failedToLoadNews: "Haberler yüklenemedi",
        unableToFetchNews: "Finans haberleri alınamadı. Lütfen tekrar deneyin.",
        lastUpdatedAt: "Son güncelleme:",
        failedToUpdate: "Güncelleme başarısız",

        // Time format
        minutesAgo: "dk önce",
        hoursAgo: "sa önce",
        daysAgo: "gün önce",
        justNow: "Şimdi",

        // Action buttons
        retryAction: "Tekrar Dene",

        // File operations
        areYouSureDelete: "Bu dosyayı silmek istediğinizden emin misiniz?",

        // Chat messages
        sorryError: "Üzgünüm, isteğinizi işleyemedim:",
        apologizeResponse: "Özür dilerim, uygun bir yanıt oluşturamadım.",
        sorryEncounteredError:
          "Üzgünüm, isteğinizi işlerken bir hatayla karşılaştım. Lütfen tekrar deneyin.",
        requestTookTooLong:
          "İstek çok uzun sürdü. AI servisi meşgul olabilir. Lütfen tekrar deneyin.",
        connectionErrorCheck:
          "Bağlantı hatası. Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.",

        // File upload messages
        downloadingFile: "İndiriliyor",
        openedFile: "Açıldı",
        unableToOpenDirectly: "Doğrudan açılamıyor",
        failedToOpenFile: "Açılamadı. Lütfen tekrar deneyin.",
        deletingFile: "Dosya siliniyor...",

        // File library messages
        uploadedOn: "Yüklenme",
        downloadFile: "Dosyayı indir",
        deleteFile: "Dosyayı sil",
        refresh: "Haberleri Yenile",

        // Error states
        errorLoadingFiles: "Dosyalar yüklenirken hata",
        failedToLoadFiles:
          "Dosyalar yüklenemedi. Lütfen daha sonra tekrar deneyin.",

        // Document Verification Section
        documentVerification: "Belge Doğrulama",
        documentVerificationTitle: "Belge Doğrulama",
        verifyDocumentsDesc:
          "Belgelerin orijinalliğini doğrulamak ve potansiyel sahtekarlığı tespit etmek için yükleyin",
        verificationDragDrop: "Doğrulanacak Belgeyi Bırakın",
        verificationSupportedFormats: "Desteklenen: PDF, JPG, PNG, TIFF, BMP",
        documentType: "Belge Türü",
        autoDetect: "Otomatik Tespit",
        invoice: "Fatura",
        receipt: "Fiş/Makbuz",
        bankStatement: "Banka Ekstresi",
        payslip: "Maaş Bordrosu",
        contract: "Sözleşme",
        taxDeclaration: "Vergi Beyannamesi",
        other: "Diğer",
        verifyDocument: "Belgeyi Doğrula",
        verificationResults: "Doğrulama Sonuçları",
        confidence: "Güven",
        verificationStatus: "Durum",
        fraudRisk: "Sahtekarlık Riski",
        verificationStages: "Doğrulama Aşamaları",
        issuesFound: "Bulunan Sorunlar",
        downloadReport: "Raporu İndir",
        verifyAnother: "Başka Belge Doğrula",
        verificationCompleted: "Doğrulama başarıyla tamamlandı",
        verificationFailed: "Belge doğrulama başarısız oldu",
        pleaseSelectFile: "Lütfen doğrulanacak bir dosya seçin",
        unsupportedFileType: "Desteklenmeyen dosya türü",
        noVerificationDataToDownload:
          "İndirilecek doğrulama verisi mevcut değil",
        reportDownloaded: "Doğrulama raporu başarıyla indirildi",
        wolframMathVerification: "Wolfram Alpha Matematiksel Doğrulama",
        wolframMathVerificationDesc:
          "Hesaplamalar, sahtekarlık tespiti ve para birimi doğrulaması için gelişmiş matematiksel doğrulamayı etkinleştir",
        // Verification stage names
        qualityControl: "Kalite Kontrol",
        documentClassification: "Belge Sınıflandırma",
        textExtraction: "Metin Çıkarma",
        templateValidation: "Şablon Doğrulama",
        dataConsistency: "Veri Tutarlılığı",
        fraudAnalysis: "Sahtekarlık Analizi",
        // Verification status values
        verified: "Doğrulandı",
        reviewRequired: "İnceleme Gerekli",
        rejected: "Reddedildi",
        passed: "Geçti",
        failed: "Başarısız",
        warning: "Uyarı",
        // Additional verification terms
        score: "Puan",
        noDetailsAvailable: "Detay bulunmuyor",
        verifying: "Doğrulanıyor...",
        startingVerification: "Doğrulama başlatılıyor...",
        selected: "Seçildi",
        // Risk levels
        low: "Düşük",
        medium: "Orta",
        high: "Yüksek",
        // Quality levels
        good: "İyi",
        fair: "Orta",
        poor: "Kötü",
        // Document types
        announcement: "Duyuru",
        expense_voucher: "Harcama Fişi",

        // File Selection
        selectFiles: "Dosya Seç",
        selectAll: "Tümünü Seç",
        deselectAll: "Seçimi Kaldır",
        writeReport: "Rapor Yaz",
        analyzeData: "Veri Analizi",
        summarize: "Özetle",
        loadingFiles: "Dosyalar yükleniyor...",
        noFilesAvailable: "Dosya mevcut değil. Önce bazı dosyalar yükleyin.",
        filesSelected: "dosya seçildi",
        allFilesSelected: "Tüm dosyalar seçildi",
        save: "Kaydet",
        cancel: "İptal",
        createNewProfile: "Yeni Profil Oluştur",
        selectProfile: "Profil Seç",
        searchFiles: "Dosyalarda ara...",
        profileName: "Profil Adı",
        enterProfileName: "Profil ismini girin",
        noFilesSelected: "Lütfen en az bir dosya seçin.",
        profileNameRequired: "Lütfen profil ismi girin.",
        profileNameExists: "Bu isimle bir profil zaten mevcut.",
        profileSaved: "Profil başarıyla kaydedildi!",
        unknownError: "Beklenmeyen bir hata oluştu.",

        // Currency labels
        gold: "Altın",
        goldUsdPerOz: "Altın (USD/ons)",
        goldTryPerGram: "Altın (₺/gram)",
        usdTry: "USD/TRY",
        eurTry: "EUR/TRY",
        usdEur: "USD/EUR",

        // Status labels
        cached: "Önbellekte",
        live: "Canlı",
        error: "Hata",
        offline: "Çevrimdışı",
        processing: "İşleniyor...",
        unknown: "Bilinmeyen",
        failed: "Başarısız",

        // Balance Calendar
        balanceCalendar: {
          navLabel: "Ödemeler Dengesi",
          title: "Ödemeler Dengesi",
          subtitle:
            "İşlenen Excel çalışma kitaplarından türetilen günlük nakit pozisyonlarını takip edin.",
          timeframeLabel: "Zaman Aralığı",
          timeframes: {
            last1Month: "Son 1 ay",
            last3Months: "Son 3 ay",
            last6Months: "Son 6 ay",
            last9Months: "Son 9 ay",
            last12Months: "Son 12 ay",
          },
          refresh: "Yenile",
          processTitle: "Ödemeler Dengesi Belgesini İşle",
          processDescription:
            "Bir ödemeler dengesi belgesi (Excel, PDF, görsel vb.) yükleyin. Ayrıştırıcı defteri çıkarır ve ajan işlemleri otomatik olarak normalleştirir.",
          uploadButton: "Yükle ve İşle",
          uploadNote:
            "Ajanı çalıştırmadan önce defter detaylarını çıkarmak için parser.py kullanır.",
          runAgent: "Ajanı Çalıştır",
          loading: undefined,
          selectDayPrompt: "İşlem detaylarını görmek için bir gün seçin.",
          noDocuments: "Ödemeler dengesi belgesi bulunamadı",
          fetchDocumentsError: "Belgeler yüklenemedi",
          retry: "Tekrar dene",
          summaryPeriodLabel: "Dönem",
          latestActivity: "Son işlem: {date}",
          noActivity: "Henüz kayıtlı işlem yok",
          totalIncome: "Toplam Gelir",
          totalExpense: "Toplam Gider",
          netChange: "Net Değişim",
          weekdays: ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
          legendTitle: "Net ödeme yoğunluğu",
          incomeLabel: "Gelir",
          expenseLabel: "Gider",
          netLabel: "Net",
          tooltipNoTransactions: "İşlem yok",
          dayNoTransactions: "Bu gün için kayıtlı işlem yok.",
          transactionsLoadError: "İşlemler yüklenemedi",
          calendarLoadError: "Takvim yüklenemedi",
          calendarFetchError: "Takvim verileri alınamadı",
          selectFilePrompt: "Lütfen önce bir ödemeler dengesi belgesi yükleyin.",
          runningAgent: "Ajan çalıştırılıyor...",
          agentRunFailed: "Ajan çalışması başarısız oldu",
          agentRequestFailed: "Ajan çalıştırılamadı.",
          agentSuccess: "Ajan başarıyla tamamlandı.",
          unsupportedFileType: "Ödemeler dengesi işlemesi için desteklenmeyen dosya türü.",
          uploadingFile: "{filename} yükleniyor...",
          uploadSuccess: "{filename} yüklendi. Ajan çalıştırılıyor...",
          uploadFailed: "Ödemeler dengesi belgesi yüklenemedi.",
          transactionSingular: "{count} işlem",
          transactionPlural: "{count} işlem",
          direction: {
            income: "Gelir",
            expense: "Gider",
          },
        },

        // Navigation
        goToChat: "Sohbete Git",

        // Stock/Company Details
        exchange: "Borsa",
        istanbulStockExchange: "Borsa İstanbul",
        fulltimeEmployees: "Tam Zamanlı Çalışan",
        sector: "Sektör",
        industry: "Endüstri",
        country: "Ülke",
        loading: "Yükleniyor...",
        companyInfo: "Şirket Bilgileri",
        prevClose: "Önceki Kapanış",
        open: "Açılış",
        dayRange: "Günlük Aralık",
        volume: "Hacim",
        searchStocks: "Hisse ara...",
        noResultsFound: "Sonuç bulunamadı",
        searchForStocks: "Hisse arayın",
        atClose: "Kapanışta",
      },
    };
  }

  loadSavedLanguage() {
    const saved = localStorage.getItem("airis-language");
    if (saved && this.translations[saved]) {
      this.currentLanguage = saved;
    } else {
      // Auto-detect browser language
      const browserLang = navigator.language || navigator.userLanguage;
      if (browserLang.startsWith("tr")) {
        this.currentLanguage = "tr";
      }
    }
  }

  setLanguage(language) {
    if (!this.translations[language]) {
      console.warn(`Language '${language}' not supported`);
      return;
    }

    this.currentLanguage = language;
    localStorage.setItem("airis-language", language);

    // Update document language
    document.documentElement.lang = language;

    // Notify observers
    this.notifyObservers();
  }

  getCurrentLanguage() {
    return this.currentLanguage;
  }

  get(key, replacements = {}) {
    const keys = key.split(".");
    let value = this.translations[this.currentLanguage];

    for (const k of keys) {
      if (value && typeof value === "object") {
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
        if (fallback && typeof fallback === "object") {
          fallback = fallback[k];
        } else {
          fallback = key; // Return key if no translation found
          break;
        }
      }
      value = fallback;
    }

    // Replace placeholders
    if (typeof value === "string" && Object.keys(replacements).length > 0) {
      Object.keys(replacements).forEach((placeholder) => {
        value = value.replace(
          new RegExp(`{${placeholder}}`, "g"),
          replacements[placeholder]
        );
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
      this.observers = this.observers.filter((obs) => obs !== callback);
    };
  }

  notifyObservers() {
    this.observers.forEach((callback) => callback(this.currentLanguage));
  }

  // Get available languages
  getAvailableLanguages() {
    return Object.keys(this.translations).map((code) => ({
      code,
      name: this.translations[code].language || code,
    }));
  }

  // Update all text elements with data-i18n attribute
  updatePageTexts() {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.getAttribute("data-i18n");
      const text = this.get(key);

      if (
        element.tagName === "INPUT" &&
        (element.type === "text" || element.type === "search")
      ) {
        element.placeholder = text;
      } else if (element.tagName === "TEXTAREA") {
        element.placeholder = text;
      } else {
        element.textContent = text;
      }
    });

    // Update elements with data-i18n-placeholder attribute
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      const key = element.getAttribute("data-i18n-placeholder");
      const text = this.get(key);
      element.placeholder = text;
    });

    document.querySelectorAll("[data-i18n-title]").forEach((element) => {
      const key = element.getAttribute("data-i18n-title");
      element.title = this.get(key);
    });

    document.querySelectorAll("[data-i18n-tooltip]").forEach((element) => {
      const key = element.getAttribute("data-i18n-tooltip");
      const text = this.get(key);
      element.setAttribute("data-tooltip", text);
      element.setAttribute("aria-label", text);
    });

    // Update title
    document.title = this.get("appTitle");
  }
}

// Create global language service instance
window.languageService = new LanguageService();

// Auto-update texts when language changes
window.languageService.subscribe(() => {
  window.languageService.updatePageTexts();
});

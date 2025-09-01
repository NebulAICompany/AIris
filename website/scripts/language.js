/**
 * Language Management System for AIris Website
 * Supports Turkish and English with best practices implementation
 */

class LanguageManager {
  constructor() {
    this.currentLanguage = "en"; // Default to English as requested
    this.supportedLanguages = ["en", "tr"];
    this.translations = this.getTranslations();
    this.init();
  }

  init() {
    this.detectLanguage();
    this.loadLanguage();
    this.setupLanguageSwitcher();
    this.updatePageLanguage();
  }

  // Language detection with fallback to English
  detectLanguage() {
    // Check localStorage first
    const savedLanguage = localStorage.getItem("airis-language");
    if (savedLanguage && this.supportedLanguages.includes(savedLanguage)) {
      this.currentLanguage = savedLanguage;
      return;
    }

    // Check browser language
    const browserLanguage = navigator.language || navigator.userLanguage;
    const primaryLanguage = browserLanguage.split("-")[0];

    if (this.supportedLanguages.includes(primaryLanguage)) {
      this.currentLanguage = primaryLanguage;
    } else {
      // Default to English as requested
      this.currentLanguage = "en";
    }
  }

  // Load and apply language
  loadLanguage() {
    this.applyTranslations();
    this.saveLanguage();
  }

  // Switch language
  switchLanguage(languageCode) {
    if (this.supportedLanguages.includes(languageCode)) {
      this.currentLanguage = languageCode;
      this.loadLanguage();
      this.updatePageLanguage();
      this.updateLanguageSwitcher();
    }
  }

  // Update HTML lang attribute for SEO
  updatePageLanguage() {
    document.documentElement.lang = this.currentLanguage;

    // Update meta tags for better SEO
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.content =
        this.translations[this.currentLanguage].meta.description;
    }
  }

  // Apply translations to the page
  applyTranslations() {
    const elements = document.querySelectorAll("[data-translate]");
    elements.forEach((element) => {
      const key = element.getAttribute("data-translate");
      const translation = this.getTranslation(key);
      if (translation) {
        if (
          element.tagName === "INPUT" &&
          (element.type === "text" || element.type === "email")
        ) {
          element.placeholder = translation;
        } else if (element.tagName === "TEXTAREA") {
          element.placeholder = translation;
        } else if (element.tagName === "OPTION") {
          element.textContent = translation;
        } else {
          element.textContent = translation;
        }
      }
    });
  }

  // Get translation by key
  getTranslation(key) {
    const keys = key.split(".");
    let translation = this.translations[this.currentLanguage];

    for (const k of keys) {
      if (translation && translation[k]) {
        translation = translation[k];
      } else {
        return null;
      }
    }

    return translation;
  }

  // Save language preference
  saveLanguage() {
    localStorage.setItem("airis-language", this.currentLanguage);
  }

  // Setup language switcher
  setupLanguageSwitcher() {
    const switcher = document.getElementById("language-switcher");
    if (switcher) {
      switcher.addEventListener("click", (e) => {
        e.preventDefault();
        this.toggleLanguage();
      });
    }
  }

  // Toggle between languages
  toggleLanguage() {
    const newLanguage = this.currentLanguage === "en" ? "tr" : "en";
    this.switchLanguage(newLanguage);
  }

  // Update language switcher display
  updateLanguageSwitcher() {
    const switcher = document.getElementById("language-switcher");
    if (switcher) {
      const currentLangText =
        this.currentLanguage === "en" ? "Türkçe" : "English";
      switcher.textContent = currentLangText;
      switcher.setAttribute("aria-label", `Switch to ${currentLangText}`);
    }
  }

  // Get all translations
  getTranslations() {
    return {
      en: {
        meta: {
          description:
            "AIris is an advanced AI-powered desktop application for financial document processing, verification, and analysis. Experience the future of financial technology with Nebula Intelligence.",
        },
        nav: {
          home: "Home",
          features: "Features",
          demo: "Demo",
          gallery: "Gallery",
          contact: "Contact",
        },
        hero: {
          title: "All your financial operations",
          titleHighlight: "in one platform",
          description:
            "AIris handles document verification, financial analysis, data processing, and market research.",
          descriptionHighlight:
            "No additional resources needed - everything you need is here.",
          discover: "Discover AIris",
        },
        features: {
          title: "What can AIris do for you?",
          documentVerification: "Document Verification",
          financialAnalysis: "Financial Analysis",
          visualIntelligence: "Visual Intelligence",
          mathematicalComputing: "Mathematical Computing",
          webSearch: "Web Search",
          userMessage: "You",
          airisMessage: "AIris",
          documentQuestion: "Is this invoice authentic?",
          documentAnswer:
            "Document verified ✓ No fraud detected. All signatures and watermarks are authentic.",
          analysisQuestion: "Show me Tesla stock with moving averages",
          analysisAnswer:
            "Interactive chart generated ✓ Tesla at $248.50 with 50-day and 200-day moving averages.",
          visualQuestion: "What does this revenue chart show?",
          visualAnswer:
            "Chart analysis complete ✓ 23% Q3 growth with peak in September. Trend shows strong upward momentum.",
          mathQuestion: "Calculate CAGR and statistical significance",
          mathAnswer:
            "Analysis complete ✓ CAGR: 15.7% with 95% confidence interval. Results statistically significant.",
          searchQuestion: "Find latest news about this company",
          searchAnswer:
            "News retrieved ✓ 5 recent articles: earnings beat expectations, new partnerships announced.",
        },
        demo: {
          title: "See AIris in Action",
          description:
            "Watch how AIris transforms complex financial document processing into simple, automated workflows.",
          videoTitle: "AIris Product Demo",
          videoDescription: "Complete walkthrough of features and capabilities",
        },
        gallery: {
          title: "Gallery",
          mainDashboard: "Main Dashboard",
          financialCharts: "Financial Charts",
          documentVerification: "Document Verification",
        },
        security: {
          title: "Your Data, Your Control",
          description:
            "Enterprise-grade security with complete privacy protection.",
          onPremise: "On-Premise Processing",
          onPremiseDesc:
            "All data processing happens on your local infrastructure. Your documents never leave your environment.",
          encryption: "End-to-End Encryption",
          encryptionDesc:
            "Military-grade encryption protects your data at rest and in transit. Zero-knowledge architecture ensures privacy.",
          noDataCollection: "No Data Collection",
          noDataCollectionDesc:
            "We don't collect, store, or share your financial data. What's yours stays yours, always.",
        },
        contact: {
          title: "Ready to transform your workflow?",
          formTitle: "Send us a Message",
          name: "Name",
          namePlaceholder: "Your full name",
          email: "Email",
          emailPlaceholder: "your.email@example.com",
          subject: "Subject",
          subjectPlaceholder: "Select a subject",
          message: "Message",
          messagePlaceholder: "Tell us how we can help you...",
          submit: "Submit",
          generalInquiry: "General Inquiry",
          requestDemo: "Request Demo",
          technicalSupport: "Technical Support",
          partnership: "Partnership",
          other: "Other",
        },
        footer: {
          tagline: "AI-Powered Financial Document Processing",
          product: "Product",
          legal: "Legal",
          privacyPolicy: "Privacy Policy",
          termsOfService: "Terms of Service",
          copyright: "NebulAI Intelligence. All rights reserved.",
        },
        legal: {
          backToHome: "Back to Home",
          lastUpdated: "Last updated: September 1, 2025",
          privacyPolicy: "Privacy Policy",
          termsOfService: "Terms of Service",
          contactUs: "Contact Us",
        },
      },
      tr: {
        meta: {
          description:
            "AIris, finansal belge işleme, doğrulama ve analiz için gelişmiş AI destekli masaüstü uygulamasıdır. Nebula Intelligence ile finansal teknolojinin geleceğini deneyimleyin.",
        },
        nav: {
          home: "Ana Sayfa",
          features: "Özellikler",
          demo: "Demo",
          gallery: "Galeri",
          contact: "İletişim",
        },
        hero: {
          title: "Tüm finansal işlemleriniz",
          titleHighlight: "tek platformda",
          description:
            "AIris belge doğrulama, finansal analiz, veri işleme ve pazar araştırması yapar.",
          descriptionHighlight:
            "Ek kaynak gerekmez - ihtiyacınız olan her şey burada.",
          discover: "AIris'i Keşfedin",
        },
        features: {
          title: "AIris sizin için neler yapabilir?",
          documentVerification: "Belge Doğrulama",
          financialAnalysis: "Finansal Analiz",
          visualIntelligence: "Görsel Zeka",
          mathematicalComputing: "Matematiksel Hesaplama",
          webSearch: "Web Arama",
          userMessage: "Siz",
          airisMessage: "AIris",
          documentQuestion: "Bu fatura gerçek mi?",
          documentAnswer:
            "Belge doğrulandı ✓ Sahtecilik tespit edilmedi. Tüm imzalar ve filigranlar orijinal.",
          analysisQuestion: "Tesla hissesini hareketli ortalamalarla göster",
          analysisAnswer:
            "İnteraktif grafik oluşturuldu ✓ Tesla $248.50'de 50 günlük ve 200 günlük hareketli ortalamalarla.",
          visualQuestion: "Bu gelir grafiği ne gösteriyor?",
          visualAnswer:
            "Grafik analizi tamamlandı ✓ Q3'te %23 büyüme, Eylül'de zirve. Trend güçlü yukarı momentum gösteriyor.",
          mathQuestion: "CAGR ve istatistiksel anlamlılığı hesapla",
          mathAnswer:
            "Analiz tamamlandı ✓ CAGR: %15.7, %95 güven aralığı. Sonuçlar istatistiksel olarak anlamlı.",
          searchQuestion: "Bu şirket hakkında son haberleri bul",
          searchAnswer:
            "Haberler alındı ✓ 5 son makale: kazançlar beklentileri aştı, yeni ortaklıklar duyuruldu.",
        },
        demo: {
          title: "AIris'i Çalışırken Görün",
          description:
            "AIris'in karmaşık finansal belge işlemeyi nasıl basit, otomatik iş akışlarına dönüştürdüğünü izleyin.",
          videoTitle: "AIris Ürün Demo",
          videoDescription: "Özellikler ve yeteneklerin tam kılavuzu",
        },
        gallery: {
          title: "Galeri",
          mainDashboard: "Ana Kontrol Paneli",
          financialCharts: "Finansal Grafikler",
          documentVerification: "Belge Doğrulama",
        },
        security: {
          title: "Verileriniz, Kontrolünüz",
          description: "Kurumsal düzeyde güvenlik ile tam gizlilik koruması.",
          onPremise: "Şirket İçi İşleme",
          onPremiseDesc:
            "Tüm veri işleme yerel altyapınızda gerçekleşir. Belgeleriniz ortamınızdan asla çıkmaz.",
          encryption: "Uçtan Uca Şifreleme",
          encryptionDesc:
            "Askeri düzeyde şifreleme verilerinizi hem beklerken hem de aktarım sırasında korur. Sıfır bilgi mimarisi gizliliği sağlar.",
          noDataCollection: "Veri Toplama Yok",
          noDataCollectionDesc:
            "Finansal verilerinizi toplamıyor, saklamıyor veya paylaşmıyoruz. Sizin olan her zaman sizin kalır.",
        },
        contact: {
          title: "İş akışınızı dönüştürmeye hazır mısınız?",
          formTitle: "Bize Mesaj Gönderin",
          name: "Ad",
          namePlaceholder: "Adınız ve soyadınız",
          email: "E-posta",
          emailPlaceholder: "email@ornek.com",
          subject: "Konu",
          subjectPlaceholder: "Bir konu seçin",
          message: "Mesaj",
          messagePlaceholder: "Size nasıl yardımcı olabileceğimizi söyleyin...",
          submit: "Gönder",
          generalInquiry: "Genel Soru",
          requestDemo: "Demo Talep Et",
          technicalSupport: "Teknik Destek",
          partnership: "Ortaklık",
          other: "Diğer",
        },
        footer: {
          tagline: "AI Destekli Finansal Belge İşleme",
          product: "Ürün",
          legal: "Yasal",
          privacyPolicy: "Gizlilik Politikası",
          termsOfService: "Hizmet Şartları",
          copyright: "NebulAI Intelligence. Tüm hakları saklıdır.",
        },
        legal: {
          backToHome: "Ana Sayfaya Dön",
          lastUpdated: "Son güncelleme: 1 Eylül 2025",
          privacyPolicy: "Gizlilik Politikası",
          termsOfService: "Hizmet Şartları",
          contactUs: "İletişim",
        },
      },
    };
  }
}

// Initialize language manager when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.languageManager = new LanguageManager();
});

/**
 * Main JavaScript for Nebula Intelligence Website
 * AIris Product Website Interactive Features
 */

class NebulaWebsite {
  constructor() {
    this.navbar = document.getElementById("navbar");
    this.mobileMenuToggle = document.getElementById("mobile-menu-toggle");
    this.navMenu = document.getElementById("nav-menu");
    this.init();
  }

  init() {
    this.setupScrollEffects();
    this.setupSmoothScrolling();
    this.setupMobileMenu();
    this.setupAnimations();
    this.setupVideoPlayer();
    this.setupDownloadButtons();
    this.startPerformanceAnimations();
  }

  // Navbar scroll effects
  setupScrollEffects() {
    let lastScrollTop = 0;

    window.addEventListener("scroll", () => {
      const scrollTop =
        window.pageYOffset || document.documentElement.scrollTop;

      // Add/remove scrolled class
      if (scrollTop > 50) {
        this.navbar.classList.add("scrolled");
      } else {
        this.navbar.classList.remove("scrolled");
      }

      // Hide/show navbar on scroll
      if (scrollTop > lastScrollTop && scrollTop > 100) {
        this.navbar.style.transform = "translateY(-100%)";
      } else {
        this.navbar.style.transform = "translateY(0)";
      }

      lastScrollTop = scrollTop;
    });
  }

  // Smooth scrolling for navigation links
  setupSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        e.preventDefault();
        const targetId = anchor.getAttribute("href").substring(1);
        const targetElement = document.getElementById(targetId);

        if (targetElement) {
          const navbarHeight = this.navbar.offsetHeight;
          const targetPosition = targetElement.offsetTop - navbarHeight;

          window.scrollTo({
            top: targetPosition,
            behavior: "smooth",
          });

          // Close mobile menu if open
          this.closeMobileMenu();

          // Update active nav link
          this.updateActiveNavLink(targetId);
        }
      });
    });
  }

  // Mobile menu functionality
  setupMobileMenu() {
    if (this.mobileMenuToggle && this.navMenu) {
      this.mobileMenuToggle.addEventListener("click", () => {
        this.toggleMobileMenu();
      });

      // Close menu when clicking outside
      document.addEventListener("click", (e) => {
        if (!this.navbar.contains(e.target)) {
          this.closeMobileMenu();
        }
      });
    }
  }

  toggleMobileMenu() {
    this.navMenu.classList.toggle("mobile-open");
    this.mobileMenuToggle.classList.toggle("active");
    document.body.classList.toggle("mobile-menu-open");
  }

  closeMobileMenu() {
    this.navMenu.classList.remove("mobile-open");
    this.mobileMenuToggle.classList.remove("active");
    document.body.classList.remove("mobile-menu-open");
  }

  // Update active navigation link based on scroll position
  updateActiveNavLink(targetId) {
    document.querySelectorAll(".nav-link").forEach((link) => {
      link.classList.remove("active");
    });

    const activeLink = document.querySelector(`a[href="#${targetId}"]`);
    if (activeLink) {
      activeLink.classList.add("active");
    }
  }

  // Intersection Observer for scroll-triggered animations
  setupAnimations() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px",
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animate-in");
        }
      });
    }, observerOptions);

    // Observe elements for animation
    document
      .querySelectorAll(
        ".feature-card, .tech-feature, .stat-card, .demo-check-item"
      )
      .forEach((el) => {
        el.classList.add("animate-on-scroll");
        observer.observe(el);
      });

    // Section observer for active nav links
    const sectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const sectionId = entry.target.id;
            this.updateActiveNavLink(sectionId);
          }
        });
      },
      { threshold: 0.3 }
    );

    document.querySelectorAll("section[id]").forEach((section) => {
      sectionObserver.observe(section);
    });
  }

  // Video player functionality
  setupVideoPlayer() {
    const videoPlaceholder = document.querySelector(".video-placeholder");
    const playButton = document.querySelector(".play-button");

    if (videoPlaceholder && playButton) {
      videoPlaceholder.addEventListener("click", () => {
        this.playDemoVideo();
      });
    }
  }

  playDemoVideo() {
    // Placeholder for video player functionality
    // In a real implementation, this would open a modal or embed a video
    alert(
      "Demo video would play here. Replace with actual video player implementation."
    );
  }

  // Download button functionality
  setupDownloadButtons() {
    document.querySelectorAll(".download-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const platform = btn.querySelector(".btn-platform").textContent;
        this.handleDownload(platform);
      });
    });
  }

  handleDownload(platform) {
    // Placeholder for download functionality
    // In a real implementation, this would trigger actual downloads
    console.log(`Download for ${platform} initiated`);

    // Show notification
    this.showNotification(
      `Download for ${platform} will begin shortly...`,
      "success"
    );
  }

  // Performance animations for hero section
  startPerformanceAnimations() {
    this.animateProgressBar();
    this.animateStats();
    this.animateTypingEffect();
  }

  animateProgressBar() {
    const progressFill = document.querySelector(".progress-fill");
    if (progressFill) {
      setTimeout(() => {
        progressFill.style.animation = "progressFill 3s ease-in-out infinite";
      }, 1000);
    }
  }

  animateStats() {
    const stats = document.querySelectorAll(".stat-number");
    stats.forEach((stat, index) => {
      setTimeout(() => {
        this.countUpAnimation(stat);
      }, 500 + index * 200);
    });
  }

  countUpAnimation(element) {
    const target = element.textContent;
    const isPercentage = target.includes("%");
    const isTime = target.includes("ms");
    const isCount = target.includes("K+");

    let startValue = 0;
    let endValue;
    let suffix = "";

    if (isPercentage) {
      endValue = parseFloat(target);
      suffix = "%";
    } else if (isTime) {
      endValue = parseFloat(target);
      suffix = "ms";
    } else if (isCount) {
      endValue = parseFloat(target);
      suffix = "K+";
    } else {
      endValue = parseFloat(target) || 0;
    }

    const duration = 2000;
    const stepTime = Math.abs(Math.floor(duration / endValue));

    const timer = setInterval(() => {
      startValue += endValue / (duration / 16);
      if (startValue >= endValue) {
        startValue = endValue;
        clearInterval(timer);
      }
      element.textContent = Math.floor(startValue) + suffix;
    }, 16);
  }

  animateTypingEffect() {
    const badge = document.querySelector(".hero-badge span");
    if (badge) {
      const text = badge.textContent;
      badge.textContent = "";
      badge.style.width = "auto";

      let i = 0;
      const typeInterval = setInterval(() => {
        badge.textContent += text.charAt(i);
        i++;
        if (i >= text.length) {
          clearInterval(typeInterval);
        }
      }, 50);
    }
  }

  // Utility function to show notifications
  showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
      <i class="fas fa-${
        type === "success" ? "check-circle" : "info-circle"
      }"></i>
      <span>${message}</span>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.add("show");
    }, 100);

    setTimeout(() => {
      notification.classList.remove("show");
      setTimeout(() => {
        document.body.removeChild(notification);
      }, 300);
    }, 3000);
  }

  // Utility function for smooth animations
  easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
  }
}

// Stellar background animation system
class StellarBackground {
  constructor() {
    this.createShootingStars();
    this.createFloatingParticles();
  }

  createShootingStars() {
    setInterval(() => {
      this.createShootingStar();
    }, 3000 + Math.random() * 5000);
  }

  createShootingStar() {
    const star = document.createElement("div");
    star.className = "shooting-star";
    star.style.cssText = `
      position: fixed;
      width: 2px;
      height: 2px;
      background: linear-gradient(45deg, white, #8b5cf6);
      border-radius: 50%;
      z-index: -1;
      pointer-events: none;
      left: ${Math.random() * 100}vw;
      top: ${Math.random() * 50}vh;
      animation: shootingStar 2s linear forwards;
    `;

    document.body.appendChild(star);

    setTimeout(() => {
      if (star.parentNode) {
        star.parentNode.removeChild(star);
      }
    }, 2000);
  }

  createFloatingParticles() {
    for (let i = 0; i < 20; i++) {
      setTimeout(() => {
        this.createParticle();
      }, i * 200);
    }
  }

  createParticle() {
    const particle = document.createElement("div");
    particle.className = "floating-particle";
    particle.style.cssText = `
      position: fixed;
      width: ${2 + Math.random() * 4}px;
      height: ${2 + Math.random() * 4}px;
      background: rgba(139, 92, 246, ${0.3 + Math.random() * 0.7});
      border-radius: 50%;
      z-index: -1;
      pointer-events: none;
      left: ${Math.random() * 100}vw;
      top: ${Math.random() * 100}vh;
      animation: floatParticle ${10 + Math.random() * 20}s ease-in-out infinite;
    `;

    document.body.appendChild(particle);
  }
}

// Performance monitoring
class PerformanceMonitor {
  constructor() {
    this.startTime = performance.now();
    this.logPageLoad();
  }

  logPageLoad() {
    window.addEventListener("load", () => {
      const loadTime = performance.now() - this.startTime;
      console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);

      // Log performance metrics
      if ("performance" in window) {
        const perfData = performance.getEntriesByType("navigation")[0];
        console.log("Performance metrics:", {
          domContentLoaded:
            perfData.domContentLoadedEventEnd -
            perfData.domContentLoadedEventStart,
          loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
          totalTime: perfData.loadEventEnd - perfData.fetchStart,
        });
      }
    });
  }
}

// Initialize everything when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const website = new NebulaWebsite();
  const stellar = new StellarBackground();
  const monitor = new PerformanceMonitor();

  console.log("🌌 Nebula Intelligence Website Initialized");
  console.log("🚀 AIris Product Website Ready");

  // Initialize Horizontal Gallery Navigation
  initializeGallery();
});

// Horizontal Gallery Navigation
function initializeGallery() {
  const track = document.querySelector(".gallery-track");
  const items = document.querySelectorAll(".gallery-item");
  const pagination = document.querySelector(".gallery-pagination");
  const indicators = document.querySelectorAll(".page-indicator");

  if (!track || !items.length) return;

  let currentIndex = 0;
  const totalItems = items.length;

  function updateNavigation() {
    // Update pagination indicators
    indicators.forEach((indicator, index) => {
      if (index === currentIndex) {
        indicator.classList.add("active");
      } else {
        indicator.classList.remove("active");
      }
    });
  }

  function goToSlide(index) {
    currentIndex = index;
    const translateX = -currentIndex * 100;
    track.style.transform = `translateX(${translateX}%)`;
    updateNavigation();
  }

  // Add pagination click events
  indicators.forEach((indicator, index) => {
    indicator.addEventListener("click", () => {
      goToSlide(index);
    });
  });

  // Initialize navigation state
  updateNavigation();

  // Touch/swipe support for mobile
  let startX = 0;
  let currentX = 0;

  track.addEventListener("touchstart", (e) => {
    startX = e.touches[0].clientX;
  });

  track.addEventListener("touchmove", (e) => {
    currentX = e.touches[0].clientX;
    e.preventDefault(); // Prevent page scroll during swipe
  });

  track.addEventListener("touchend", () => {
    const diff = startX - currentX;
    const threshold = 50;

    if (Math.abs(diff) > threshold) {
      if (diff > 0 && currentIndex < totalItems - 1) {
        // Swipe left - next
        goToSlide(currentIndex + 1);
        console.log("Swiped left - Next slide");
      } else if (diff < 0 && currentIndex > 0) {
        // Swipe right - prev
        goToSlide(currentIndex - 1);
        console.log("Swiped right - Previous slide");
      }
    }
  });

  console.log("🎠 Horizontal Gallery Navigation Initialized");
}

// Add CSS animations dynamically
const style = document.createElement("style");
style.textContent = `
  /* Animation styles */
  .animate-on-scroll {
    opacity: 0;
    transform: translateY(30px);
    transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .animate-on-scroll.animate-in {
    opacity: 1;
    transform: translateY(0);
  }
  
  @keyframes shootingStar {
    0% {
      transform: translateX(0) translateY(0);
      opacity: 1;
    }
    100% {
      transform: translateX(300px) translateY(300px);
      opacity: 0;
    }
  }
  
  @keyframes floatParticle {
    0%, 100% {
      transform: translateY(0) rotate(0deg);
      opacity: 0.3;
    }
    50% {
      transform: translateY(-50px) rotate(180deg);
      opacity: 1;
    }
  }
  
  .notification {
    position: fixed;
    top: 2rem;
    right: 2rem;
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    color: white;
    padding: 1rem 1.5rem;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-lg);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    z-index: 10000;
    transform: translateX(100%);
    opacity: 0;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .notification.show {
    transform: translateX(0);
    opacity: 1;
  }
  
  .notification.success {
    background: linear-gradient(135deg, var(--success), var(--accent-tertiary));
  }
  
  /* Mobile menu styles */
  @media (max-width: 768px) {
    .nav-menu {
      position: fixed;
      top: var(--navbar-height);
      left: 0;
      right: 0;
      background: linear-gradient(135deg, rgba(13, 2, 33, 0.95), rgba(26, 11, 46, 0.9));
      backdrop-filter: blur(20px);
      border-top: 1px solid rgba(139, 92, 246, 0.2);
      flex-direction: column;
      padding: 2rem;
      gap: 1.5rem;
      transform: translateY(-100%);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 999;
    }
    
    .nav-menu.mobile-open {
      display: flex;
      transform: translateY(0);
      opacity: 1;
    }
    
    .mobile-menu-toggle.active span:nth-child(1) {
      transform: rotate(45deg) translate(5px, 5px);
    }
    
    .mobile-menu-toggle.active span:nth-child(2) {
      opacity: 0;
    }
    
    .mobile-menu-toggle.active span:nth-child(3) {
      transform: rotate(-45deg) translate(7px, -6px);
    }
    
    body.mobile-menu-open {
      overflow: hidden;
    }
  }
`;

document.head.appendChild(style);

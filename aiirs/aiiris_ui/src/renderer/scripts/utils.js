// Utility Functions

class Utils {
  // Format file size in human readable format
  static formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  // Format date to relative time
  static formatTimeAgo(date) {
    const now = new Date();
    const diff = now - date;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString();
  }

  // Get file icon based on extension
  static getFileIcon(fileName) {
    const ext = fileName.split(".").pop().toLowerCase();

    const iconMap = {
      pdf: "fas fa-file-pdf",
      docx: "fas fa-file-word",
      doc: "fas fa-file-word",
      xlsx: "fas fa-file-excel",
      xls: "fas fa-file-excel",
      txt: "fas fa-file-alt",
      png: "fas fa-file-image",
      jpg: "fas fa-file-image",
      jpeg: "fas fa-file-image",
      gif: "fas fa-file-image",
      mp4: "fas fa-file-video",
      mp3: "fas fa-file-audio",
    };

    return iconMap[ext] || "fas fa-file";
  }

  // Debounce function
  static debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Throttle function
  static throttle(func, limit) {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), limit);
      }
    };
  }

  // Generate unique ID
  static generateId() {
    return "_" + Math.random().toString(36).substr(2, 9);
  }

  // Escape HTML to prevent XSS
  static escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Copy text to clipboard
  static async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);
      return successful;
    }
  }

  // Validate file type
  static isValidFileType(fileName) {
    const validExtensions = [
      "pdf",
      "docx",
      "doc",
      "xlsx",
      "xls",
      "txt",
      "png",
      "jpg",
      "jpeg",
      "gif",
    ];
    const ext = fileName.split(".").pop().toLowerCase();
    return validExtensions.includes(ext);
  }

  // Check if file size is acceptable
  static isValidFileSize(size, maxSizeMB = 50) {
    const maxSize = maxSizeMB * 1024 * 1024; // Convert to bytes
    return size <= maxSize;
  }

  // Validate file (combines type and size validation)
  static validateFile(file, maxSizeMB = 50) {
    return this.isValidFileType(file.name) && this.isValidFileSize(file.size, maxSizeMB);
  }

  // Sanitize filename
  static sanitizeFilename(filename) {
    return filename.replace(/[^a-z0-9.-]/gi, "_");
  }

  // Parse markdown-like text for basic formatting
  static parseBasicMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");
  }

  // Auto-resize textarea
  static autoResizeTextarea(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
  }

  // Smooth scroll to element
  static scrollToElement(element, behavior = "smooth") {
    element.scrollIntoView({ behavior, block: "nearest" });
  }

  // Check if element is in viewport
  static isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <=
        (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
  }

  // Local storage helpers
  static storage = {
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (e) {
        console.error("Failed to save to localStorage:", e);
        return false;
      }
    },

    get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (e) {
        console.error("Failed to read from localStorage:", e);
        return defaultValue;
      }
    },

    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (e) {
        console.error("Failed to remove from localStorage:", e);
        return false;
      }
    },

    clear() {
      try {
        localStorage.clear();
        return true;
      } catch (e) {
        console.error("Failed to clear localStorage:", e);
        return false;
      }
    },
  };

  // Animation helpers
  static animate = {
    fadeIn(element, duration = 300) {
      element.style.opacity = "0";
      element.style.display = "block";

      let start = performance.now();

      function step(timestamp) {
        const elapsed = timestamp - start;
        const progress = Math.min(elapsed / duration, 1);

        element.style.opacity = progress;

        if (progress < 1) {
          requestAnimationFrame(step);
        }
      }

      requestAnimationFrame(step);
    },

    fadeOut(element, duration = 300) {
      let start = performance.now();

      function step(timestamp) {
        const elapsed = timestamp - start;
        const progress = Math.min(elapsed / duration, 1);

        element.style.opacity = 1 - progress;

        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          element.style.display = "none";
        }
      }

      requestAnimationFrame(step);
    },

    slideDown(element, duration = 300) {
      element.style.height = "0px";
      element.style.overflow = "hidden";
      element.style.display = "block";

      const targetHeight = element.scrollHeight;
      let start = performance.now();

      function step(timestamp) {
        const elapsed = timestamp - start;
        const progress = Math.min(elapsed / duration, 1);

        element.style.height = targetHeight * progress + "px";

        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          element.style.height = "auto";
          element.style.overflow = "visible";
        }
      }

      requestAnimationFrame(step);
    },
  };
}

// Export for use in other modules
window.Utils = Utils;

/**
 * Renderer Process Logger
 * Handles console and file-based logging for the renderer process
 */
class RendererLogger {
  constructor() {
    this.logLevels = {
      DEBUG: 0,
      INFO: 1,
      WARN: 2,
      ERROR: 3,
      FATAL: 4
    };
    
    this.currentLevel = this.logLevels.DEBUG; // Show all logs in development
    this.maxConsoleHistory = 1000;
    this.logHistory = [];
    
    // Setup error handling
    this.setupErrorHandling();
  }
  
  setupErrorHandling() {
    // Catch unhandled errors
    window.addEventListener('error', (event) => {
      this.error(`Unhandled error: ${event.error?.message}`, 'WINDOW');
      this.error(`Stack: ${event.error?.stack}`, 'WINDOW');
    });
    
    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error(`Unhandled promise rejection: ${event.reason}`, 'PROMISE');
    });
  }
  
  formatMessage(level, message, context = 'RENDERER') {
    const timestamp = new Date().toISOString();
    return `${timestamp} [${level}] [${context}] ${message}`;
  }
  
  addToHistory(level, message, context) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      context,
      message
    };
    
    this.logHistory.push(logEntry);
    
    // Maintain max history size
    if (this.logHistory.length > this.maxConsoleHistory) {
      this.logHistory.shift();
    }
  }
  
  log(level, message, context = 'RENDERER') {
    if (this.logLevels[level] < this.currentLevel) {
      return; // Skip if below current log level
    }
    
    const formattedMessage = this.formatMessage(level, message, context);
    this.addToHistory(level, message, context);
    
    // Send to main process if available
    if (window.electronAPI && window.electronAPI.log) {
      window.electronAPI.log(level.toLowerCase(), message, context);
    }
    
    // Console output with colors
    switch (level) {
      case 'DEBUG':
        console.log(`%c${formattedMessage}`, 'color: #3498db'); // Blue
        break;
      case 'INFO':
        console.log(`%c${formattedMessage}`, 'color: #2ecc71'); // Green
        break;
      case 'WARN':
        console.warn(`%c${formattedMessage}`, 'color: #f39c12'); // Orange
        break;
      case 'ERROR':
        console.error(`%c${formattedMessage}`, 'color: #e74c3c'); // Red
        break;
      case 'FATAL':
        console.error(`%c${formattedMessage}`, 'color: #9b59b6; font-weight: bold'); // Purple bold
        break;
      default:
        console.log(formattedMessage);
    }
  }
  
  debug(message, context = 'RENDERER') {
    this.log('DEBUG', message, context);
  }
  
  info(message, context = 'RENDERER') {
    this.log('INFO', message, context);
  }
  
  warn(message, context = 'RENDERER') {
    this.log('WARN', message, context);
  }
  
  error(message, context = 'RENDERER') {
    this.log('ERROR', message, context);
  }
  
  fatal(message, context = 'RENDERER') {
    this.log('FATAL', message, context);
  }
  
  // Utility methods
  setLogLevel(level) {
    if (this.logLevels.hasOwnProperty(level)) {
      this.currentLevel = this.logLevels[level];
      this.info(`Log level set to ${level}`, 'LOGGER');
    } else {
      this.warn(`Invalid log level: ${level}`, 'LOGGER');
    }
  }
  
  getLogHistory() {
    return [...this.logHistory];
  }
  
  clearHistory() {
    this.logHistory = [];
    this.info('Log history cleared', 'LOGGER');
  }
  
  exportLogs() {
    const logs = this.getLogHistory().map(entry => 
      `${entry.timestamp} [${entry.level}] [${entry.context}] ${entry.message}`
    ).join('\n');
    
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `renderer-logs-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
    this.info('Logs exported', 'LOGGER');
  }
}

// Create global logger instance
const logger = new RendererLogger();

// Make it globally available
window.logger = logger;

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = logger;
} 
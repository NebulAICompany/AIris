/**
 * Simple Logger for Renderer Process
 * Works within Electron's context isolation
 */
class RendererLogger {
  constructor() {
    this.isDev = navigator.userAgent.includes('Electron') && 
                 (localStorage.getItem('dev-mode') === 'true' || window.location.search.includes('dev'));
    
    this.logLevels = {
      ERROR: 0,
      WARN: 1,
      INFO: 2,
      DEBUG: 3
    };
    
    // Set log level based on environment
    this.currentLogLevel = this.isDev ? this.logLevels.DEBUG : this.logLevels.INFO;
  }
  
  formatMessage(level, message, context = '') {
    const timestamp = new Date().toISOString();
    const contextStr = context ? ` [${context}]` : '';
    return `${timestamp} [${level}]${contextStr} ${message}`;
  }
  
  log(level, message, context = '') {
    if (this.logLevels[level] > this.currentLogLevel) {
      return;
    }
    
    const formattedMessage = this.formatMessage(level, message, context);
    
    // Use appropriate console method
    const consoleMethod = level === 'ERROR' ? 'error' : 
                         level === 'WARN' ? 'warn' : 
                         level === 'INFO' ? 'info' : 'log';
    
    // Add colors in development
    if (this.isDev) {
      const colors = {
        ERROR: 'color: #ff4444; font-weight: bold;',
        WARN: 'color: #ffaa00; font-weight: bold;',
        INFO: 'color: #0099ff; font-weight: bold;',
        DEBUG: 'color: #888888;'
      };
      
      console[consoleMethod](`%c${formattedMessage}`, colors[level] || '');
    } else {
      console[consoleMethod](formattedMessage);
    }
  }
  
  error(message, context = '') {
    this.log('ERROR', message, context);
  }
  
  warn(message, context = '') {
    this.log('WARN', message, context);
  }
  
  info(message, context = '') {
    this.log('INFO', message, context);
  }
  
  debug(message, context = '') {
    this.log('DEBUG', message, context);
  }
}

// Create global logger instance
window.logger = new RendererLogger(); 
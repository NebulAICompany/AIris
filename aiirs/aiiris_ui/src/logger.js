const fs = require('fs');
const path = require('path');
const { app } = require('electron');

class Logger {
  constructor() {
    this.logLevels = {
      ERROR: 0,
      WARN: 1,
      INFO: 2,
      DEBUG: 3
    };
    
    // Set log level based on environment
    this.currentLogLevel = process.argv.includes('--dev') ? this.logLevels.DEBUG : this.logLevels.INFO;
    
    // Create logs directory
    const userDataPath = app?.getPath('userData') || path.join(__dirname, '../../logs');
    this.logDir = path.join(userDataPath, 'logs');
    
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
    }
    
    this.logFile = path.join(this.logDir, 'airis-electron.log');
    this.errorLogFile = path.join(this.logDir, 'airis-errors.log');
    
    // Rotate logs if they get too large (10MB)
    this.rotateLogsIfNeeded();
    
    this.info('Logger initialized');
  }
  
  rotateLogsIfNeeded() {
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    [this.logFile, this.errorLogFile].forEach(file => {
      if (fs.existsSync(file)) {
        const stats = fs.statSync(file);
        if (stats.size > maxSize) {
          const backupFile = `${file}.${Date.now()}.old`;
          fs.renameSync(file, backupFile);
          
          // Keep only the last 5 backup files
          const dir = path.dirname(file);
          const baseName = path.basename(file);
          const backupFiles = fs.readdirSync(dir)
            .filter(f => f.startsWith(baseName) && f.endsWith('.old'))
            .sort()
            .reverse();
          
          if (backupFiles.length > 5) {
            backupFiles.slice(5).forEach(f => {
              fs.unlinkSync(path.join(dir, f));
            });
          }
        }
      }
    });
  }
  
  formatMessage(level, message, context = '') {
    const timestamp = new Date().toISOString();
    const contextStr = context ? ` [${context}]` : '';
    return `${timestamp} [${level}]${contextStr} ${message}`;
  }
  
  writeToFile(message, isError = false) {
    const file = isError ? this.errorLogFile : this.logFile;
    try {
      fs.appendFileSync(file, message + '\n');
    } catch (err) {
      console.error('Failed to write to log file:', err);
    }
  }
  
  log(level, message, context = '') {
    if (this.logLevels[level] > this.currentLogLevel) {
      return;
    }
    
    const formattedMessage = this.formatMessage(level, message, context);
    
    // Always write to file
    this.writeToFile(formattedMessage, level === 'ERROR');
    
    // Console output with colors in development
    if (process.argv.includes('--dev')) {
      const colors = {
        ERROR: '\x1b[31m',    // Red
        WARN: '\x1b[33m',     // Yellow
        INFO: '\x1b[36m',     // Cyan
        DEBUG: '\x1b[90m'     // Gray
      };
      const reset = '\x1b[0m';
      
      console.log(`${colors[level] || ''}${formattedMessage}${reset}`);
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

// Export singleton instance
const logger = new Logger();
module.exports = logger; 
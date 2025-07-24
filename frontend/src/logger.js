/**
 * Main Process Logger for Electron App
 * Handles file-based logging for the main process
 */

const { app } = require('electron');
const fs = require('fs');
const path = require('path');
const os = require('os');

class Logger {
  constructor() {
    this.logDir = path.join(app.getPath('userData'), 'logs');
    this.logFile = path.join(this.logDir, 'main.log');
    this.errorFile = path.join(this.logDir, 'main-errors.log');
    this.maxLogSize = 10 * 1024 * 1024; // 10MB
    this.maxBackups = 5;
    
    this.setupLogDirectory();
  }
  
  setupLogDirectory() {
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
    }
  }
  
  formatMessage(level, message, context = 'MAIN') {
    const timestamp = new Date().toISOString();
    return `${timestamp} [${level}] [${context}] ${message}${os.EOL}`;
  }
  
  writeToFile(filePath, content) {
    try {
      // Check file size and rotate if needed
      if (fs.existsSync(filePath)) {
        const stats = fs.statSync(filePath);
        if (stats.size > this.maxLogSize) {
          this.rotateLogFile(filePath);
        }
      }
      
      fs.appendFileSync(filePath, content, { encoding: 'utf8' });
    } catch (error) {
      console.error('Failed to write to log file:', error);
    }
  }
  
  rotateLogFile(filePath) {
    try {
      // Move existing backups
      for (let i = this.maxBackups - 1; i >= 1; i--) {
        const oldPath = `${filePath}.${i}`;
        const newPath = `${filePath}.${i + 1}`;
        
        if (fs.existsSync(oldPath)) {
          if (i === this.maxBackups - 1) {
            fs.unlinkSync(oldPath); // Delete oldest backup
          } else {
            fs.renameSync(oldPath, newPath);
          }
        }
      }
      
      // Move current log to .1
      if (fs.existsSync(filePath)) {
        fs.renameSync(filePath, `${filePath}.1`);
      }
    } catch (error) {
      console.error('Failed to rotate log file:', error);
    }
  }
  
  debug(message, context = 'MAIN') {
    const formattedMessage = this.formatMessage('DEBUG', message, context);
    console.log(`\x1b[36m${formattedMessage.trim()}\x1b[0m`); // Cyan
    this.writeToFile(this.logFile, formattedMessage);
  }
  
  info(message, context = 'MAIN') {
    const formattedMessage = this.formatMessage('INFO', message, context);
    console.log(`\x1b[32m${formattedMessage.trim()}\x1b[0m`); // Green
    this.writeToFile(this.logFile, formattedMessage);
  }
  
  warn(message, context = 'MAIN') {
    const formattedMessage = this.formatMessage('WARN', message, context);
    console.warn(`\x1b[33m${formattedMessage.trim()}\x1b[0m`); // Yellow
    this.writeToFile(this.logFile, formattedMessage);
  }
  
  error(message, context = 'MAIN') {
    const formattedMessage = this.formatMessage('ERROR', message, context);
    console.error(`\x1b[31m${formattedMessage.trim()}\x1b[0m`); // Red
    this.writeToFile(this.logFile, formattedMessage);
    this.writeToFile(this.errorFile, formattedMessage);
  }
  
  fatal(message, context = 'MAIN') {
    const formattedMessage = this.formatMessage('FATAL', message, context);
    console.error(`\x1b[35m${formattedMessage.trim()}\x1b[0m`); // Magenta
    this.writeToFile(this.logFile, formattedMessage);
    this.writeToFile(this.errorFile, formattedMessage);
  }
}

// Export singleton instance
module.exports = new Logger(); 
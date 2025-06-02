# AIris Desktop - AI-Powered Financial Document Processing

A modern Electron.js desktop application for AIris, providing an intuitive interface for AI-powered financial document analysis and querying.

## Features

- 🤖 **AI Chat Interface** - Interactive chat with your financial documents
- 📄 **Document Upload** - Drag & drop support for PDF, DOCX, XLSX, and images
- 📁 **File Management** - Organize and manage your uploaded documents
- 📊 **Analytics Dashboard** - Monitor system performance and usage
- 🎨 **Modern UI** - Clean, responsive design with dark/light themes
- 🔒 **Secure** - Context isolation and secure IPC communication

## Prerequisites

Before running the application, ensure you have:

1. **Node.js** (v18 or higher)
2. **AIris Backend** running on `http://localhost:8000`
   - The FastAPI backend should be started from the `aiiris_backend` directory
   - Run: `python main.py` or `uvicorn main:app --reload`

## Installation

1. **Clone or navigate to the project directory:**

   ```bash
   cd c:\Users\ASUS\Desktop\Coding\Python\vectorrag\aiirs\claude
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

## Running the Application

### Development Mode (with DevTools)

```bash
npm run dev
```

### Production Mode

```bash
npm start
```

### Building for Distribution

```bash
npm run build
```

## Project Structure

```
airis-desktop/
├── src/
│   ├── main.js              # Main Electron process
│   ├── preload.js           # Secure IPC preload script
│   └── renderer/
│       ├── index.html       # Main application UI
│       ├── scripts/
│       │   ├── app.js       # Main application logic
│       │   ├── components.js # UI components and interactions
│       │   ├── api.js       # Backend API service
│       │   └── utils.js     # Utility functions
│       └── styles/
│           ├── main.css     # Core styles and themes
│           └── components.css # Component-specific styles
├── assets/                  # Application icons and images
├── .vscode/
│   └── tasks.json          # VS Code development tasks
└── package.json            # Project configuration
```

## Backend Integration

The application connects to the AIris FastAPI backend with the following endpoints:

- `POST /api/query` - Submit AI queries
- `POST /api/upload` - Upload documents
- `GET /` - Health check and Prometheus metrics

### Backend Requirements

Ensure your AIris backend is running with these features:

- Document processing (PDF, DOCX, Excel, images)
- Vector store with FAISS
- OpenAI GPT-4o integration
- Prometheus metrics endpoint

## Usage

1. **Start the Backend:** First, ensure the AIris backend is running on localhost:8000
2. **Launch the App:** Run `npm run dev` for development or `npm start` for production
3. **Upload Documents:** Use the Upload tab to add your financial documents
4. **Chat with AI:** Switch to the Chat tab and ask questions about your documents
5. **Monitor Analytics:** View system metrics in the Analytics tab

## Development

### Available Scripts

- `npm start` - Start the application in production mode
- `npm run dev` - Start with development features (DevTools, hot reload)
- `npm run build` - Build the application for distribution
- `npm install` - Install dependencies

### Keyboard Shortcuts

- `Ctrl/Cmd + K` - Focus chat input
- `Ctrl/Cmd + U` - Switch to upload tab
- `Ctrl/Cmd + 1-5` - Switch between tabs
- `Ctrl/Cmd + Shift + D` - Toggle dark mode
- `Ctrl/Cmd + Shift + K` - Clear chat
- `F12` - Toggle developer tools

### Development Features

When running in development mode (`npm run dev`):

- DevTools open automatically
- Hot reload enabled
- Additional debugging features

## Troubleshooting

### Common Issues

1. **"Cannot find module" error:**

   - Run `npm install` to ensure all dependencies are installed

2. **Backend connection failed:**

   - Verify the AIris backend is running on localhost:8000
   - Check the API endpoint in Settings tab

3. **File upload issues:**

   - Ensure files are in supported formats (PDF, DOCX, XLSX, images)
   - Check file size limits

4. **Application won't start:**
   - Use `npm start` or `npm run dev`, not `node main.js`
   - Check that Electron is properly installed

### Logs and Debugging

- Open DevTools with F12 or from the View menu
- Check the Console tab for JavaScript errors
- Network tab shows API request/response details

## Security

The application follows Electron security best practices:

- Context isolation enabled
- Node integration disabled in renderer
- Secure IPC communication via preload script
- No direct access to Node.js APIs from renderer

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:

- Check the troubleshooting section above
- Open an issue in the project repository
- Review console logs for error details

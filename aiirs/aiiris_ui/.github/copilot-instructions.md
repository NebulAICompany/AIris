# AIris Electron App - Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview

This is an Electron.js desktop application for AIris - an AI-powered financial document processing system that provides:

- Modern desktop interface for document upload and management
- Real-time chat interface for querying financial documents
- Integration with FastAPI backend (running on localhost:8000)
- File processing status monitoring
- Professional UI with dark/light themes

## Key Technologies

- **Electron.js** - Desktop application framework
- **HTML/CSS/JavaScript** - Frontend technologies
- **Axios** - HTTP client for backend communication
- **Marked.js** - Markdown rendering for responses
- **Highlight.js** - Syntax highlighting

## Backend Integration

The app connects to a FastAPI backend with these endpoints:

- `POST /api/query` - Submit queries to the AI system
- `POST /api/upload` - Upload documents for processing
- `GET /` - Prometheus metrics

## Code Style Guidelines

- Use modern JavaScript (ES6+)
- Follow Electron security best practices
- Implement responsive design
- Use consistent naming conventions
- Add proper error handling
- Include loading states and user feedback

## Security Considerations

- Enable context isolation in renderer processes
- Disable node integration in renderer
- Use IPC for secure communication between main and renderer
- Validate all user inputs before sending to backend

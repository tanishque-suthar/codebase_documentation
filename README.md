# BloomDocs - Code Documentation Generator

A full-stack application that generates comprehensive documentation for code snippets, files, and entire GitHub repositories using Google's Gemma AI model with intelligent file prioritization.

## ✨ Features

- **Multi-Input Support**: Generate documentation from:
  - Direct code paste
  - File uploads
  - GitHub repositories
- **AI-Powered Analysis**: Smart file prioritization for GitHub repositories
- **Professional Output**: Formatted Markdown documentation with syntax highlighting
- **Universal Download System**: Download documentation as .md files with intelligent naming
- **Modern UI**: Beautiful homepage with glassmorphism design and smooth animations
- **Real-time Processing**: Live loading indicators and status updates

## 🏗️ Project Structure

```
codebase_docApp/
├── backend/                 # FastAPI server
│   ├── main.py             # Application entry point
│   ├── middleware.py       # CORS configuration
│   ├── config/             # Application settings
│   ├── models/             # Pydantic schemas
│   ├── routers/            # API endpoints
│   │   ├── docs.py         # Code/file documentation
│   │   ├── github.py       # GitHub repository analysis
│   │   └── download.py     # Universal download system
│   ├── services/           # Business logic
│   │   ├── ai_service.py   # AI documentation generation
│   │   └── github_service.py # GitHub API integration with caching
│   └── utils/              # Helper functions
└── frontend/docapp/        # React + Vite application
    ├── src/
    │   ├── components/     # React components
    │   │   ├── Homepage.jsx        # Landing page
    │   │   ├── DocumentationApp.jsx # Main app
    │   │   ├── CodeInput.jsx       # Code paste interface
    │   │   ├── FileUpload.jsx      # File upload interface
    │   │   ├── GitHubInput.jsx     # GitHub repo interface
    │   │   └── DocumentationDisplay.jsx # Output display
    │   ├── services/       # API integration
    │   └── App.css         # Comprehensive styling
    └── package.json
```

## 🚀 Quick Start

### Backend Setup

1. **Create virtual environment(optional but recommended):**
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # macOS/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Create a `.env` file in the backend directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   PORT=8000
   HOST=0.0.0.0
   GITHUB_TOKEN=your_github_token_here  # Optional, for higher rate limits
   ```

4. **Start the server:**
   ```bash
   uvicorn main:app --reload
   # or
   python main.py
   ```

   Server will be available at: http://localhost:8000
   API documentation at: http://localhost:8000/api-docs

### Frontend Setup

1. **Navigate to frontend:**
   ```bash
   cd frontend/docapp
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

   Frontend will be available at: http://localhost:5173

## 🎯 Usage Guide

### 1. **Code Input Method**
- Paste any code snippet directly into the text area
- Supports all programming languages
- Real-time validation and processing

### 2. **File Upload Method**
- Upload code files (up to 10MB)
- Supported formats: `.js`, `.ts`, `.py`, `.java`, and more
- Automatic file type detection and processing

### 3. **GitHub Repository Method**
- Enter any public GitHub repository URL
- AI automatically prioritizes important files
- Configurable file limit (1-50 files, recommended: 10-20)
- Smart filtering excludes build artifacts and dependencies, which result in efficient token usage and faster documentation generation
- Repository language detection for better analysis

## 🔧 API Endpoints

### Documentation Generation

#### `POST /docs/gen`
Generate documentation from code text.

**Request:**
```json
{
  "code": "def hello_world():\n    print('Hello, world!')",
  "isBase64": false
}
```

**Response:**
```json
{
  "markdown": "# Documentation\n\n## Overview\n\nThis function prints a greeting..."
}
```

#### `POST /docs/from-upload`
Generate documentation from uploaded file.

**Request:** Multipart form with `file` field

**Response:**
```json
{
  "markdown": "# File Documentation\n\n..."
}
```

#### `POST /docs/from-github`
Generate documentation from GitHub repository.

**Request:**
```json
{
  "github_url": "https://github.com/owner/repository",
  "max_files": 10
}
```

**Response:**
```json
{
  "markdown": "# Repository Documentation\n\n..."
}
```

### Download System

#### `POST /docs/download`
Universal download endpoint for pre-generated documentation.

**Request:**
```json
{
  "markdown_content": "# My Documentation\n\nContent here...",
  "filename_prefix": "my_project_docs",
  "source_type": "github"
}
```

**Response:** Markdown file download with timestamp

### Health Check

#### `GET /health`
Check service status.

**Response:**
```json
{
  "status": "healthy",
  "service": "Code Documentation API"
}
```

## 🧠 AI Features

### Smart Repository Analysis
- **Language Detection**: Automatically identifies primary programming languages
- **File Prioritization**: AI ranks files by documentation importance (1-5 scale)
- **Intelligent Filtering**: Skips build artifacts, dependencies, and temporary files
- **Optimized API Usage**: Efficient GitHub API usage with caching and rate limiting

### Documentation Quality
- **Contextual Analysis**: Understands project structure and relationships
- **Comprehensive Output**: Generates project overview, architecture, API reference, and setup instructions
- **Multiple Formats**: Supports various programming languages and frameworks
- **Professional Formatting**: Clean, readable Markdown with proper structure

## 🎨 UI/UX Features

### Modern Design
- **Glassmorphism Homepage**: Beautiful landing page with gradient backgrounds
- **Smooth Animations**: Floating elements and loading indicators
- **Tab Navigation**: Easy switching between input methods

### User Experience
- **Real-time Feedback**: Loading states and progress indicators
- **Error Handling**: Clear error messages and recovery suggestions
- **Auto-scroll**: Automatic navigation to generated documentation
- **Download Integration**: One-click download with intelligent file naming

## ⚙️ Technical Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Google Gemma AI**: gemma-3-12b-it for documentation generation
- **Pydantic**: Data validation and settings management
- **Requests**: GitHub API integration
- **Python-multipart**: File upload handling
- **Uvicorn**: ASGI server

### Frontend
- **React 19**: Latest React with modern hooks
- **Vite**: Fast build tool and development server
- **React Router**: Client-side routing
- **Marked.js**: Markdown parsing and rendering
- **Highlight.js**: Syntax highlighting for code blocks
- **Font Awesome**: Icon library

### DevOps & Deployment
- **Render**: Backend hosting (https://codebase-documentation.onrender.com)
- **Vercel**: Frontend hosting (https://codebase-documentation.vercel.app/)
- **Environment Variables**: Secure configuration management
- **CORS**: Properly configured cross-origin requests

## 🛠️ Development

### Building for Production

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd frontend/docapp
npm install
npm run build
npm run preview
```

### Code Quality
- **ESLint**: JavaScript/React linting
- **Type Safety**: Proper TypeScript-style prop validation
- **Modular Architecture**: Clean separation of concerns
- **Error Boundaries**: Comprehensive error handling

## 🌐 Browser Compatibility

Tested and optimized for:
- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 📝 Examples

### Base64 Encoding
For complex code with special characters:

```javascript
const code = document.getElementById('codeInput').value;
const encodedCode = btoa(code);

fetch('/docs/gen', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code: encodedCode,
    isBase64: true
  })
});
```

### GitHub Repository Analysis
```bash
https://github.com/facebook/react
https://github.com/microsoft/vscode
https://github.com/nodejs/node
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines
- Follow existing code style and patterns
- Add comments for complex logic
- Test new features thoroughly
- Update documentation as needed

---

For support or questions, please open an issue on GitHub.
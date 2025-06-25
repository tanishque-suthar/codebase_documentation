# Code Documentation API

A full-stack application that generates documentation for code snippets using Google's Gemma AI model.

## Features

- Generate documentation from code in any programming language
- Handle complex multiline code via base64 encoding
- Return formatted Markdown documentation
- Download documentation as .md files
- Upload code files for documentation generation
- Modern React UI with code input and file upload options
- Syntax-highlighted documentation preview

## Project Structure

- **Backend**: FastAPI server that processes code and generates documentation
- **Frontend**: React application with Vite for a responsive user interface

## Backend Setup

1. Set up a virtual environment:
   ```
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Create a `.env` file in the backend directory
   - Add the following variables:
     ```
     GOOGLE_API_KEY=your_google_api_key
     PORT=8000
     HOST=0.0.0.0
     ```

## Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend/docapp
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```

4. The frontend will be available at: http://localhost:5173

## Running the Application

### Backend
Start the API server:
```
uvicorn main:app --reload
```

Or run directly:
```
python main.py
```

Once the server is running, you can access the Swagger UI for API documentation at: /api-docs

### Frontend
Start the frontend development server:
```
cd frontend/docapp
npm run dev
```

## UI Components

The frontend includes the following main components:

- **CodeInput**: Text area for pasting code snippets
- **FileUpload**: File upload interface for code files
- **DocumentationDisplay**: Displays generated documentation with syntax highlighting

## API Endpoints

### `POST /docs/gen`

Generates documentation for provided code and returns it as JSON.

**Request Body:**
```json
{
  "code": "def hello_world():\n    print('Hello, world!')",
  "isBase64": false
}
```

**Response:**
```json
{
  "markdown": "## Overview\n\nThis code defines a function that prints 'Hello, world!'...",
}
```

### `POST /docs/from-upload`

Generates documentation from an uploaded file containing code.

**Request:**
- `file`: Upload a text file containing code.

**Response:**
```json
{
  "markdown": "## Overview\n\nThis code defines a function that prints 'Hello, world!'...",
}
```

### `POST /docs/download`

Generates documentation and returns it as a downloadable .md file.

**Request:**
- `file`: Upload a text file containing code.
- OR
- `code`: Provide code directly in the request body.

**Response:** Markdown file download

## Base64 Encoding

For complex multiline code with special characters, use base64 encoding:

```javascript
// Frontend example
const code = document.getElementById('codeInput').value;
const encodedCode = btoa(code);  // Base64 encode

fetch('/docs/gen', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code: encodedCode,
    isBase64: true
  })
})
.then(response => response.json())
.then(data => {
  console.log(data.markdown);
});
```

## Technical Details

Backend:
- Uses FastAPI framework for the REST API
- Leverages Google's Gemma 3 12B IT model for documentation generation
- Implements proper error handling for all endpoints
- Includes temporary file management for downloads
- Supports file uploads for documentation generation

Frontend:
- Built with React + Vite for a fast, modern UI
- Uses marked.js for Markdown rendering
- Highlight.js for syntax highlighting code blocks
- Responsive design for desktop and mobile use
- Clean tab-based interface for code input and file upload options

## Development

### Building for Production

#### Backend
```
cd backend
pip install -r requirements.txt
```

#### Frontend
```
cd frontend/docapp
npm install
npm run build
```

The production build will be available in the `frontend/docapp/dist` directory.

### Browser Compatibility

The application has been tested and works on:
- Chrome (latest)
- Firefox (latest)
- Edge (latest)
- Safari (latest)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

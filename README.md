# Code Documentation API Backend

A FastAPI backend that generates documentation for code snippets using Google's Gemma AI model.

## Features

- Generate documentation from code in any programming language
- Handle complex multiline code via base64 encoding
- Return formatted Markdown documentation
- Download documentation as .md files

## Setup

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

## Running the API

Start the API server:
```
uvicorn main:app --reload
```

Or run directly:
```
python main.py
```

## API Endpoints

### `POST /document`

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

### `POST /document/download`

Generates documentation and returns it as a downloadable .md file.

**Request Body:** Same as `/document` endpoint

**Response:** Markdown file download

## Base64 Encoding

For complex multiline code with special characters, use base64 encoding:

```javascript
// Frontend example
const code = document.getElementById('codeInput').value;
const encodedCode = btoa(code);  // Base64 encode

fetch('/document', {
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

- Uses FastAPI framework for the REST API
- Leverages Google's Gemma 3 12B IT model for documentation generation
- Implements proper error handling for all endpoints
- Includes temporary file management for downloads

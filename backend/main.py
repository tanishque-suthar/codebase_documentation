from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn
import base64
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
from typing import Optional
from google import genai
from google.genai import types
import os
from tempfile import NamedTemporaryFile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Document AI App", 
              description="API for processing documents with AI",
              version="0.1.0")

# Initialize Google AI client
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    
client = genai.Client(api_key=api_key)

# Define request model
class CodeDocumentationRequest(BaseModel):
    code: str
    isBase64: bool = False  # Flag to indicate if code is base64 encoded
    
    class Config:
        schema_extra = {
            "example": {
                "code": "def hello_world():\n    print('Hello, world!')",
                "isBase64": False
            }
        }

# Define response model
class DocumentationResponse(BaseModel):
    markdown: str

@app.get("/")
async def root():
    return {
        "message": "Welcome to Code Documentation API",
        "usage": {
            "endpoint": "/document",
            "method": "POST",
            "body": {
                "code": "Your code here (any programming language)",
                "isBase64": "Optional boolean (default: false) to indicate if the code is base64 encoded"
            }
        },
        "example": {
            "code": "def hello_world():\n    print('Hello, world!')",
            "isBase64": False
        }
    }

@app.post("/document", response_model=DocumentationResponse)
async def generate_documentation(request: CodeDocumentationRequest):
    try:
        if not request.code:
            raise HTTPException(status_code=400, detail="Code cannot be empty")
        
        # Decode base64 if the flag is set
        try:
            if request.isBase64:
                code = base64.b64decode(request.code).decode('utf-8')
            else:
                code = request.code
        except Exception as decode_error:
            raise HTTPException(status_code=400, detail=f"Error decoding base64: {str(decode_error)}")
        print(f"Decoded code:\n{code}\n")     
        # Create a prompt for documentation generation with consistent formatting
        prompt = (
            "Generate concise brief documentation for the following code:\n\n"
            "```\n"
            f"{code}\n"
            "```\n\n"
            "Include only these sections:\n"
            "1. Overview of what the code does\n"
            "2. Description of functions with parameters and return values\n\n"
            "Format the documentation as Markdown."
        )
        print(f"Generated prompt for AI:\n{prompt}\n")
        
        # Generation configuration
        gen_config = types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=1024
        )
        
        # Generate documentation with AI
        try:
            response = client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=gen_config
            )
            
            return DocumentationResponse(
                markdown=response.text
            )
        except Exception as api_error:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating documentation: {str(api_error)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/document/download")
async def download_documentation(request: CodeDocumentationRequest):
    try:
        # Generate documentation using the same logic as /document endpoint
        doc_response = await generate_documentation(request)
        
        # Create a timestamped filename for the download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_filename = f"code_documentation_{timestamp}.md"
        
        # Create a temporary file with the markdown content
        with NamedTemporaryFile(delete=False, mode='w', suffix='.md') as temp_file:
            temp_file.write(doc_response.markdown)
            temp_path = temp_file.name
        
        # Return the file as a download
        return FileResponse(
            path=temp_path,
            filename=doc_filename,
            media_type='text/markdown',
            background=BackgroundTask(lambda: os.unlink(temp_path))  # Delete file after download
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add this if you want to run directly using python (not needed for uvicorn command line)
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
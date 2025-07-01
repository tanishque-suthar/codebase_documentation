from fastapi import FastAPI
import uvicorn
from middleware import setup_cors_middleware

# Import configuration
from config.settings import settings

# Import models and services
from models.schemas import CodeDocumentationRequest, DocumentationResponse, GitHubDocumentationRequest, DownloadRequest
from services.ai_service import AIDocumentationService

# Import routers
from routers import docs, github, download

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url=settings.API_DOCS_URL
)

# Apply CORS middleware
app = setup_cors_middleware(app)

# Include routers
app.include_router(docs.router)
app.include_router(github.router)
app.include_router(download.router)

# Initialize AI service
ai_service = AIDocumentationService()

@app.get("/")
async def root():
    return {
        "message": "Welcome to Code Documentation API",
        "usage": {
            "text_input": {
                "endpoint": "/docs/gen",
                "method": "POST",
                "body": {
                    "code": "Your code here (any programming language)",
                    "isBase64": "Optional boolean (default: false) to indicate if the code is base64 encoded"
                }
            },
            "file_upload": {
                "endpoint": "/docs/from-upload",
                "method": "POST",
                "form": "file: Upload a text file containing code"
            },
            "github_repo": {
                "endpoint": "/docs/from-github",
                "method": "POST",
                "body": {
                    "github_url": "GitHub repository URL",
                    "max_files": "Optional number (default: 10) to limit files processed"
                }
            },
            "download": {
                "endpoint": "/docs/download",
                "method": "POST",
                "body": {
                    "markdown_content": "Pre-generated markdown content from other endpoints",
                    "filename_prefix": "Optional filename prefix (default: 'documentation')",
                    "source_type": "Optional source indicator ('code', 'file', 'github')"
                },
                "description": "Download pre-generated documentation as .md file"
            }
        },
        "example": {
            "code": "def hello_world():\n    print('Hello, world!')",
            "isBase64": False
        },
        "workflow": "1. Generate docs using any endpoint → 2. Frontend stores markdown → 3. Download using stored content"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "service": "Code Documentation API"}

# Add this if you want to run directly using python (not needed for uvicorn command line)
if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
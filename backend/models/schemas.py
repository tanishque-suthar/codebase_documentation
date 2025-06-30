from pydantic import BaseModel
from typing import Optional


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


class DocumentationResponse(BaseModel):
    markdown: str


class GitHubDocumentationRequest(BaseModel):
    github_url: str
    max_files: int = 10  # Limit files processed for MVP
    
    class Config:
        schema_extra = {
            "example": {
                "github_url": "https://github.com/owner/repository",
                "max_files": 10
            }
        }


class DownloadRequest(BaseModel):
    markdown_content: str
    filename_prefix: str = "documentation"
    source_type: Optional[str] = "code"  # "code", "file", "github"
    
    class Config:
        schema_extra = {
            "example": {
                "markdown_content": "# My Documentation\n\nThis is the generated documentation...",
                "filename_prefix": "my_project_docs",
                "source_type": "github"
            }
        }

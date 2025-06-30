import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # App Configuration
    APP_TITLE: str = "Document AI App"
    APP_DESCRIPTION: str = "API for processing documents with AI"
    APP_VERSION: str = "0.1.0"
    API_DOCS_URL: str = "/api-docs"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # AI Service Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gemma-3-12b-it")
    
    # GitHub API Configuration
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_TIMEOUT: int = 30
    
    # File Processing Configuration
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_EXTENSIONS: set = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.kt', '.scala', '.swift', '.dart', '.r', '.sql', '.md', '.txt'}
    
    # Repository Processing Configuration
    DEFAULT_MAX_FILES: int = 10
    MAX_REPOSITORY_DEPTH: int = 8
    SKIP_DIRECTORIES: set = {
        '.git', '.github', 'node_modules', '__pycache__', '.vscode', 
        'dist', 'build', 'target', 'out', '.idea', 'logs', 'tmp', 
        '.next', '.nuxt', 'coverage', '.pytest_cache', 'vendor',
        '.env', '.venv', 'venv', 'env'
    }
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    CORS_METHODS: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: list = ["*"]
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate critical configuration settings"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        return True

# Create settings instance
settings = Settings()

# Validate configuration on import
try:
    settings.validate_config()
except ValueError as e:
    print(f"Configuration validation failed: {e}")
    # Don't raise the error here to allow the app to start for testing

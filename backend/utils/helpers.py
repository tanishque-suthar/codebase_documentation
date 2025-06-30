import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from tempfile import NamedTemporaryFile
from config.settings import settings

def decode_base64_content(content: str, is_base64: bool = False) -> str:
    """
    Decode base64 content if needed
    
    Args:
        content: The content string
        is_base64: Whether the content is base64 encoded
        
    Returns:
        Decoded content string
        
    Raises:
        ValueError: If base64 decoding fails
    """
    if not is_base64:
        return content
    
    try:
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decode base64 content: {str(e)}")

def encode_to_base64(content: bytes) -> str:
    """
    Encode bytes content to base64 string
    
    Args:
        content: Bytes content to encode
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(content).decode('utf-8')

def validate_text_content(content: bytes) -> bool:
    """
    Validate that content can be decoded as text
    
    Args:
        content: Bytes content to validate
        
    Returns:
        True if content is valid text, False otherwise
    """
    try:
        content.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False

def generate_timestamp_filename(prefix: str, extension: str = ".md") -> str:
    """
    Generate a timestamped filename
    
    Args:
        prefix: Filename prefix
        extension: File extension (default: .md)
        
    Returns:
        Timestamped filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{extension}"

def create_temp_file(content: str, suffix: str = '.md', encoding: str = 'utf-8') -> str:
    """
    Create a temporary file with content
    
    Args:
        content: Content to write to file
        suffix: File suffix/extension
        encoding: Text encoding
        
    Returns:
        Path to temporary file
    """
    with NamedTemporaryFile(delete=False, mode='w', suffix=suffix, encoding=encoding) as temp_file:
        temp_file.write(content)
        return temp_file.name

def is_code_file(filename: str, allowed_extensions: Optional[set] = None) -> bool:
    """
    Check if file is a code file based on extension
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions (optional)
        
    Returns:
        True if file is a code file, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = settings.ALLOWED_FILE_EXTENSIONS
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in allowed_extensions

def should_skip_directory(dirname: str, skip_dirs: Optional[set] = None) -> bool:
    """
    Check if directory should be skipped during traversal
    
    Args:
        dirname: Name of the directory
        skip_dirs: Set of directories to skip (optional)
        
    Returns:
        True if directory should be skipped, False otherwise
    """
    if skip_dirs is None:
        from config.settings import settings
        skip_dirs = settings.SKIP_DIRECTORIES
    
    return dirname.lower() in skip_dirs

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def clean_github_url(url: str) -> str:
    """
    Clean and normalize GitHub URL
    
    Args:
        url: GitHub URL to clean
        
    Returns:
        Cleaned URL
    """
    return url.rstrip('/')

def extract_repo_name_from_url(url: str) -> str:
    """
    Extract repository name from GitHub URL for filename generation
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Repository name in format owner_repo
    """
    from services.github_service import parse_github_url
    
    try:
        repo_info = parse_github_url(url)
        return f"{repo_info['owner']}_{repo_info['repo']}"
    except Exception:
        # Fallback: try to extract from URL directly
        parts = url.rstrip('/').split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}_{parts[-1]}"
        return "unknown_repo"

def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing unsafe characters
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Remove/replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove consecutive underscores and trim
    while '__' in filename:
        filename = filename.replace('__', '_')
    
    return filename.strip('_')

def get_file_language(filename: str) -> str:
    """
    Determine programming language from file extension
    
    Args:
        filename: Name of the file
        
    Returns:
        Programming language name
    """
    ext_to_lang = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript (React)',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript (React)',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.cs': 'C#',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.go': 'Go',
        '.rs': 'Rust',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.swift': 'Swift',
        '.dart': 'Dart',
        '.r': 'R',
        '.sql': 'SQL',
        '.md': 'Markdown',
        '.txt': 'Text'
    }
    
    file_ext = Path(filename).suffix.lower()
    return ext_to_lang.get(file_ext, 'Unknown')

def truncate_content(content: str, max_length: int = 1000) -> str:
    """
    Truncate content to maximum length for logging/display
    
    Args:
        content: Content to truncate
        max_length: Maximum length
        
    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content
    
    return content[:max_length] + "... (truncated)"

import base64
from fastapi import HTTPException, UploadFile
from typing import Optional, Dict, Any
from pathlib import Path

from config.settings import settings
from utils.helpers import (
    validate_text_content, 
    encode_to_base64, 
    is_code_file,
    get_file_language,
    format_file_size
)

class FileProcessor:
    """Utility class for processing uploaded files"""
    
    @staticmethod
    async def process_upload_file(file: UploadFile) -> Dict[str, Any]:
        """
        Process an uploaded file and return file information
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Dictionary containing file information and content
            
        Raises:
            HTTPException: If file processing fails
        """
        try:
            # Check if file was provided
            if not file or not file.filename:
                raise HTTPException(status_code=400, detail="No file provided")
            
            # Read file content
            file_content = await file.read()
            
            # Check file size
            if len(file_content) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File too large. Maximum size: {format_file_size(settings.MAX_FILE_SIZE)}"
                )
            
            # Validate that it's a text file
            if not validate_text_content(file_content):
                raise HTTPException(
                    status_code=400, 
                    detail="File could not be decoded as text. Please upload a text file containing code."
                )
            
            # Check if it's a supported code file
            if not is_code_file(file.filename):
                print(f"Warning: {file.filename} may not be a supported code file")
            
            # Get file information
            file_info = {
                "filename": file.filename,
                "size": len(file_content),
                "size_formatted": format_file_size(len(file_content)),
                "language": get_file_language(file.filename),
                "content_base64": encode_to_base64(file_content),
                "is_code_file": is_code_file(file.filename)
            }
            
            return file_info
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    @staticmethod
    def validate_file_type(filename: str) -> bool:
        """
        Validate if file type is supported
        
        Args:
            filename: Name of the file
            
        Returns:
            True if file type is supported
        """
        return is_code_file(filename)
    
    @staticmethod
    def get_supported_extensions() -> list:
        """
        Get list of supported file extensions
        
        Returns:
            List of supported extensions
        """
        return list(settings.ALLOWED_FILE_EXTENSIONS)

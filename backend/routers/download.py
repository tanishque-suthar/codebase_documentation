from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import os
from tempfile import NamedTemporaryFile
from datetime import datetime
from models.schemas import DownloadRequest
from utils.helpers import generate_timestamp_filename, create_temp_file, safe_filename

router = APIRouter(prefix="/docs", tags=["download"])

@router.post("/download")
async def download_documentation(request: DownloadRequest):
    """Universal download endpoint - accepts pre-generated markdown content"""
    try:
        # Validate markdown content
        if not request.markdown_content or not request.markdown_content.strip():
            raise HTTPException(status_code=400, detail="Markdown content cannot be empty")
        
        # Create safe filename with timestamp
        safe_prefix = safe_filename(request.filename_prefix)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_filename = f"{safe_prefix}_{timestamp}.md"
        
        print(f"Creating download file: {doc_filename}")
        print(f"Content length: {len(request.markdown_content)} characters")
        print(f"Source type: {request.source_type}")
        
        # Create temporary file with the provided markdown content
        temp_path = create_temp_file(request.markdown_content, suffix='.md', encoding='utf-8')
        
        # Return the file as download
        return FileResponse(
            path=temp_path,
            filename=doc_filename,
            media_type='text/markdown',
            background=BackgroundTask(lambda: os.unlink(temp_path))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating download: {str(e)}")

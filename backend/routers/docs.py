from fastapi import APIRouter, HTTPException, UploadFile, File
import base64
from models.schemas import CodeDocumentationRequest, DocumentationResponse
from services.ai_service import AIDocumentationService

router = APIRouter(prefix="/docs", tags=["documentation"])

# Initialize AI service
ai_service = AIDocumentationService()

@router.post("/gen", response_model=DocumentationResponse)
async def generate_documentation(request: CodeDocumentationRequest):
    """Generate documentation from code input"""
    try:
        if not request.code:
            raise HTTPException(status_code=400, detail="Code cannot be empty")
        
        # Decode base64 if the flag is set
        try:
            code = ai_service.decode_code(request.code, request.isBase64)
        except Exception as decode_error:
            raise HTTPException(status_code=400, detail=f"Error decoding base64: {str(decode_error)}")
        
        print(f"Decoded code:\n{code}\n")
        
        # Generate documentation with AI service
        try:
            ai_content = ai_service.generate_code_documentation(code)
            return DocumentationResponse(markdown=ai_content)
        except Exception as api_error:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating documentation: {str(api_error)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/from-upload", response_model=DocumentationResponse)
async def generate_docs_from_upload(file: UploadFile = File(...)):
    """Generate documentation from uploaded file"""
    try:
        # Read contents of the uploaded file
        file_content = await file.read()
        
        # Try to decode as text first to verify it's a valid text file
        try:
            # Just to verify it's readable text
            file_content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File could not be decoded as text. Please upload a text file containing code.")
        
        # Encode the file content as base64
        base64_code = base64.b64encode(file_content).decode('utf-8')
        
        # Create a request object with base64 encoded content
        request = CodeDocumentationRequest(code=base64_code, isBase64=True)
        
        # Use the existing documentation generation endpoint
        return await generate_documentation(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

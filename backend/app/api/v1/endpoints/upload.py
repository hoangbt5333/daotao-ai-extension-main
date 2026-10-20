"""
Upload endpoints
"""
from fastapi import APIRouter, File, UploadFile, Depends
import tempfile
import os
from app.models.schemas.responses import UploadResponse
from app.services.file.extractor import FileExtractor
from app.config.settings import get_settings

router = APIRouter()


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_extractor: FileExtractor = Depends(lambda: FileExtractor())
):
    """Upload and extract text from file"""
    try:
        settings = get_settings()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Extract text using file extractor service
            text = file_extractor.extract_text(temp_file_path)
            
            # Return preview of extracted text
            preview_text = text[:1000] + "..." if len(text) > 1000 else text
            
            return UploadResponse(
                success=True,
                filename=file.filename,
                text_preview=preview_text,
                full_text=text,
                message="File uploaded and processed successfully"
            )
            
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
            
    except Exception as e:
        return UploadResponse(
            success=False,
            filename=file.filename if file else "",
            text_preview="",
            full_text="",
            message=f"Upload failed: {str(e)}"
        ) 
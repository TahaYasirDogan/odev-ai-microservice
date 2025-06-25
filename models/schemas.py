from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ProcessResponse(BaseModel):
    success: bool
    message: str
    processing_id: str
    extracted_text_length: int
    chunks: Optional[List[str]] = None  # Course modunda chunk'ları direkt return et

class HealthResponse(BaseModel):
    status: str
    message: str

class ChunkData(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]

class PineconeUploadResponse(BaseModel):
    success: bool
    uploaded_count: int
    failed_count: int
    processing_id: str 
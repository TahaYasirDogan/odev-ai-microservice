from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import logging
from typing import Optional
import uuid
from datetime import datetime
from dotenv import load_dotenv

from services.pdf_processor import PDFProcessor
from services.pinecone_service import PineconeService
from models.schemas import ProcessResponse, HealthResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF Processing Microservice",
    description="PDF işleme ve Pinecone entegrasyonu için mikroservis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Railway'de tüm origin'lere izin verelim
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pdf_processor = PDFProcessor()
pinecone_service = PineconeService()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="PDF Processing Microservice is running")

@app.post("/process-pdf", response_model=ProcessResponse)
async def process_pdf(
    file: UploadFile = File(...),
    grade: str = Form(...),
    subject: str = Form(default=""),
    topic: str = Form(...),
    user_id: str = Form(...),
    mode: str = Form(default="course")  # 'course' veya 'chat'
):
    """
    PDF dosyasını işle, metni çıkar ve Pinecone'a yükle (SYNC PROCESSING)
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir")
        
        # Validate file size (5MB limit)
        file_size = 0
        temp_content = await file.read()
        file_size = len(temp_content)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="Dosya boyutu 5MB'ı geçemez")
        
        # Reset file pointer
        await file.seek(0)
        
        # Generate unique processing ID and session ID
        processing_id = str(uuid.uuid4())
        session_id = f"session_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}"
        
        logger.info(f"🚀 Processing PDF: {file.filename} for user: {user_id} (mode: {mode}, session: {session_id})")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(temp_content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text from PDF
            logger.info(f"📄 Extracting text from PDF...")
            text_content = pdf_processor.extract_text(temp_file_path)
            
            if not text_content or len(text_content.strip()) < 50:
                raise HTTPException(status_code=400, detail="PDF'den yeterli metin çıkarılamadı")
            
            logger.info(f"✅ Text extracted: {len(text_content)} characters")
            
            # Split text into chunks
            logger.info(f"🔄 Splitting text into chunks...")
            chunks = pdf_processor.split_text_into_chunks(text_content)
            logger.info(f"✅ Text split into {len(chunks)} chunks")
            
            # Prepare metadata - cleaned for better compatibility
            metadata = {
                "source": "user_upload",
                "user_id": str(user_id),  # Ensure string
                "grade": str(grade),
                "subject": str(subject) if subject else "user_content",
                "topic": str(topic),
                "filename": str(file.filename),
                "processing_id": processing_id,
                "session_id": session_id,  # 🆔 SessionId eklendi - her PDF upload unique session
                "upload_timestamp": int(datetime.now().timestamp())
            }
            
            # 🎯 Her iki modda da Pinecone'a yükle (course mode için chunk'ları da return et)
            logger.info(f"🚀 {mode.capitalize()} mode: Uploading {len(chunks)} chunks to Pinecone...")
            try:
                upload_result = await pinecone_service.upload_chunks(chunks, metadata)
                
                if upload_result.success:
                    logger.info(f"✅ Successfully uploaded {upload_result.uploaded_count} chunks to Pinecone!")
                    
                    # Mode'a göre farklı response return et
                    if mode == "course":
                        return ProcessResponse(
                            success=True,
                            message=f"PDF başarıyla işlendi ve {upload_result.uploaded_count} chunk Pinecone'a yüklendi (course mode)",
                            processing_id=processing_id,
                            session_id=session_id,
                            extracted_text_length=len(text_content),
                            chunks=chunks  # Course modunda chunk'ları da return et
                        )
                    else:  # chat mode
                        return ProcessResponse(
                            success=True,
                            message=f"PDF başarıyla işlendi ve {upload_result.uploaded_count} chunk Pinecone'a yüklendi",
                            processing_id=processing_id,
                            session_id=session_id,
                            extracted_text_length=len(text_content)
                        )
                else:
                    # Partial success - some chunks uploaded
                    if upload_result.uploaded_count > 0:
                        success_rate = (upload_result.uploaded_count / len(chunks)) * 100
                        logger.warning(f"⚠️ Partial upload: {upload_result.uploaded_count}/{len(chunks)} chunks ({success_rate:.1f}%)")
                        
                        if success_rate >= 50:  # Accept if at least 50% uploaded
                            if mode == "course":
                                return ProcessResponse(
                                    success=True,
                                    message=f"PDF kısmen işlendi: {upload_result.uploaded_count}/{len(chunks)} chunk yüklendi (%{success_rate:.1f}) (course mode)",
                                    processing_id=processing_id,
                                    session_id=session_id,
                                    extracted_text_length=len(text_content),
                                    chunks=chunks  # Course modunda chunk'ları da return et
                                )
                            else:  # chat mode
                                return ProcessResponse(
                                    success=True,
                                    message=f"PDF kısmen işlendi: {upload_result.uploaded_count}/{len(chunks)} chunk yüklendi (%{success_rate:.1f})",
                                    processing_id=processing_id,
                                    session_id=session_id,
                                    extracted_text_length=len(text_content)
                                )
                    
                    # Complete failure or too few chunks uploaded
                    logger.error(f"❌ Pinecone upload failed: {upload_result.failed_count}/{len(chunks)} chunks failed")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"PDF işlendi ama Pinecone'a yüklenemedi. {upload_result.uploaded_count}/{len(chunks)} chunk başarılı oldu."
                    )
                    
            except Exception as upload_error:
                logger.error(f"❌ Upload error: {str(upload_error)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Pinecone yükleme hatası: {str(upload_error)}"
                )
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except HTTPException as he:
        # Re-raise HTTP exceptions as-is
        logger.error(f"❌ HTTP Exception: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"❌ Error processing PDF: {str(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        logger.error(f"❌ Full traceback: {traceback_str}")
        
        # Return detailed error info
        error_detail = f"PDF işleme hatası: {str(e)} | Type: {type(e).__name__}"
        if hasattr(e, '__cause__') and e.__cause__:
            error_detail += f" | Cause: {str(e.__cause__)}"
            
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/processing-status/{processing_id}")
async def get_processing_status(processing_id: str):
    """
    İşleme durumunu kontrol et (opsiyonel - şimdilik basit response)
    """
    # Bu endpoint gelecekte database ile genişletilebilir
    return {"processing_id": processing_id, "status": "processing", "message": "İşlem devam ediyor"}

@app.get("/debug/pinecone")
async def debug_pinecone():
    """
    Pinecone bağlantısını test et ve index bilgilerini getir
    """
    try:
        # Check if pinecone_service is initialized
        if not pinecone_service or not hasattr(pinecone_service, 'index'):
            return {
                "status": "error",
                "error": "Pinecone service not initialized",
                "message": "Pinecone servis başlatılamadı"
            }
        
        # Index stats - safely convert to serializable format
        try:
            raw_stats = pinecone_service.index.describe_index_stats()
            # Convert to JSON-serializable format
            stats = {
                "dimension": raw_stats.get("dimension", 0),
                "index_fullness": raw_stats.get("index_fullness", 0),
                "total_vector_count": raw_stats.get("total_vector_count", 0),
                "namespaces": {}
            }
            
            # Process namespaces safely
            if "namespaces" in raw_stats:
                for ns_name, ns_data in raw_stats["namespaces"].items():
                    if isinstance(ns_data, dict):
                        stats["namespaces"][ns_name] = {
                            "vector_count": ns_data.get("vector_count", 0)
                        }
                    
        except Exception as stats_error:
            logger.error(f"❌ Stats error: {str(stats_error)}")
            stats = {"error": str(stats_error), "error_type": type(stats_error).__name__}
        
        # Environment variables check
        env_check = {
            "pinecone_api_key_exists": bool(os.getenv("PINECONE_API_KEY")),
            "openai_api_key_exists": bool(os.getenv("OPENAI_API_KEY")),
            "index_name": os.getenv("PINECONE_INDEX_NAME", "odev-ai")
        }
        
        return {
            "status": "success",
            "index_stats": stats,
            "environment": env_check,
            "message": "Pinecone bağlantısı başarılı"
        }
        
    except Exception as e:
        logger.error(f"❌ Pinecone debug error: {str(e)}")
        import traceback
        logger.error(f"❌ Debug traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "message": "Pinecone bağlantı hatası"
        }

@app.post("/debug/search-test")
async def search_test_chunks(request: dict = None):
    """
    Test chunk'larını Pinecone'dan ara ve getir
    """
    try:
        # Default query
        query = "test yapay zeka"
        user_id = "debug_user"
        
        if request:
            query = request.get("query", query)
            user_id = request.get("user_id", user_id)
        
        logger.info(f"🔍 Searching Pinecone for: '{query}' for user: {user_id}")
        
        # Search using pinecone_service
        results = pinecone_service.search_similar(
            query=query,
            user_id=user_id,
            top_k=5
        )
        
        # Convert results to JSON-serializable format
        serializable_results = []
        for result in results:
            if isinstance(result, dict):
                # Clean the result to ensure JSON serialization
                clean_result = {
                    "id": result.get("id", ""),
                    "score": float(result.get("score", 0.0)),
                    "metadata": {}
                }
                
                # Safely extract metadata
                if "metadata" in result and isinstance(result["metadata"], dict):
                    metadata = result["metadata"]
                    clean_result["metadata"] = {
                        "text": metadata.get("text", ""),
                        "user_id": metadata.get("user_id", ""),
                        "grade": metadata.get("grade", ""),
                        "subject": metadata.get("subject", ""),
                        "topic": metadata.get("topic", ""),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "source": metadata.get("source", "")
                    }
                
                serializable_results.append(clean_result)
        
        return {
            "status": "success",
            "query": query,
            "user_id": user_id,
            "results_count": len(serializable_results),
            "results": serializable_results,
            "message": f"{len(serializable_results)} sonuç bulundu"
        }
        
    except Exception as e:
        logger.error(f"❌ Search test error: {str(e)}")
        import traceback
        logger.error(f"❌ Search traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "message": "Arama test hatası"
        }

@app.post("/debug/test-upload")
async def debug_test_upload(request: dict = None):
    """
    Test verisi ile Pinecone upload'unu test et
    """
    try:
        # Get user_id from request if provided
        user_id = "debug_user"
        if request and "user_id" in request:
            user_id = request["user_id"]
        
        # Test chunks
        test_chunks = [
            "Bu bir test metnidir. Yapay zeka teknolojileri hakkında bilgi içerir.",
            "Machine learning ve deep learning konularında örnek içerik.",
            "Test amaçlı oluşturulmuş üçüncü chunk."
        ]
        
        # Test metadata - using user_upload source to match search filters
        test_metadata = {
            "source": "user_upload",
            "user_id": user_id,
            "grade": "lisans",
            "subject": "test",
            "topic": "debug test",
            "filename": "debug_test.pdf",
            "processing_id": "debug_" + str(uuid.uuid4())
        }
        
        logger.info(f"🧪 Testing upload with {len(test_chunks)} test chunks...")
        upload_result = await pinecone_service.upload_chunks(test_chunks, test_metadata)
        
        return {
            "status": "success" if upload_result.success else "partial_success",
            "uploaded_count": upload_result.uploaded_count,
            "failed_count": upload_result.failed_count,
            "processing_id": upload_result.processing_id,
            "message": f"Test upload: {upload_result.uploaded_count} başarılı, {upload_result.failed_count} başarısız"
        }
        
    except Exception as e:
        logger.error(f"❌ Test upload error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Test upload hatası"
        }

@app.get("/debug/env")
async def debug_env():
    """
    Environment değişkenlerini kontrol et
    """
    try:
        env_check = {
            "pinecone_api_key_exists": bool(os.getenv("PINECONE_API_KEY")),
            "pinecone_api_key_prefix": os.getenv("PINECONE_API_KEY", "")[:10] + "..." if os.getenv("PINECONE_API_KEY") else "None",
            "openai_api_key_exists": bool(os.getenv("OPENAI_API_KEY")),
            "openai_api_key_prefix": os.getenv("OPENAI_API_KEY", "")[:10] + "..." if os.getenv("OPENAI_API_KEY") else "None",
            "index_name": os.getenv("PINECONE_INDEX_NAME", "odev-ai"),
            "pinecone_service_initialized": pinecone_service is not None,
            "pinecone_service_has_index": hasattr(pinecone_service, 'index') if pinecone_service else False
        }
        
        return {
            "status": "success",
            "environment": env_check,
            "message": "Environment variables check"
        }
        
    except Exception as e:
        logger.error(f"❌ Environment debug error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Environment check hatası"
        }

if __name__ == "__main__":
    import uvicorn
    # Railway'de PORT environment variable kullanır
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
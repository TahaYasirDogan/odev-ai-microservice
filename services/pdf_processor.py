import fitz  # PyMuPDF
import logging
import re
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        """
        PDF processor with optimized chunk sizes for better upload reliability
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_size = 2000  # Hard limit for safety
    
    def extract_text(self, pdf_path: str) -> str:
        """
        PDF dosyasından metin çıkar (PyMuPDF kullanarak)
        """
        try:
            text_content = ""
            
            # PyMuPDF ile PDF aç
            doc = fitz.open(pdf_path)
            
            logger.info(f"📄 PDF has {len(doc)} pages")
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text and page_text.strip():
                        text_content += f"\n--- Sayfa {page_num + 1} ---\n"
                        text_content += page_text
                        text_content += "\n"
                        logger.info(f"✅ Page {page_num + 1}: {len(page_text)} characters extracted")
                    else:
                        logger.warning(f"⚠️ Page {page_num + 1}: No text found")
                        
                except Exception as e:
                    logger.warning(f"❌ Could not extract text from page {page_num + 1}: {str(e)}")
                    continue
            
            # PDF'i kapat
            doc.close()
            
            if not text_content.strip():
                raise Exception("PDF'den hiç metin çıkarılamadı - dosya bozuk olabilir veya sadece resim içeriyor")
            
            # Clean the text
            text_content = self._clean_text(text_content)
            
            logger.info(f"✅ Total extracted: {len(text_content)} characters from PDF")
            return text_content
            
        except Exception as e:
            logger.error(f"❌ Error extracting text from PDF: {str(e)}")
            raise Exception(f"PDF metin çıkarma hatası: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Metni temizle ve normalize et
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Turkish characters
        text = re.sub(r'[^\w\s\.,;:!?\-()çğıöşüÇĞIİÖŞÜ]', '', text)
        
        # Remove multiple consecutive punctuation
        text = re.sub(r'[.,;:!?]{2,}', '.', text)
        
        return text.strip()
    
    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Metni parçalara böl (OPTIMIZE EDİLDİ - büyük PDF'ler için güvenilir)
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Detect large documents and adjust chunk size
        text_length = len(text)
        if text_length > 50000:  # Large document (>50K chars)
            effective_chunk_size = min(1200, self.chunk_size)  # Smaller chunks for large docs
            effective_overlap = min(150, self.chunk_overlap)
            logger.info(f"📋 Large document detected ({text_length} chars), using smaller chunks ({effective_chunk_size})")
        else:
            effective_chunk_size = self.chunk_size
            effective_overlap = self.chunk_overlap
        
        # Split by sentences first for better semantic chunking
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Clean sentence
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 1 > effective_chunk_size:
                if current_chunk:
                    # Finalize current chunk
                    final_chunk = current_chunk.strip()
                    if len(final_chunk) > 30:  # Only add meaningful chunks
                        chunks.append(final_chunk)
                    
                    # Start new chunk with overlap for better context
                    if len(chunks) > 0 and effective_overlap > 0:
                        overlap_text = current_chunk[-effective_overlap:].strip()
                        current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                    else:
                        current_chunk = sentence
                else:
                    # Single sentence is too long, need to split it
                    if len(sentence) > effective_chunk_size:
                        logger.warning(f"⚠️ Very long sentence ({len(sentence)} chars), splitting...")
                        # Split long sentence by words
                        words = sentence.split()
                        temp_chunk = ""
                        
                        for word in words:
                            if len(temp_chunk) + len(word) + 1 > effective_chunk_size:
                                if temp_chunk.strip():
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                temp_chunk += " " + word if temp_chunk else word
                        
                        current_chunk = temp_chunk if temp_chunk else ""
                    else:
                        current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk if it has meaningful content
        if current_chunk.strip() and len(current_chunk.strip()) > 30:
            chunks.append(current_chunk.strip())
        
        # Final cleanup - ensure no chunk exceeds max size
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.max_chunk_size:
                logger.warning(f"⚠️ Chunk too large ({len(chunk)} chars), splitting further...")
                # Split by words if still too large
                words = chunk.split()
                temp_chunk = ""
                
                for word in words:
                    if len(temp_chunk) + len(word) + 1 > self.max_chunk_size:
                        if temp_chunk.strip():
                            final_chunks.append(temp_chunk.strip())
                        temp_chunk = word
                    else:
                        temp_chunk += " " + word if temp_chunk else word
                
                if temp_chunk.strip():
                    final_chunks.append(temp_chunk.strip())
            else:
                final_chunks.append(chunk)
        
        # Filter out chunks that are too short (but keep some minimum content)
        final_chunks = [chunk for chunk in final_chunks if len(chunk.strip()) > 30]
        
        # Log statistics
        if final_chunks:
            avg_chunk_size = sum(len(chunk) for chunk in final_chunks) / len(final_chunks)
            max_chunk_size = max(len(chunk) for chunk in final_chunks)
            logger.info(f"📊 Split into {len(final_chunks)} chunks (avg: {avg_chunk_size:.0f}, max: {max_chunk_size} chars)")
        else:
            logger.warning("⚠️ No valid chunks created from text")
        
        return final_chunks 
import os
import logging
import uuid
import time
from typing import List, Dict, Any, Union
from pinecone import Pinecone, ServerlessSpec
import openai
from openai import OpenAI
from models.schemas import PineconeUploadResponse

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'odev-ai')
        self.max_retries = 3  # Maximum number of retries for failed uploads
        self.retry_delay = 2  # Delay in seconds between retries
        
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index(self.index_name)
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        logger.info(f"Initialized Pinecone service with index: {self.index_name}")
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Tek text için OpenAI embedding oluştur (backward compatibility)
        """
        try:
            # Truncate text if too long (OpenAI has a token limit)
            if len(text) > 8000:  # Approximate limit
                text = text[:8000]
                logger.warning("Text truncated to 8000 characters for embedding")
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise Exception(f"Embedding oluşturma hatası: {str(e)}")
    
    def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Birden fazla text için batch embedding oluştur (OPTIMIZE EDİLDİ!)
        """
        try:
            logger.info(f"Creating embeddings for {len(texts)} texts in batch")
            
            # OpenAI batch limit = 2048, ama güvenli olması için 1000 kullan
            max_batch_size = 1000
            all_embeddings = []
            
            # Büyük listeler için birden fazla API çağrısı yap
            for batch_start in range(0, len(texts), max_batch_size):
                batch_end = min(batch_start + max_batch_size, len(texts))
                batch_texts = texts[batch_start:batch_end]
                
                # Truncate long texts
                processed_texts = []
                for text in batch_texts:
                    if len(text) > 8000:  # OpenAI limit
                        text = text[:8000]
                        logger.warning("Text truncated to 8000 characters for batch embedding")
                    processed_texts.append(text)
                
                logger.info(f"Processing embedding batch {batch_start//max_batch_size + 1} with {len(processed_texts)} texts")
                
                # API çağrısı retry mekanizması ile
                retry_count = 0
                max_retries = 3
                
                while retry_count <= max_retries:
                    try:
                        response = self.openai_client.embeddings.create(
                            model="text-embedding-3-small",
                            input=processed_texts,
                            encoding_format="float"
                        )
                        
                        batch_embeddings = [data.embedding for data in response.data]
                        all_embeddings.extend(batch_embeddings)
                        logger.info(f"✅ Successfully created {len(batch_embeddings)} embeddings in batch {batch_start//max_batch_size + 1}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count <= max_retries:
                            logger.warning(f"⚠️ Embedding batch {batch_start//max_batch_size + 1} retry {retry_count}/{max_retries}. Error: {str(e)}")
                            time.sleep(2 * retry_count)  # Exponential backoff
                        else:
                            logger.error(f"❌ Failed to create embeddings for batch {batch_start//max_batch_size + 1} after {max_retries} retries")
                            raise Exception(f"Embedding batch failed: {str(e)}")
            
            logger.info(f"🎉 Successfully created {len(all_embeddings)} total embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error creating batch embeddings: {str(e)}")
            raise Exception(f"Batch embedding oluşturma hatası: {str(e)}")
    
    async def upload_chunks(self, chunks: List[str], base_metadata: Dict[str, Any]) -> PineconeUploadResponse:
        """
        Text chunk'larını Pinecone'a yükle (ULTRA OPTIMIZE EDİLDİ!)
        """
        uploaded_count = 0
        failed_count = 0
        processing_id = base_metadata.get('processing_id', str(uuid.uuid4()))
        
        try:
            logger.info(f"🚀 Starting optimized batch processing for {len(chunks)} chunks")
            
            # CHUNK'LARI KÜÇÜLTELİM - Büyük PDF'ler için daha güvenilir
            if len(chunks) > 100:
                logger.info(f"📋 Large document detected ({len(chunks)} chunks), using conservative batch processing")
                batch_size = 20  # Küçük batch size
                self.max_retries = 5  # Daha fazla retry
            else:
                batch_size = 50  # Normal batch size
                self.max_retries = 3
            
            # Skip index stats for large uploads to avoid JSON serialization issues
            if len(chunks) <= 50:
                try:
                    stats = self.index.describe_index_stats()
                    logger.info(f"📊 Pinecone vectors before upload: {stats.get('total_vector_count', 'unknown')}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not get index stats: {str(e)}")
            
            # 🚀 BATCH EMBEDDINGS (smaller batches for reliability)
            embeddings = self.create_batch_embeddings(chunks)
            
            if len(embeddings) != len(chunks):
                raise Exception(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)} chunks")
            
            # Prepare vectors in smaller batches
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            logger.info(f"📦 Will upload in {total_batches} batches of max {batch_size} vectors each")
            
            for batch_num in range(total_batches):
                batch_start = batch_num * batch_size
                batch_end = min(batch_start + batch_size, len(chunks))
                
                batch_chunks = chunks[batch_start:batch_end]
                batch_embeddings = embeddings[batch_start:batch_end]
                
                logger.info(f"🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_chunks)} chunks)")
                
                vectors_to_upsert = []
                
                for i, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                    try:
                        # Create unique ID for this chunk
                        global_index = batch_start + i
                        chunk_id = f"{processing_id}_chunk_{global_index}"
                        
                        # Clean and truncate metadata text fields to avoid issues
                        clean_chunk = chunk[:500] if len(chunk) > 500 else chunk  # Smaller limit for metadata
                        
                        # Prepare metadata (simplified to avoid serialization issues)
                        metadata = {
                            'source': base_metadata.get('source', 'user_upload'),
                            'user_id': base_metadata.get('user_id', 'unknown'),
                            'grade': base_metadata.get('grade', 'unknown'),
                            'subject': base_metadata.get('subject', 'user_content'),
                            'topic': base_metadata.get('topic', 'unknown'),
                            'text': clean_chunk,
                            'content': clean_chunk,
                            'chunk_index': global_index,
                            'total_chunks': len(chunks),
                            'processing_id': processing_id,
                            'filename': base_metadata.get('filename', 'unknown.pdf')
                        }
                        
                        # Add to batch
                        vectors_to_upsert.append({
                            'id': chunk_id,
                            'values': embedding,
                            'metadata': metadata
                        })
                        
                    except Exception as e:
                        logger.error(f"❌ Error preparing chunk {global_index}: {str(e)}")
                        failed_count += 1
                        continue
                
                # Upload this batch with retry mechanism
                batch_uploaded = False
                retry_count = 0
                
                while retry_count <= self.max_retries and not batch_uploaded:
                    try:
                        logger.info(f"🚀 Uploading batch {batch_num + 1} (attempt {retry_count + 1}) - {len(vectors_to_upsert)} vectors")
                        
                        self.index.upsert(vectors=vectors_to_upsert)
                        uploaded_count += len(vectors_to_upsert)
                        batch_uploaded = True
                        
                        logger.info(f"✅ Batch {batch_num + 1} uploaded successfully!")
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count <= self.max_retries:
                            wait_time = min(2 * retry_count, 10)  # Max 10 seconds wait
                            logger.warning(f"⚠️ Batch {batch_num + 1} retry {retry_count}/{self.max_retries} in {wait_time}s. Error: {type(e).__name__}")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"❌ Batch {batch_num + 1} failed after {self.max_retries} retries: {str(e)}")
                            failed_count += len(vectors_to_upsert)
                
                # Progress log for large uploads
                if total_batches > 5:
                    progress = ((batch_num + 1) / total_batches) * 100
                    logger.info(f"📈 Upload progress: {progress:.1f}% ({uploaded_count} uploaded, {failed_count} failed)")
            
            success_rate = (uploaded_count / len(chunks)) * 100 if len(chunks) > 0 else 0
            logger.info(f"🎉 Upload completed! Success: {uploaded_count}/{len(chunks)} ({success_rate:.1f}%)")
            
            return PineconeUploadResponse(
                success=failed_count == 0,
                uploaded_count=uploaded_count,
                failed_count=failed_count,
                processing_id=processing_id
            )
            
        except Exception as e:
            logger.error(f"❌ Critical error in upload_chunks: {str(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            return PineconeUploadResponse(
                success=False,
                uploaded_count=uploaded_count,
                failed_count=len(chunks) - uploaded_count,
                processing_id=processing_id
            )
    
    def search_similar(self, query: str, grade: str = None, subject: str = None, 
                      user_id: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic search in Pinecone
        """
        try:
            # Create query embedding
            query_embedding = self.create_embedding(query)
            
            # Build filter
            filter_dict = {}
            if grade:
                filter_dict['grade'] = {'$eq': grade}
            if subject:
                filter_dict['subject'] = {'$eq': subject}
            if user_id:
                filter_dict['user_id'] = {'$eq': user_id}
            
            # Search
            search_response = self.index.query(
                vector=query_embedding,
                filter=filter_dict if filter_dict else None,
                top_k=top_k,
                include_metadata=True,
                include_values=False
            )
            
            results = []
            for match in search_response.matches:
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'content': match.metadata.get('content', match.metadata.get('text', '')),
                    'metadata': match.metadata
                })
            
            logger.info(f"Search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in search_similar: {str(e)}")
            return [] 
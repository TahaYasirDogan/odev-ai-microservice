# PDF Processing Microservice

Bu mikroservis, PDF dosyalarını işleyerek metin çıkarımı yapar ve Pinecone'a yükler.

## 🚀 Başlatma

### 1. Environment Variables
```bash
cp env_example.txt .env
```

`.env` dosyasını düzenleyip gerekli API key'leri ekleyin:
- `PINECONE_API_KEY`: Pinecone API anahtarınız
- `OPENAI_API_KEY`: OpenAI API anahtarınız

### 2. Local Development

#### Python Virtual Environment ile:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
python main.py
```

#### Docker ile:
```bash
# Build
docker build -t pdf-processor .

# Run
docker run -p 8000:8000 --env-file .env pdf-processor
```

#### Docker Compose ile:
```bash
docker-compose up --build
```

### 3. Next.js Integration

Next.js projesinin `.env.local` dosyasına mikroservis URL'ini ekleyin:
```bash
PDF_MICROSERVICE_URL=http://localhost:8000
```

## 📡 API Endpoints

### Health Check
```
GET /health
```

### PDF Processing
```
POST /process-pdf
```

**Parameters (Form Data):**
- `file`: PDF dosyası
- `grade`: Sınıf seviyesi
- `subject`: Ders (opsiyonel)
- `topic`: Konu
- `user_id`: Kullanıcı ID'si

**Response:**
```json
{
  "success": true,
  "message": "PDF başarıyla işlendi",
  "processing_id": "uuid",
  "extracted_text_length": 1234
}
```

### Processing Status
```
GET /processing-status/{processing_id}
```

## 🔧 Configuration

### Environment Variables
- `PINECONE_API_KEY`: Pinecone API key
- `PINECONE_INDEX_NAME`: Pinecone index adı (default: rag-turkce-egitim-1536)
- `OPENAI_API_KEY`: OpenAI API key
- `HOST`: Host address (default: 0.0.0.0)
- `PORT`: Port number (default: 8000)
- `FRONTEND_URL`: Frontend URL for CORS (default: http://localhost:3000)

### PDF Processing Settings
- **Maksimum dosya boyutu**: 5MB
- **Chunk boyutu**: 1000 karakter
- **Chunk overlap**: 200 karakter
- **Desteklenen formatlar**: PDF

### Pinecone Integration
- **Embedding model**: text-embedding-3-small
- **Batch size**: 100 vectors per batch
- **Metadata fields**: 
  - `source`: "user_upload"
  - `user_id`: Kullanıcı ID'si
  - `grade`: Sınıf seviyesi
  - `subject`: Ders adı
  - `topic`: Konu
  - `filename`: Original dosya adı
  - `text`: Chunk içeriği
  - `content`: Chunk içeriği (compat)

## 🐛 Troubleshooting

### Common Issues

1. **Pinecone Connection Error**
   - API key'in doğru olduğundan emin olun
   - Index adının doğru olduğunu kontrol edin

2. **OpenAI API Error**
   - API key'in valid olduğundan emin olun
   - Rate limit'e takılmış olabilirsiniz

3. **PDF Extraction Failed**
   - PDF'in corrupt olmadığından emin olun
   - PDF'de yeterli metin olduğundan emin olun

### Logs
```bash
# Container logs
docker logs pdf-processor

# Docker compose logs
docker-compose logs -f
```

## 🔐 Security

- PDF dosyaları temporary olarak saklanır ve işlem sonrası silinir
- User ID bazlı izolasyon sağlanır
- CORS ayarları yapılandırılabilir
- File upload size limits uygulanır 
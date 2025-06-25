# 🚀 Railway.app ile PDF Mikroservis Deployment

Bu rehber Railway.app üzerinde PDF mikroservisini nasıl deploy edeceğinizi gösterir.

## 📋 Ön Hazırlık

### 1. Railway Hesabı
- [railway.app](https://railway.app) adresinden ücretsiz hesap oluşturun
- GitHub ile bağlantı kurun

### 2. GitHub Repository Hazırlığı
```bash
# Mikroservis klasörünü ayrı bir repo yapmak için
cd microservice
git init
git add .
git commit -m "Initial PDF microservice"

# GitHub'da yeni repo oluşturun ve push edin
git remote add origin https://github.com/KULLANICI_ADI/pdf-microservice.git
git push -u origin main
```

## 🚀 Railway Deployment

### 1. Railway'de Yeni Proje Oluştur
1. Railway dashboard'una gidin
2. "New Project" tıklayın
3. "Deploy from GitHub repo" seçin
4. `pdf-microservice` reposunu seçin

### 2. Environment Variables Ayarlayın
Railway dashboard'da Variables sekmesinde aşağıdaki değişkenleri ekleyin:

```bash
PINECONE_API_KEY=pcsk_32VJ9F_BK9eDdhH7vJHMQgtT3a5q9D3p4YdrVxQGKQYvNGVjc5rw886piHQ91hgcek5RHm
OPENAI_API_KEY=sk-proj-gwtK4IagT6QJz6cEE7Z3mXxy6bhONWfiMn9X5ObZU8NI0bJ4dcWr2RMEZMlgJBvshSAh81nWXN
PINECONE_INDEX_NAME=rag-turkce-egitim-1536
```

⚠️ **Önemli**: Gerçek API key'lerinizi kullanın!

### 3. Domain Adresini Al
- Deploy tamamlandıktan sonra Railway size bir domain verecek
- Örnek: `https://pdf-microservice-production.up.railway.app`

## 🔧 Next.js Entegrasyonu

Ana Next.js projenizde `.env.local` dosyasını güncelleyin:

```bash
# Railway mikroservis URL'ini ekleyin
PDF_MICROSERVICE_URL=https://pdf-microservice-production.up.railway.app
```

## ✅ Test Etme

### 1. Health Check
```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
```

Başarılı response:
```json
{
  "status": "healthy", 
  "message": "PDF Processing Microservice is running"
}
```

### 2. Next.js'den Test
SetupForm'da lisans seçip PDF yükleyerek test edin.

## 📊 Monitoring

Railway dashboard'da şunları izleyebilirsiniz:
- **Deployment logs**
- **Runtime metrics**
- **Environment variables**
- **Custom domains**

## 💰 Maliyet

- **Starter Plan**: $5/ay (512 MB RAM, 1 GB disk)
- **İlk ay ücretsiz**
- **Kullanım bazlı fiyatlandırma**

## 🐛 Troubleshooting

### Build Errors
```bash
# Logs'u kontrol edin
railway logs --tail

# Environment variables'ı kontrol edin
railway variables
```

### API Connection Issues
```bash
# CORS ayarlarını kontrol edin
# main.py'de allow_origins=["*"] olduğundan emin olun
```

### Memory Issues
```bash
# Railway plan'ınızı upgrade edin
# Starter plan: 512MB RAM yeterli olmalı
```

## 🚀 Avantajlar

✅ **Otomatik SSL**: HTTPS support  
✅ **Auto-scaling**: Trafik bazlı ölçeklendirme  
✅ **Continuous deployment**: Git push ile otomatik deploy  
✅ **Environment isolation**: Production ortamı  
✅ **Monitoring**: Built-in izleme araçları  
✅ **Database support**: PostgreSQL, MySQL, Redis  

Bu şekilde mikroservisiniz Railway cloud'da çalışacak ve Next.js uygulamanız PDF işleme için bu servisi kullanabilecek! 🎉 
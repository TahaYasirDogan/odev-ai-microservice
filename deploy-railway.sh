#!/bin/bash

echo "🚀 Railway.app Deployment Script"
echo "================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
fi

# Add all files
echo "📁 Adding files to git..."
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "ℹ️  No changes to commit"
else
    echo "💾 Committing changes..."
    git commit -m "Railway deployment setup - $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo ""
echo "✅ Repository hazır!"
echo ""
echo "🔗 Şimdi aşağıdaki adımları takip edin:"
echo ""
echo "1. GitHub'da yeni bir repository oluşturun:"
echo "   - Repository adı: pdf-microservice"
echo "   - Public veya Private seçebilirsiniz"
echo ""
echo "2. Remote repository ekleyin:"
echo "   git remote add origin https://github.com/KULLANICI_ADI/pdf-microservice.git"
echo ""
echo "3. Kodu GitHub'a push edin:"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "4. Railway.app'e gidin:"
echo "   - https://railway.app adresine gidin"
echo "   - GitHub ile giriş yapın"
echo "   - 'New Project' > 'Deploy from GitHub repo' seçin"
echo "   - pdf-microservice reposunu seçin"
echo ""
echo "5. Environment Variables ekleyin:"
echo "   PINECONE_API_KEY=pcsk_32VJ9F_BK9eDdhH7vJHMQgtT3a5q9D3p4YdrVxQGKQYvNGVjc5rw886piHQ91hgcek5RHm"
echo "   OPENAI_API_KEY=sk-proj-gwtK4IagT6QJz6cEE7Z3mXxy6bhONWfiMn9X5ObZU8NI0bJ4dcWr2RMEZMlgJBvshSAh81nWXN"
echo "   PINECONE_INDEX_NAME=rag-turkce-egitim-1536"
echo ""
echo "6. Deploy tamamlandığında size verilen URL'i Next.js projesine ekleyin:"
echo "   PDF_MICROSERVICE_URL=https://your-app.up.railway.app"
echo ""
echo "🎉 Deployment tamamlandıktan sonra mikroservisiniz Railway cloud'da çalışacak!"

# Show current directory contents
echo ""
echo "📋 Deployment için hazırlanan dosyalar:"
ls -la | grep -E "(requirements\.txt|main\.py|Procfile|railway\.toml|runtime\.txt)" 
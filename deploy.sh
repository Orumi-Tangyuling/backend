#!/bin/bash

set -euo pipefail

echo "🚀 Tangyuling API 배포 시작..."

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker가 실행되고 있지 않습니다."
    exit 1
fi

cd ~/tangyuling

echo "📥 최신 이미지 다운로드 중..."
docker compose --env-file .env.prod -f docker-compose.prod.yml pull api mysql

echo "▶️  애플리케이션 시작 중..."
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d mysql api

echo "✅ 컨테이너 상태 확인..."
sleep 5
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

echo "📋 최근 로그 확인..."
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=30 api

PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-clean-be.sinryuji.me}"
echo "🏥 Traefik 경유 헬스체크: https://${PUBLIC_DOMAIN}/health"
if curl -fsS "https://${PUBLIC_DOMAIN}/health" > /dev/null 2>&1; then
    echo "✅ 배포 완료! API가 Traefik 뒤에서 정상 동작합니다."
else
    echo "⚠️  헬스체크 실패. API 로그를 확인하세요."
    docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=50 api
    exit 1
fi

echo "🧹 사용하지 않는 이미지 정리 중..."
docker image prune -af

echo "✨ 배포 완료!"

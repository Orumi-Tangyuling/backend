#!/bin/bash

# Tangyuling API 배포 스크립트
# 서버에서 수동으로 배포할 때 사용

set -e

echo "🚀 Tangyuling API 배포 시작..."

# Docker Hub 로그인 확인
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker가 실행되고 있지 않습니다."
    exit 1
fi

# 배포 디렉토리로 이동
cd ~/tangyuling

if [ -n "$DOCKER_USERNAME" ]; then
    echo "📥 최신 Docker 이미지 다운로드 중..."
    docker compose -f docker-compose.prod.yml pull
else
    echo "🏗️  DOCKER_USERNAME이 없어 로컬에서 API 이미지를 빌드합니다."
    docker compose -f docker-compose.prod.yml build api
fi

DOMAIN="${DOMAIN:-clean-be.sinryuji.me}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"

# 새 컨테이너 시작
echo "▶️  애플리케이션 및 Nginx 시작 중..."
docker compose -f docker-compose.prod.yml up -d mysql api nginx

# 인증서 발급 또는 갱신 준비
if [ ! -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    if [ -z "$LETSENCRYPT_EMAIL" ]; then
        echo "⚠️  LETSENCRYPT_EMAIL 환경 변수가 없어 SSL 인증서 발급을 건너뜁니다."
        echo "    HTTP는 열리지만 HTTPS는 비활성화됩니다."
    else
        echo "🔐 Let's Encrypt 인증서 최초 발급 중..."
        docker compose --profile certbot -f docker-compose.prod.yml run --rm certbot certonly \
            --webroot \
            --webroot-path /var/www/certbot \
            --email "$LETSENCRYPT_EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN"

        echo "🔁 Nginx 재시작으로 HTTPS 활성화..."
        docker compose -f docker-compose.prod.yml restart nginx
    fi
else
    echo "🔐 기존 SSL 인증서 확인됨. Nginx를 HTTPS 구성으로 유지합니다."
    docker compose -f docker-compose.prod.yml restart nginx
fi

# 컨테이너 상태 확인
echo "✅ 컨테이너 상태 확인..."
sleep 5
docker compose -f docker-compose.prod.yml ps

# 로그 확인
echo "📋 최근 로그 확인..."
docker compose -f docker-compose.prod.yml logs --tail=30 api

# 헬스체크
echo "🏥 API 헬스체크..."
sleep 3
if [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    if curl -k -f "https://localhost/health" > /dev/null 2>&1; then
        echo "✅ 배포 완료! HTTPS로 API가 정상적으로 실행 중입니다."
    else
        echo "⚠️  HTTPS 헬스체크 실패. 로그를 확인하세요."
        docker compose -f docker-compose.prod.yml logs --tail=50 nginx api
        exit 1
    fi
elif curl -f "http://localhost/health" > /dev/null 2>&1; then
    echo "✅ 배포 완료! HTTP로 API가 정상적으로 실행 중입니다."
else
    echo "⚠️  API 헬스체크 실패. 로그를 확인하세요."
    docker compose -f docker-compose.prod.yml logs --tail=50 nginx api
    exit 1
fi

# 사용하지 않는 이미지 정리
echo "🧹 사용하지 않는 이미지 정리 중..."
docker image prune -af

echo "✨ 배포 완료!"

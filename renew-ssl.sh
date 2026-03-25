#!/bin/bash

set -e

DOMAIN="${DOMAIN:-clean-be.sinryuji.me}"

cd ~/tangyuling

echo "🔄 SSL 인증서 갱신 확인 중..."
docker compose --profile certbot -f docker-compose.prod.yml run --rm certbot renew --webroot -w /var/www/certbot

echo "🔁 Nginx 재시작 중..."
docker compose -f docker-compose.prod.yml restart nginx

echo "✅ SSL 갱신 작업 완료: $DOMAIN"

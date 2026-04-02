# Tangyuling Backend 배포 가이드 (GitHub Actions + GHCR + Traefik)

## 개요

- 배포 도메인: `clean-be.sinryuji.me`
- 컨테이너 레지스트리: GitHub Container Registry (`ghcr.io`)
- 리버스 프록시/SSL: 서버의 Traefik이 처리 (네트워크: `dev`)
- 앱 배포: GitHub Actions에서 SSH로 서버 접속 후 `docker compose` 갱신 (`.env.prod` 사용)

## GitHub Actions 워크플로우

- 파일: `.github/workflows/deploy.yml`
- 트리거:
  - `push` to `main`
  - `workflow_dispatch`
- 동작:
  1. Docker 이미지를 `ghcr.io/<owner>/tangyuling-api`로 빌드/푸시
  2. `ssh.sinryuji.me` (`sinryuji`)로 SSH 접속
  3. 서버 `~/tangyuling`에 `docker-compose.prod.yml`, `.env.prod` 반영
  4. `mysql`, `api` 서비스 pull/up
  5. `https://clean-be.sinryuji.me/health` 확인

## GitHub Secrets

GitHub 저장소 → Settings → Secrets and variables → Actions

- `SSH_PRIVATE_KEY`: 배포 서버 접속용 개인키
- `ENV_FILE`: 서버에 배포할 `.env.prod` 전체 내용

## ENV_FILE 예시

```env
DATABASE_URL=mysql+pymysql://root:your_password@mysql:3306/tangyuling
MYSQL_ROOT_PASSWORD=your_secure_password
MYSQL_DATABASE=tangyuling
CURRENT_API_URL=https://apis.data.go.kr/1192136/twRecent/GetTWRecentApiService
CURRENT_API_KEY=your-ocean-api-key
WIND_API_URL=https://apis.data.go.kr/1192136/surveyWind/GetSurveyWindApiService
WIND_API_KEY=your-ocean-api-key
TEMPERATURE_API_URL=https://apis.data.go.kr/1192136/surveyWaterTemp/GetSurveyWaterTempApiService
TEMPERATURE_API_KEY=your-ocean-api-key
MODEL_PATH=ml/random_forest_model_vector_0.68_0.31.pkl
JWT_SECRET_KEY=your-very-secure-secret-key-here
CORS_ORIGINS=https://clean.sinryuji.me
ALAN_API_BASE_URL=https://your-alan-ai-url
ALAN_CLIENT_ID=your-client-id
GHCR_OWNER=sinryuji
IMAGE_TAG=latest
PUBLIC_DOMAIN=clean-be.sinryuji.me
ENV=production
DEBUG=False
```

## 서버 사전 조건

배포 서버에서 아래가 준비되어 있어야 합니다.

1. Docker / Docker Compose 사용 가능
2. `dev` Docker external network 존재
3. Traefik이 `dev` 네트워크에서 동작 중
4. Traefik에 `certificatesresolvers.le` 설정 존재
5. `sinryuji` 사용자로 SSH 접속 가능

참고: 현재 Traefik compose 파일은 `~/traefik/compose.yaml` 입니다.

## 프로덕션 Compose

파일: `docker-compose.prod.yml`

- `api`, `mysql`만 실행
- `api`는 `dev` 네트워크에 연결
- Traefik 라벨:
  - `Host(clean-be.sinryuji.me)` 라우팅
  - `entrypoints=websecure`
  - `tls.certresolver=le`
  - 서비스 포트 `8000`

## 자동 배포 절차

1. `main` 브랜치에 push
2. GitHub Actions `Deploy Backend (GHCR + Traefik)` 확인
3. 성공 후 확인:
   - `https://clean-be.sinryuji.me/health`
   - `https://clean-be.sinryuji.me/docs`

## 수동 배포 (필요 시)

서버에서:

```bash
cd ~/tangyuling
docker login ghcr.io
GHCR_OWNER=sinryuji IMAGE_TAG=latest PUBLIC_DOMAIN=clean-be.sinryuji.me ./deploy.sh
```

## 점검 명령어

```bash
cd ~/tangyuling
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=100 api
curl -fsS https://clean-be.sinryuji.me/health
```

## Current API 점검 체크리스트

`/api/v1/trash/beach` 500을 방지하려면 아래를 반드시 확인하세요.

1. `CURRENT_API_URL`가 폐지 URL이 아닌지 확인
   - 허용: `https://apis.data.go.kr/1192136/twRecent/GetTWRecentApiService`
   - 금지: `http(s)://www.khoa.go.kr/api/oceangrid/tidalCurrentArea/search.do`
2. `CURRENT_API_KEY` 값 확인
3. 관측소 코드는 현재 `KG_0021`, `KG_0028`를 사용
4. `KG_0021` 응답에서 유향/유속(`crdir`, `crsp`)이 결측일 수 있으므로 코드에서 `KG_0028`으로 fallback됨

서버에서 실호출 점검:

```bash
curl -sS --get 'https://apis.data.go.kr/1192136/twRecent/GetTWRecentApiService' \
  --data-urlencode "serviceKey=${CURRENT_API_KEY}" \
  --data-urlencode "obsCode=KG_0021" \
  --data-urlencode "reqDate=$(date +%Y%m%d)" \
  --data-urlencode "min=30" \
  --data-urlencode "numOfRows=10" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "type=json"

curl -sS --get 'https://apis.data.go.kr/1192136/twRecent/GetTWRecentApiService' \
  --data-urlencode "serviceKey=${CURRENT_API_KEY}" \
  --data-urlencode "obsCode=KG_0028" \
  --data-urlencode "reqDate=$(date +%Y%m%d)" \
  --data-urlencode "min=30" \
  --data-urlencode "numOfRows=10" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "type=json"
```

## 트러블슈팅

1. 이미지 pull 실패
   - 서버에서 `docker login ghcr.io` 상태 확인
   - GHCR 패키지 권한/가시성 확인
2. 라우팅 실패
   - Traefik 컨테이너가 `dev` 네트워크에 연결되어 있는지 확인
   - `docker compose -f docker-compose.prod.yml config` 결과에서 `api` 라벨 확인
3. 앱 기동 실패
   - `ENV_FILE` 값 확인 (`.env.prod` 내용: `DATABASE_URL`, `MYSQL_ROOT_PASSWORD` 등)
   - `docker compose logs api mysql` 확인

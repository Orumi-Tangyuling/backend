# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# entrypoint 스크립트에 실행 권한 부여
RUN chmod +x /app/entrypoint.sh

# 포트 노출
EXPOSE 8000

# 한글 폰트가 필요한 경우를 위한 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# entrypoint 스크립트 설정
ENTRYPOINT ["/app/entrypoint.sh"]

# Uvicorn으로 FastAPI 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

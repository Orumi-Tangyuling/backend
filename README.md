# FastAPI Backend

## 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## 실행

```bash
uvicorn main:app --reload
```

서버는 http://127.0.0.1:8000 에서 실행됩니다.

## API 문서

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

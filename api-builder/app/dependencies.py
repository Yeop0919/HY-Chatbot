import hashlib
import os

from dotenv import load_dotenv
from fastapi import Security, Request, HTTPException
from fastapi.security import APIKeyHeader
from loguru import logger

from app.config import settings

# 환경변수 로드
load_dotenv()

# 환경변수에서 API Key 가져오기
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY", "").strip()

# FastAPI API Key Security 설정
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_current_user(api_key: str = Security(api_key_header)):
    """ API Key 인증 함수 """
    if not api_key:
        raise HTTPException(status_code=403, detail="API Key가 제공되지 않았습니다.")

    # 'ApiKey ' 접두어 제거 후 비교
    clean_api_key = api_key.replace("ApiKey ", "").strip()

    # API Key 검증 (해시 비교로 타이밍 공격 방지)
    if hashlib.sha256(clean_api_key.encode()).hexdigest() != hashlib.sha256(ELASTIC_API_KEY.encode()).hexdigest():
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return {"user": "authenticated"}

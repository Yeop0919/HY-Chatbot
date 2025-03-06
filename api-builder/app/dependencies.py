import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Security, Request, HTTPException
from fastapi.security import APIKeyHeader
from app.config import settings 
import os
from app.utils.authentication import token_validation
from dotenv import load_dotenv
from fastapi import Security, Request, HTTPException
from fastapi.security import APIKeyHeader

header_scheme = APIKeyHeader(name="x-token")


async def get_token_header(x_token: Annotated[str, Security(header_scheme)]):
    await token_validation(x_token)

from fastapi import Security, HTTPException, Request
from fastapi.security import APIKeyHeader
from app.config import settings
from loguru import logger

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)



# 환경변수 로드
load_dotenv()
import hashlib
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

    # API Key 검증
    if clean_api_key != ELASTIC_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    # 해시 비교 (보안 강화)
    if hashlib.sha256(clean_api_key.encode()).hexdigest() != hashlib.sha256(ELASTIC_API_KEY.encode()).hexdigest():
        raise HTTPException(status_code=403, detail="Invalid API Key (Hash Mismatch)")

    return {"user": "authenticated"}


# import os
# import hashlib
# import logging
# from pydantic_settings import BaseSettings  # 변경된 import 방식
# from dotenv import load_dotenv

# # 환경변수 로드
# load_dotenv()

# # FastAPI 설정 (Pydantic v2 호환)
# class Settings(BaseSettings):
#     ELASTIC_API_KEY: str = os.getenv("ELASTIC_API_KEY", "").strip()

# settings = Settings()

# # 로거 설정
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def debug_api_key():
#     """ 환경변수 및 API Key 불러오기 & 검증 """
#     env_api_key = os.getenv("ELASTIC_API_KEY", "").strip()
#     settings_api_key = settings.ELASTIC_API_KEY.strip()

#     logger.info("환경변수 & API Key 체크 시작")

#     if not env_api_key:
#         logger.error("❌ 환경변수 'ELASTIC_API_KEY'가 로드되지 않음!")
#     else:
#         logger.info(f"✅ 환경변수 'ELASTIC_API_KEY' 로드됨: {repr(env_api_key)} (길이: {len(env_api_key)})")

#     if not settings_api_key:
#         logger.error("❌ settings에서 'ELASTIC_API_KEY'가 None 또는 공백!")
#     else:
#         logger.info(f"✅ settings.ELASTIC_API_KEY: {repr(settings_api_key)} (길이: {len(settings_api_key)})")

#     # 공백 및 개행 체크
#     if env_api_key != settings_api_key:
#         logger.warning(f"❌ API Key 불일치 (공백/개행 가능성): '{env_api_key}' != '{settings_api_key}'")

#     # 인코딩 체크
#     if env_api_key.encode() != settings_api_key.encode():
#         logger.error(f"❌ API Key 인코딩 불일치: {env_api_key.encode()} != {settings_api_key.encode()}")

#     # Hash 비교 (완벽한 체크)
#     if hashlib.sha256(env_api_key.encode()).hexdigest() != hashlib.sha256(settings_api_key.encode()).hexdigest():
#         logger.error("❌ API Key Hash 불일치!")

#     logger.info("✅ 환경변수 검증 완료")

# FastAPI API Key 인증 함수
async def get_current_user(api_key: str = settings.ELASTIC_API_KEY):
    if not api_key:
        logger.error("❌ API Key 없음 - 인증 실패!")
        raise ValueError("Not authenticated")

    logger.info(f"✅ API Key 인증 성공: {repr(api_key)}")
    return {"user": "authenticated"}

# 환경변수 체크 실행
# debug_api_key()



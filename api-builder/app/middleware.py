from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message


class AddAuthHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 기존 요청 헤더 로그 출력
        # print(f"[DEBUG] 기존 요청 헤더: {dict(request.headers)}")

        # '/bot/search' 경로에 대한 요청인지 확인
        if request.url.path.startswith("/bot/search"):
            # print(f"[DEBUG] '/bot/search' 요청 감지, Authorization 헤더 추가")

            # 기존 헤더를 가져와 수정
            headers = list(request.headers.raw)
            headers.append((b"authorization", b"ApiKey b2NlM0..."))  # API 키 추가

            # scope의 헤더를 변경
            request.scope["headers"] = headers

        response = await call_next(request)
        return response

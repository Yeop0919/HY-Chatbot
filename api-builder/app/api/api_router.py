from app.api.routers import rest
from app.dependencies import get_current_user
from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

api_router = APIRouter(dependencies=[Depends(get_current_user)], default_response_class=JSONResponse)

api_router.include_router(rest.router, tags=["rest"])

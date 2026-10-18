from fastapi import APIRouter

from app.api.routes.v1 import jobs

api_router = APIRouter()
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])


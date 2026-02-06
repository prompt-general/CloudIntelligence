from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def v1_root():
    return {"message": "Welcome to API v1"}

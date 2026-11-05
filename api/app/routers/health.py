"""Responsible for the health check that the deployed site is probed with."""
from fastapi import APIRouter

router = APIRouter()


# Says the API is up. res: { status }
@router.get("/health")
def health():
    return {"status": "ok"}

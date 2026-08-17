from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas import UserResponse, CompanyProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    user = await db.get(User, current_user["id"])
    if not user:
        raise HTTPException(404, "Not found")
    return user


@router.patch("/me/profile")
async def update_profile(
    body: CompanyProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await db.get(User, current_user["id"])
    if not user:
        raise HTTPException(404, "Not found")

    if body.company_description is not None:
        user.company_description = body.company_description
    if body.company_profile is not None:
        user.company_profile = body.company_profile

    await db.commit()
    return {"message": "Profile updated"}


@router.post("/profile")
async def save_profile(
    body: CompanyProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await db.get(User, current_user["id"])
    if not user:
        raise HTTPException(404, "Not found")

    if body.company_description is not None:
        user.company_description = body.company_description
    if body.company_profile is not None:
        user.company_profile = body.company_profile

    await db.commit()
    return {
        "message": "Profile saved successfully",
        "company_description": user.company_description,
        "company_profile": user.company_profile
    }

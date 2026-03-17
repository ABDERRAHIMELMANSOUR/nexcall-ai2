from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.models.database import get_db
from app.models.ivr import IVRMenu, IVROption
from app.services.ivr_service import ivr_engine

router = APIRouter(prefix="/api/ivr", tags=["ivr"])


class MenuCreate(BaseModel):
    campaign_id: int
    name: str
    welcome_text: str
    timeout_seconds: int = 10


class OptionCreate(BaseModel):
    menu_id: int
    key_press: str
    label: str
    action: str          # info | transfer | ai_agent | submenu | hangup
    action_value: Optional[str] = None
    position: int = 0


class OptionUpdate(BaseModel):
    key_press: Optional[str] = None
    label: Optional[str] = None
    action: Optional[str] = None
    action_value: Optional[str] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/menu/{campaign_id}")
async def get_menu(campaign_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IVRMenu).where(IVRMenu.campaign_id == campaign_id))
    menu = r.scalar_one_or_none()
    if not menu:
        raise HTTPException(404, "Menu IVR introuvable")
    options = await ivr_engine.get_options(menu.id, db)
    return {**_menu_out(menu), "options": [_opt_out(o) for o in options]}


@router.post("/menu", status_code=201)
async def create_menu(body: MenuCreate, db: AsyncSession = Depends(get_db)):
    menu = IVRMenu(**body.model_dump())
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return _menu_out(menu)


@router.post("/menu/{campaign_id}/default", status_code=201)
async def create_default_menu(campaign_id: int, db: AsyncSession = Depends(get_db)):
    menu = await ivr_engine.create_default_menu(campaign_id, db)
    options = await ivr_engine.get_options(menu.id, db)
    return {**_menu_out(menu), "options": [_opt_out(o) for o in options]}


@router.put("/menu/{menu_id}")
async def update_menu(menu_id: int, body: MenuCreate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IVRMenu).where(IVRMenu.id == menu_id))
    menu = r.scalar_one_or_none()
    if not menu:
        raise HTTPException(404)
    menu.name            = body.name
    menu.welcome_text    = body.welcome_text
    menu.timeout_seconds = body.timeout_seconds
    await db.commit()
    return _menu_out(menu)


@router.post("/option", status_code=201)
async def add_option(body: OptionCreate, db: AsyncSession = Depends(get_db)):
    opt = IVROption(**body.model_dump())
    db.add(opt)
    await db.commit()
    await db.refresh(opt)
    return _opt_out(opt)


@router.put("/option/{opt_id}")
async def update_option(opt_id: int, body: OptionUpdate, db: AsyncSession = Depends(get_db)):
    r   = await db.execute(select(IVROption).where(IVROption.id == opt_id))
    opt = r.scalar_one_or_none()
    if not opt:
        raise HTTPException(404)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(opt, field, val)
    await db.commit()
    return _opt_out(opt)


@router.delete("/option/{opt_id}")
async def delete_option(opt_id: int, db: AsyncSession = Depends(get_db)):
    r   = await db.execute(select(IVROption).where(IVROption.id == opt_id))
    opt = r.scalar_one_or_none()
    if not opt:
        raise HTTPException(404)
    await db.delete(opt)
    await db.commit()
    return {"deleted": opt_id}


def _menu_out(m: IVRMenu) -> dict:
    return {"id": m.id, "campaign_id": m.campaign_id, "name": m.name,
            "welcome_text": m.welcome_text, "timeout_seconds": m.timeout_seconds}

def _opt_out(o: IVROption) -> dict:
    return {"id": o.id, "menu_id": o.menu_id, "key_press": o.key_press,
            "label": o.label, "action": o.action, "action_value": o.action_value,
            "position": o.position, "is_active": o.is_active}

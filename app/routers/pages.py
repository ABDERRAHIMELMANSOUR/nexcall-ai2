from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TMPL_DIR = Path(__file__).resolve().parent.parent / "templates"
templates  = Jinja2Templates(directory=str(_TMPL_DIR))
router     = APIRouter(tags=["pages"])


@router.get("/",            response_class=HTMLResponse)
@router.get("/dashboard",   response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "page": "dashboard"})


@router.get("/calls",       response_class=HTMLResponse)
async def page_calls(request: Request):
    return templates.TemplateResponse("calls.html", {"request": request, "page": "calls"})


@router.get("/leads",       response_class=HTMLResponse)
async def page_leads(request: Request):
    return templates.TemplateResponse("leads.html", {"request": request, "page": "leads"})


@router.get("/campaigns",   response_class=HTMLResponse)
async def page_campaigns(request: Request):
    return templates.TemplateResponse("campaigns.html", {"request": request, "page": "campaigns"})


@router.get("/campaigns/new", response_class=HTMLResponse)
async def page_new_campaign(request: Request):
    return templates.TemplateResponse("campaign_builder.html", {"request": request, "page": "campaigns"})


@router.get("/campaigns/{camp_id}/ivr", response_class=HTMLResponse)
async def page_ivr_builder(request: Request, camp_id: int):
    return templates.TemplateResponse("ivr_builder.html", {"request": request, "page": "campaigns", "camp_id": camp_id})


@router.get("/config",      response_class=HTMLResponse)
async def page_config(request: Request):
    return templates.TemplateResponse("config.html", {"request": request, "page": "config"})

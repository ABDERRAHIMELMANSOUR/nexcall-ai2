"""
NexCall AI — Router Pages HTML
Utilise un chemin ABSOLU pour les templates (obligatoire avec Gunicorn).
"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

# Chemin absolu vers les templates (ce fichier est dans app/routers/)
_templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active": "dashboard"})


@router.get("/calls", response_class=HTMLResponse)
async def page_calls(request: Request):
    return templates.TemplateResponse("calls.html", {"request": request, "active": "calls"})


@router.get("/leads", response_class=HTMLResponse)
async def page_leads(request: Request):
    return templates.TemplateResponse("leads.html", {"request": request, "active": "leads"})


@router.get("/campaigns", response_class=HTMLResponse)
async def page_campaigns(request: Request):
    return templates.TemplateResponse("campaigns.html", {"request": request, "active": "campaigns"})


@router.get("/configuration", response_class=HTMLResponse)
async def page_configuration(request: Request):
    return templates.TemplateResponse("configuration.html", {"request": request, "active": "configuration"})

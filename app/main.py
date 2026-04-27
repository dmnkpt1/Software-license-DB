import os

from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import crud
from app.db import DatabaseSession, get_db
from app.routers.common import (
    ROLE_LABELS,
    base_context,
    dashboard_path_for_role,
    flash,
    get_current_role,
    require_client_selection,
    require_permission,
    templates,
)
from app.routers import devices, features, licenses, payments, reports


app = FastAPI(title="Software License DB")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "hw3-secret-key"))
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(licenses.router)
app.include_router(payments.router)
app.include_router(devices.router)
app.include_router(features.router)
app.include_router(reports.router)


@app.get("/")
def index(request: Request):
    role = get_current_role(request)
    if not role:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=dashboard_path_for_role(role), status_code=status.HTTP_303_SEE_OTHER)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/login")
def login_page(request: Request, db: DatabaseSession = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=base_context(
            request,
            {
                "roles": ROLE_LABELS,
                "clients": crud.get_clients(db),
            },
        ),
    )


@app.post("/login")
def login(
    request: Request,
    role: str = Form(...),
    client_id: int | None = Form(default=None),
    db: DatabaseSession = Depends(get_db),
):
    if role not in ROLE_LABELS:
        flash(request, "error", "Choose a valid role to continue.")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if role == "client":
        if client_id is None:
            flash(request, "error", "Choose a client name to continue.")
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        client = crud.get_client(db, client_id)
        if not client:
            flash(request, "error", "Selected client was not found.")
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        request.session["client_id"] = client.client_id
        request.session["client_name"] = client.contact_name
    else:
        request.session.pop("client_id", None)
        request.session.pop("client_name", None)
    request.session["role"] = role
    return RedirectResponse(url=dashboard_path_for_role(role), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/logout")
def logout(request: Request):
    request.session.pop("role", None)
    request.session.pop("client_id", None)
    request.session.pop("client_name", None)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/client")
def client_dashboard(request: Request):
    blocked = require_permission(request, "client_dashboard")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    return templates.TemplateResponse(
        request=request,
        name="dashboards/client.html",
        context=base_context(request),
    )


@app.get("/manager")
def manager_dashboard(request: Request):
    blocked = require_permission(request, "manager_dashboard")
    if blocked:
        return blocked
    return templates.TemplateResponse(
        request=request,
        name="dashboards/manager.html",
        context=base_context(request),
    )


@app.exception_handler(404)
async def not_found_handler(_: Request, __):
    return RedirectResponse(url="/")

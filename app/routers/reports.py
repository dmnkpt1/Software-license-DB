from fastapi import APIRouter, Depends, Query, Request

from app import crud
from app.db import DatabaseSession, get_db
from app.routers.common import (
    base_context,
    get_current_client_id,
    require_any_permission,
    require_client_selection,
    require_permission,
    templates,
)


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/license-record")
def license_record_selector(
    request: Request,
    license_key: str | None = Query(default=None),
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_any_permission(request, {"report_license_record", "report_status", "report_activation"})
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    if license_key:
        return license_record(license_key, request, db)
    return templates.TemplateResponse(
        request=request,
        name="reports/license_record_selector.html",
        context=base_context(request, {"licenses": crud.get_licenses(db, client_id=client_id)}),
    )


@router.get("/license-record/{license_key}")
def license_record(license_key: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "report_license_record")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    return templates.TemplateResponse(
        request=request,
        name="reports/license_record.html",
        context=base_context(
            request,
            {"license": crud.get_license_record_report(db, license_key, client_id=client_id)},
        ),
    )


@router.get("/activation-record/{license_key}")
def activation_record(license_key: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "report_activation")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    license_row, devices = crud.get_activation_record_report(db, license_key, client_id=client_id)
    return templates.TemplateResponse(
        request=request,
        name="reports/activation_record.html",
        context=base_context(request, {"license": license_row, "devices": devices}),
    )


@router.get("/license-status/{license_key}")
def license_status(license_key: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "report_status")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    return templates.TemplateResponse(
        request=request,
        name="reports/license_status.html",
        context=base_context(request, {"report": crud.get_license_status_report(db, license_key, client_id=client_id)}),
    )

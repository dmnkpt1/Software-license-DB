from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app import crud, schemas
from app.db import DatabaseSession, get_db
from app.routers.common import (
    base_context,
    flash,
    get_current_client_id,
    require_permission,
    templates,
)


router = APIRouter(prefix="/licenses", tags=["licenses"])


def license_form_defaults() -> dict:
    return {
        "license_id": "",
        "license_key": "",
        "issue_date": "",
        "status": "inactive",
        "duration": "",
        "limit_activation": "",
        "client_id": "",
        "type_id": "",
    }


@router.get("")
def list_licenses(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "license_view")
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    return templates.TemplateResponse(
        request=request,
        name="licenses/list.html",
        context=base_context(
            request,
            {
                "licenses": crud.get_licenses(db, client_id=client_id),
            },
        ),
    )


@router.get("/create")
def create_license_form(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "license_manage")
    if blocked:
        return blocked
    return templates.TemplateResponse(
        request=request,
        name="licenses/form.html",
        context=base_context(
            request,
            {
                "mode": "create",
                "form_data": license_form_defaults(),
                "errors": [],
                "clients": crud.get_clients(db),
                "license_types": crud.get_license_types(db),
                "license_statuses": sorted(schemas.LICENSE_STATUSES),
            },
        ),
    )


@router.post("/create")
def create_license(
    request: Request,
    license_id: int = Form(...),
    license_key: str = Form(...),
    issue_date: str = Form(...),
    status_value: str = Form(..., alias="status"),
    duration: int = Form(...),
    limit_activation: int = Form(...),
    client_id: int = Form(...),
    type_id: int = Form(...),
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_permission(request, "license_manage")
    if blocked:
        return blocked
    form_data = {
        "license_id": license_id,
        "license_key": license_key.strip(),
        "issue_date": issue_date,
        "status": status_value,
        "duration": duration,
        "limit_activation": limit_activation,
        "client_id": client_id,
        "type_id": type_id,
    }
    try:
        payload = schemas.LicenseCreate(**form_data)
        license_row = crud.create_license(db, payload)
    except (ValidationError, ValueError) as exc:
        errors = [error["msg"] for error in exc.errors()] if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(
            request=request,
            name="licenses/form.html",
            context=base_context(
                request,
                {
                    "mode": "create",
                    "form_data": form_data,
                    "errors": errors,
                    "clients": crud.get_clients(db),
                    "license_types": crud.get_license_types(db),
                    "license_statuses": sorted(schemas.LICENSE_STATUSES),
                },
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    flash(request, "success", f"License {license_row.license_key} created successfully.")
    return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{license_key}/edit")
def edit_license_form(license_key: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "license_manage")
    if blocked:
        return blocked
    license_row = crud.get_license(db, license_key)
    if not license_row:
        flash(request, "error", "License not found.")
        return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="licenses/form.html",
        context=base_context(
            request,
            {
                "mode": "edit",
                "license": license_row,
                "form_data": {
                    "license_id": license_row.license_id,
                    "license_key": license_row.license_key,
                    "issue_date": license_row.issue_date.isoformat(),
                    "status": license_row.status,
                    "duration": license_row.duration,
                    "limit_activation": license_row.limit_activation,
                    "client_id": license_row.client_id,
                    "type_id": license_row.type_id,
                },
                "errors": [],
                "clients": crud.get_clients(db),
                "license_types": crud.get_license_types(db),
                "license_statuses": sorted(schemas.LICENSE_STATUSES),
            },
        ),
    )


@router.post("/{license_key}/edit")
def edit_license(
    license_key: str,
    request: Request,
    status_value: str = Form(..., alias="status"),
    duration: int = Form(...),
    limit_activation: int = Form(...),
    type_id: int = Form(...),
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_permission(request, "license_manage")
    if blocked:
        return blocked
    license_row = crud.get_license(db, license_key)
    if not license_row:
        flash(request, "error", "License not found.")
        return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)

    form_data = {
        "license_id": license_row.license_id,
        "license_key": license_row.license_key,
        "issue_date": license_row.issue_date.isoformat(),
        "status": status_value,
        "duration": duration,
        "limit_activation": limit_activation,
        "client_id": license_row.client_id,
        "type_id": type_id,
    }
    try:
        payload = schemas.LicenseUpdate(
            status=status_value,
            duration=duration,
            limit_activation=limit_activation,
            type_id=type_id,
        )
        crud.update_license(db, license_key, payload)
    except (ValidationError, ValueError) as exc:
        errors = [error["msg"] for error in exc.errors()] if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(
            request=request,
            name="licenses/form.html",
            context=base_context(
                request,
                {
                    "mode": "edit",
                    "license": license_row,
                    "form_data": form_data,
                    "errors": errors,
                    "clients": crud.get_clients(db),
                    "license_types": crud.get_license_types(db),
                    "license_statuses": sorted(schemas.LICENSE_STATUSES),
                },
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    flash(request, "success", f"License {license_key} updated successfully.")
    return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{license_key}/delete")
def delete_license(license_key: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "license_manage")
    if blocked:
        return blocked
    try:
        crud.delete_license(db, license_key)
        flash(request, "success", f"License {license_key} deleted.")
    except ValueError as exc:
        flash(request, "error", str(exc))
    return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app import crud, schemas
from app.db import DatabaseSession, get_db
from app.routers.common import base_context, flash, get_current_client_id, require_client_selection, require_permission, templates


router = APIRouter(prefix="/devices", tags=["devices"])


def device_form_defaults() -> dict:
    return {
        "license_key": "",
        "hardware_id": "",
        "device_status": "active",
        "activation_date": "",
    }


@router.get("")
def list_devices(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "device_activate")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    return templates.TemplateResponse(
        request=request,
        name="devices/list.html",
        context=base_context(request, {"devices": crud.get_devices(db, client_id=client_id)}),
    )


@router.get("/create")
def create_device_form(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "device_activate")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    return templates.TemplateResponse(
        request=request,
        name="devices/form.html",
        context=base_context(
            request,
            {
                "mode": "create",
                "form_data": device_form_defaults(),
                "errors": [],
                "licenses": crud.get_licenses(db, client_id=client_id),
                "device_statuses": sorted(schemas.DEVICE_STATUSES),
            },
        ),
    )


@router.post("/create")
def create_device(
    request: Request,
    license_key: str = Form(...),
    hardware_id: str = Form(...),
    device_status: str = Form(...),
    activation_date: str = Form(...),
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_permission(request, "device_activate")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    form_data = {
        "license_key": license_key,
        "hardware_id": hardware_id.strip(),
        "device_status": device_status,
        "activation_date": activation_date,
    }
    try:
        payload = schemas.DeviceCreate(**form_data)
        license_row = crud.get_license(db, license_key, client_id=client_id)
        if not license_row:
            raise ValueError("You can only activate devices for your own licenses.")
        crud.create_device(db, payload)
    except (ValidationError, ValueError) as exc:
        errors = [error["msg"] for error in exc.errors()] if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(
            request=request,
            name="devices/form.html",
            context=base_context(
                request,
                {
                    "mode": "create",
                    "form_data": form_data,
                    "errors": errors,
                    "licenses": crud.get_licenses(db, client_id=client_id),
                    "device_statuses": sorted(schemas.DEVICE_STATUSES),
                },
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    flash(request, "success", f"Device {hardware_id} activated for {license_key}.")
    return RedirectResponse(url="/devices", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{license_key}/{hardware_id}/edit")
def edit_device_form(license_key: str, hardware_id: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "device_activate")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    device = crud.get_device(db, license_key, hardware_id, client_id=client_id)
    if not device:
        flash(request, "error", "Device activation record not found.")
        return RedirectResponse(url="/devices", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="devices/form.html",
        context=base_context(
            request,
            {
                "mode": "edit",
                "device": device,
                "form_data": {
                    "license_key": device.license_key,
                    "hardware_id": device.hardware_id,
                    "device_status": device.device_status,
                    "activation_date": device.activation_date.isoformat(),
                },
                "errors": [],
                "licenses": crud.get_licenses(db, client_id=client_id),
                "device_statuses": sorted(schemas.DEVICE_STATUSES),
            },
        ),
    )


@router.post("/{license_key}/{hardware_id}/edit")
def edit_device(
    license_key: str,
    hardware_id: str,
    request: Request,
    device_status: str = Form(...),
    activation_date: str = Form(...),
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_permission(request, "device_activate")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    device = crud.get_device(db, license_key, hardware_id, client_id=client_id)
    if not device:
        flash(request, "error", "Device activation record not found.")
        return RedirectResponse(url="/devices", status_code=status.HTTP_303_SEE_OTHER)
    form_data = {
        "license_key": license_key,
        "hardware_id": hardware_id,
        "device_status": device_status,
        "activation_date": activation_date,
    }
    try:
        payload = schemas.DeviceUpdate(device_status=device_status, activation_date=activation_date)
        crud.update_device(db, license_key, hardware_id, payload)
    except (ValidationError, ValueError) as exc:
        errors = [error["msg"] for error in exc.errors()] if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(
            request=request,
            name="devices/form.html",
            context=base_context(
                request,
                {
                    "mode": "edit",
                    "device": device,
                    "form_data": form_data,
                    "errors": errors,
                    "licenses": crud.get_licenses(db, client_id=client_id),
                    "device_statuses": sorted(schemas.DEVICE_STATUSES),
                },
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    flash(request, "success", f"Device {hardware_id} updated.")
    return RedirectResponse(url="/devices", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{license_key}/{hardware_id}/delete")
def delete_device(license_key: str, hardware_id: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "device_activate")
    if blocked:
        return blocked
    blocked = require_client_selection(request)
    if blocked:
        return blocked
    client_id = get_current_client_id(request)
    try:
        device = crud.get_device(db, license_key, hardware_id, client_id=client_id)
        if not device:
            raise ValueError("Device activation record not found.")
        crud.delete_device(db, license_key, hardware_id)
        flash(request, "success", f"Device {hardware_id} deleted.")
    except ValueError as exc:
        flash(request, "error", str(exc))
    return RedirectResponse(url="/devices", status_code=status.HTTP_303_SEE_OTHER)

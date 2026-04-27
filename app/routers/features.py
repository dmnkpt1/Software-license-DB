from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app import crud, schemas
from app.db import DatabaseSession, get_db
from app.routers.common import base_context, flash, require_permission, templates


router = APIRouter(tags=["features"])


@router.get("/licenses/{license_key}/features")
def edit_features_form(license_key: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "features")
    if blocked:
        return blocked
    license_row = crud.get_license(db, license_key)
    if not license_row:
        flash(request, "error", "License not found.")
        return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="features/form.html",
        context=base_context(
            request,
            {
                "license": license_row,
                "features": crud.get_features(db),
                "selected_feature_ids": crud.get_assigned_feature_ids(db, license_key),
                "errors": [],
            },
        ),
    )


@router.post("/licenses/{license_key}/features")
def update_features(
    license_key: str,
    request: Request,
    feature_ids: list[int] = Form(default=[]),
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_permission(request, "features")
    if blocked:
        return blocked
    license_row = crud.get_license(db, license_key)
    if not license_row:
        flash(request, "error", "License not found.")
        return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)
    try:
        payload = schemas.FeatureAssignmentUpdate(license_key=license_key, feature_ids=feature_ids)
        crud.replace_license_features(db, license_key, payload.feature_ids)
    except (ValidationError, ValueError) as exc:
        errors = [error["msg"] for error in exc.errors()] if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(
            request=request,
            name="features/form.html",
            context=base_context(
                request,
                {
                    "license": license_row,
                    "features": crud.get_features(db),
                    "selected_feature_ids": feature_ids,
                    "errors": errors,
                },
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    flash(request, "success", f"Features updated for license {license_key}.")
    return RedirectResponse(url=f"/licenses/{license_key}/features", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/licenses/{license_key}/features/{feature_id}/delete")
def delete_feature_assignment(
    license_key: str,
    feature_id: int,
    request: Request,
    db: DatabaseSession = Depends(get_db),
):
    blocked = require_permission(request, "features")
    if blocked:
        return blocked
    try:
        crud.delete_feature_assignment(db, license_key, feature_id)
        flash(request, "success", f"Feature {feature_id} removed from license {license_key}.")
    except ValueError as exc:
        flash(request, "error", str(exc))
    return RedirectResponse(url=f"/licenses/{license_key}/features", status_code=status.HTTP_303_SEE_OTHER)

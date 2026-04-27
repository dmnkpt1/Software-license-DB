from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from app import crud
from app.db import DatabaseSession, get_db
from app.routers.common import base_context, flash, require_permission, templates


router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("")
def list_payments(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "payments")
    if blocked:
        return blocked
    return templates.TemplateResponse(
        request=request,
        name="payments/list.html",
        context=base_context(request, {"payments": crud.get_payments(db)}),
    )


@router.get("/create")
def create_payment_form(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "payments")
    if blocked:
        return blocked
    flash(request, "error", "Payment confirmation is read-only and not automated in this application.")
    return RedirectResponse(url="/payments", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/create")
def create_payment(request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "payments")
    if blocked:
        return blocked
    flash(request, "error", "Payment confirmation is read-only and not automated in this application.")
    return RedirectResponse(url="/payments", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{transaction_id}/edit")
def edit_payment_form(transaction_id: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "payments")
    if blocked:
        return blocked
    flash(request, "error", "Payment confirmation is read-only and not automated in this application.")
    return RedirectResponse(url="/payments", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{transaction_id}/edit")
def edit_payment(transaction_id: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "payments")
    if blocked:
        return blocked
    flash(request, "error", "Payment confirmation is read-only and not automated in this application.")
    return RedirectResponse(url="/payments", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{transaction_id}/delete")
def delete_payment(transaction_id: str, request: Request, db: DatabaseSession = Depends(get_db)):
    blocked = require_permission(request, "payments")
    if blocked:
        return blocked
    flash(request, "error", "Payment confirmation is read-only and not automated in this application.")
    return RedirectResponse(url="/payments", status_code=status.HTTP_303_SEE_OTHER)

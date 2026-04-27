from collections.abc import Mapping

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")

ROLE_LABELS = {
    "client": "Client",
    "license_manager": "License Manager",
}

ROLE_PERMISSIONS = {
    "client": {
        "client_dashboard",
        "license_view",
        "device_activate",
        "report_status",
        "report_activation",
    },
    "license_manager": {
        "manager_dashboard",
        "license_view",
        "license_manage",
        "payments",
        "features",
        "report_license_record",
        "report_status",
        "report_activation",
    },
}


def flash(request: Request, category: str, text: str) -> None:
    request.session.setdefault("messages", [])
    request.session["messages"].append({"category": category, "text": text})


def get_current_role(request: Request) -> str | None:
    role = request.session.get("role")
    if role in ROLE_PERMISSIONS:
        return role
    return None


def has_permission(request: Request, permission: str) -> bool:
    role = get_current_role(request)
    return bool(role and permission in ROLE_PERMISSIONS.get(role, set()))


def require_permission(request: Request, permission: str) -> RedirectResponse | None:
    role = get_current_role(request)
    if not role:
        flash(request, "error", "Select a role first to open the application.")
        return RedirectResponse(url="/login", status_code=303)
    if permission not in ROLE_PERMISSIONS.get(role, set()):
        flash(request, "error", "That page is not available for the selected role.")
        return RedirectResponse(url="/", status_code=303)
    return None


def require_any_permission(request: Request, permissions: set[str] | list[str] | tuple[str, ...]) -> RedirectResponse | None:
    role = get_current_role(request)
    if not role:
        flash(request, "error", "Select a role first to open the application.")
        return RedirectResponse(url="/login", status_code=303)
    allowed = ROLE_PERMISSIONS.get(role, set())
    if not any(permission in allowed for permission in permissions):
        flash(request, "error", "That page is not available for the selected role.")
        return RedirectResponse(url="/", status_code=303)
    return None


def dashboard_path_for_role(role: str | None) -> str:
    if role == "client":
        return "/client"
    if role == "license_manager":
        return "/manager"
    return "/login"


def get_current_client_id(request: Request) -> int | None:
    role = get_current_role(request)
    if role != "client":
        return None
    client_id = request.session.get("client_id")
    return client_id if isinstance(client_id, int) else None


def get_current_client_name(request: Request) -> str | None:
    role = get_current_role(request)
    if role != "client":
        return None
    client_name = request.session.get("client_name")
    return client_name if isinstance(client_name, str) else None


def require_client_selection(request: Request) -> RedirectResponse | None:
    if get_current_role(request) == "client" and get_current_client_id(request) is None:
        flash(request, "error", "Choose a client record to continue.")
        return RedirectResponse(url="/login", status_code=303)
    return None


def base_context(request: Request, extra: Mapping | None = None) -> dict:
    role = get_current_role(request)
    context = {
        "request": request,
        "messages": request.session.pop("messages", []),
        "current_role": role,
        "role_label": ROLE_LABELS.get(role),
        "permissions": ROLE_PERMISSIONS.get(role, set()),
        "selected_client_id": get_current_client_id(request),
        "selected_client_name": get_current_client_name(request),
    }
    if extra:
        context.update(extra)
    return context

from __future__ import annotations

import copy

from q_cura_api.api_client import get, post, put
from q_cura_api.utils import get_reference_id, required_text

PROFILE = "http://curafhir.dk/p/CuraCarePlan"


def _clean_new_resource(resource: dict) -> dict:
    body = copy.deepcopy(resource)
    body.pop("id", None)
    meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
    for field in ("versionId", "lastUpdated", "extension"):
        meta.pop(field, None)
    body["meta"] = meta
    return body


def normalise_forloeb(resource: dict) -> dict:
    subject = resource.get("subject") or {}
    return {
        "forloeb_id": str(resource.get("id") or ""),
        "forloeb_reference": (
            f"CarePlan/{resource.get('id')}" if resource.get("id") else ""
        ),
        "borger_reference": str(subject.get("reference") or ""),
        "borger_id": get_reference_id(subject, "Patient"),
        "status": str(resource.get("status") or ""),
        "period": resource.get("period") or {},
        "raw_resource": resource,
    }


def get_forloeb_by_id(forloeb_id: str, raw: bool = False):
    forloeb_id = required_text(forloeb_id, "forloeb_id")
    resource = get(f"CarePlan/{forloeb_id}", raw=True)
    return resource if raw else normalise_forloeb(resource)


def build_forloeb(
    template_resource: dict,
    borger_id: str,
    *,
    start_datetime: str | None = None,
) -> dict:
    """Bygger et nyt forløb fra en godkendt RAW-standardresource."""
    if not isinstance(template_resource, dict):
        raise TypeError("template_resource skal være en dictionary")
    body = _clean_new_resource(template_resource)
    body["subject"] = {
        "reference": f"Patient/{required_text(borger_id, 'borger_id')}"
    }
    if start_datetime:
        period = body.get("period") if isinstance(body.get("period"), dict) else {}
        period["start"] = start_datetime
        body["period"] = period
    return body


def create_forloeb(
    template_resource: dict,
    borger_id: str,
    *,
    start_datetime: str | None = None,
    raw: bool = False,
):
    body = build_forloeb(
        template_resource,
        borger_id,
        start_datetime=start_datetime,
    )
    created = post("CarePlan", body, raw=False)
    return created if raw else normalise_forloeb(created)


def update_forloeb(
    forloeb_id: str,
    updated_resource: dict,
    *,
    raw: bool = False,
):
    """Gemmer en komplet, allerede ændret CarePlan-resource."""
    forloeb_id = required_text(forloeb_id, "forloeb_id")
    if updated_resource.get("id") != forloeb_id:
        raise ValueError("updated_resource.id matcher ikke forloeb_id")
    put(f"CarePlan/{forloeb_id}", updated_resource, raw=False)
    verified = get(f"CarePlan/{forloeb_id}", raw=True)
    return verified if raw else normalise_forloeb(verified)

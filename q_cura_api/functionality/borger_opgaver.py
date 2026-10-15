from __future__ import annotations

from typing import Any

from q_cura_api.api_client import get, put
from q_cura_api.functionality.fhir_helpers import (
    find_extension,
    get_reference,
    get_reference_id,
    set_reference_extension,
    validate_profile,
)

PROFILE = "http://curafhir.dk/p/CuraSimpleTask"
EXTENSION_FOR = "http://curafhir.dk/x/CuraSimpleTask/for"
EXTENSION_MANAGING_ORGANIZATION = (
    "http://curafhir.dk/x/CuraSimpleTask/managingOrganization"
)
EXTENSION_STATUS = "http://curafhir.dk/x/task/status"


def normalize_task(resource: dict[str, Any]) -> dict[str, Any]:
    """Normaliserer en CuraSimpleTask til de vigtigste relationer."""
    validate_profile(resource, PROFILE)
    extensions = resource.get("extension") or []
    citizen_extension = find_extension(extensions, EXTENSION_FOR) or {}
    organization_extension = (
        find_extension(extensions, EXTENSION_MANAGING_ORGANIZATION) or {}
    )
    status_extension = find_extension(extensions, EXTENSION_STATUS) or {}
    communication_reference = get_reference(resource.get("subject"))
    citizen_reference = get_reference(citizen_extension.get("valueReference"))
    organization_reference = get_reference(
        organization_extension.get("valueReference")
    )
    return {
        "task_id": str(resource.get("id") or ""),
        "task_reference": f"Basic/{resource.get('id')}" if resource.get("id") else "",
        "communication_reference": communication_reference,
        "communication_id": get_reference_id(
            communication_reference, "Communication"
        ),
        "citizen_reference": citizen_reference,
        "citizen_id": get_reference_id(citizen_reference, "Patient"),
        "managing_organization_reference": organization_reference,
        "managing_organization_id": get_reference_id(
            organization_reference, "Organization"
        ),
        "status": str(status_extension.get("valueCode") or ""),
        "raw_resource": resource,
    }


def get_task_by_id(task_id: str, raw: bool = False):
    """Henter en konkret CuraSimpleTask."""
    resource = get(f"Basic/{task_id}", raw=True)
    return resource if raw else normalize_task(resource)


def build_task_organization_update(
    resource: dict[str, Any], organization_id: str
) -> dict[str, Any]:
    """Bygger PUT-body uden at skrive til CURA."""
    validate_profile(resource, PROFILE)
    return set_reference_extension(
        resource,
        EXTENSION_MANAGING_ORGANIZATION,
        f"Organization/{organization_id}",
    )


def update_task_managing_organization(
    task_id: str,
    organization_id: str,
    *,
    dry_run: bool = True,
    raw: bool = False,
):
    """Aendrer opgavens managingOrganization og verificerer bagefter."""
    current = get(f"Basic/{task_id}", raw=True)
    body = build_task_organization_update(current, organization_id)
    if dry_run:
        return {"dry_run": True, "endpoint": f"Basic/{task_id}", "body": body}
    put(f"Basic/{task_id}", body, raw=True)
    verified = get(f"Basic/{task_id}", raw=True)
    normalized = normalize_task(verified)
    if normalized["managing_organization_id"] != organization_id:
        raise RuntimeError("Opgavens organisation blev ikke opdateret som forventet")
    return verified if raw else normalized

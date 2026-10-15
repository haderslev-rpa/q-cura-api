from __future__ import annotations

from q_cura_api.api_client import get, post, put
from q_cura_api.utils import (
    bundle_resources,
    get_extension_boolean,
    get_extension_reference,
    get_reference_id,
    required_text,
    set_boolean_extension,
    set_reference_extension,
)

PROFILE = "http://curafhir.dk/p/RehabilitationPlanMapping"
EXTENSION_REHABILITATION_PLAN = (
    "http://curafhir.dk/x/RehabilitationPlanMapping/rehabilitationPlan"
)
EXTENSION_RELATES_TO = (
    "http://curafhir.dk/x/RehabilitationPlanMapping/relatesTo"
)
EXTENSION_IS_ACTIVE = (
    "http://curafhir.dk/x/RehabilitationPlanMapping/isActive"
)


def normalise_mapping(resource: dict) -> dict:
    communication_reference = get_extension_reference(
        resource, EXTENSION_REHABILITATION_PLAN
    )
    care_plan_reference = get_extension_reference(resource, EXTENSION_RELATES_TO)
    subject = resource.get("subject") or {}
    return {
        "mapping_id": str(resource.get("id") or ""),
        "communication_reference": communication_reference,
        "communication_id": get_reference_id(
            communication_reference, "Communication"
        ),
        "forloeb_reference": care_plan_reference,
        "forloeb_id": get_reference_id(care_plan_reference, "CarePlan"),
        "borger_reference": str(subject.get("reference") or ""),
        "borger_id": get_reference_id(subject, "Patient"),
        "is_active": get_extension_boolean(resource, EXTENSION_IS_ACTIVE),
        "raw_resource": resource,
    }


def get_mapping_by_id(mapping_id: str, raw: bool = False):
    mapping_id = required_text(mapping_id, "mapping_id")
    resource = get(f"Basic/{mapping_id}", raw=True)
    return resource if raw else normalise_mapping(resource)


def build_mapping(
    borger_id: str,
    communication_id: str,
    forloeb_id: str,
) -> dict:
    return {
        "resourceType": "Basic",
        "meta": {"profile": [PROFILE]},
        "extension": [
            {
                "url": EXTENSION_REHABILITATION_PLAN,
                "valueReference": {
                    "reference": f"Communication/{communication_id}"
                },
            },
            {
                "url": EXTENSION_RELATES_TO,
                "valueReference": {"reference": f"CarePlan/{forloeb_id}"},
            },
            {"url": EXTENSION_IS_ACTIVE, "valueBoolean": True},
        ],
        "code": {
            "coding": [
                {
                    "system": "http://curafhir.dk/p",
                    "code": "RehabilitationPlanMapping",
                }
            ]
        },
        "subject": {"reference": f"Patient/{borger_id}"},
    }


def create_mapping(
    borger_id: str,
    communication_id: str,
    forloeb_id: str,
    *,
    raw: bool = False,
):
    body = build_mapping(
        required_text(borger_id, "borger_id"),
        required_text(communication_id, "communication_id"),
        required_text(forloeb_id, "forloeb_id"),
    )
    created = post("Basic", body, raw=False)
    return created if raw else normalise_mapping(created)


def update_mapping_forloeb(
    mapping_id: str,
    forloeb_id: str,
    *,
    raw: bool = False,
):
    resource = get(f"Basic/{mapping_id}", raw=True)
    body = set_reference_extension(
        resource,
        EXTENSION_RELATES_TO,
        f"CarePlan/{forloeb_id}",
    )
    put(f"Basic/{mapping_id}", body, raw=False)
    verified = get(f"Basic/{mapping_id}", raw=True)
    result = normalise_mapping(verified)
    if result["forloeb_id"] != forloeb_id:
        raise RuntimeError("Mappingen peger ikke på det forventede forløb")
    return verified if raw else result


def set_mapping_active(
    mapping_id: str,
    is_active: bool,
    *,
    raw: bool = False,
):
    resource = get(f"Basic/{mapping_id}", raw=True)
    body = set_boolean_extension(resource, EXTENSION_IS_ACTIVE, is_active)
    put(f"Basic/{mapping_id}", body, raw=False)
    verified = get(f"Basic/{mapping_id}", raw=True)
    return verified if raw else normalise_mapping(verified)

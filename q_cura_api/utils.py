from __future__ import annotations

from copy import deepcopy
from typing import Any


def required_text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field_name} skal være udfyldt")
    return result


def get_reference(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("reference") or "").strip()
    return ""


def get_reference_id(value: Any, expected_type: str | None = None) -> str:
    reference = get_reference(value)
    if "/" not in reference:
        return ""
    resource_type, resource_id = reference.split("/", 1)
    if expected_type and resource_type != expected_type:
        return ""
    return resource_id.strip()


def get_profiles(resource: dict) -> list[str]:
    meta = resource.get("meta") if isinstance(resource.get("meta"), dict) else {}
    profiles = meta.get("profile") if isinstance(meta.get("profile"), list) else []
    return [str(value) for value in profiles if value]


def validate_profile(resource: dict, expected_profile: str) -> None:
    profiles = get_profiles(resource)
    if expected_profile not in profiles:
        raise ValueError(f"Forventede profil {expected_profile}, men fandt {profiles}")


def find_extension(extensions: Any, extension_url: str) -> dict | None:
    if not isinstance(extensions, list):
        return None
    for extension in extensions:
        if isinstance(extension, dict) and extension.get("url") == extension_url:
            return extension
    return None


def get_extension(resource: dict, extension_url: str) -> dict | None:
    return find_extension(resource.get("extension"), extension_url)


def get_extension_reference(resource: dict, extension_url: str) -> str:
    extension = get_extension(resource, extension_url) or {}
    return get_reference(extension.get("valueReference"))


def get_extension_boolean(resource: dict, extension_url: str) -> bool | None:
    extension = get_extension(resource, extension_url) or {}
    value = extension.get("valueBoolean")
    return value if isinstance(value, bool) else None


def set_reference_extension(resource: dict, extension_url: str, reference: str) -> dict:
    updated = deepcopy(resource)
    extension = get_extension(updated, extension_url)
    if extension is None:
        raise ValueError(f"Resource mangler extension {extension_url}")
    extension["valueReference"] = {"reference": required_text(reference, "reference")}
    return updated


def set_boolean_extension(resource: dict, extension_url: str, value: bool) -> dict:
    updated = deepcopy(resource)
    extension = get_extension(updated, extension_url)
    if extension is None:
        raise ValueError(f"Resource mangler extension {extension_url}")
    extension["valueBoolean"] = bool(value)
    return updated


def bundle_resources(bundle: Any, resource_type: str | None = None) -> list[dict]:
    if not isinstance(bundle, dict):
        return []
    result = []
    for entry in bundle.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            continue
        if resource_type and resource.get("resourceType") != resource_type:
            continue
        result.append(resource)
    return result

"""
OPRET PLAN-MAPPING I CURA
=========================

Modulet opretter en FHIR Basic-resource, som forbinder en eksisterende plan med
en eksisterende målresource. Den offentlige, konkrete hjælpefunktion er:

    opret_rehabilitation_plan_mapping(...)

For RehabilitationPlanMapping er den dokumenterede kæde:

    Communication/CuraRehabilitationPlan
        <- RehabilitationPlanMapping/rehabilitationPlan
    Basic/RehabilitationPlanMapping
        -> RehabilitationPlanMapping/relatesTo
    CarePlan/CuraCarePlan

Obligatoriske input er derfor:

    borger_id
    communication_id
    care_plan_id

Funktionen opretter ikke Communication eller CarePlan. Begge ressourcer skal
findes på forhånd og tilhøre samme Patient.

SIKKERHED
---------
Før POST udføres læsende kontroller af Communication, CarePlan og eksisterende
mappings. Ved dry_run=True bygges og returneres request body, men der sendes
ingen POST. Ved dry_run=False udføres præcis ét skrivende kald: POST Basic.
Den nye Basic-resource hentes derefter igen med GET og verificeres.

UDVIDELSE
---------
PLAN_MAPPING_TYPER er oversætteren. En ny mappingtype tilføjes ved at registrere
resource types, profiler, extension-URL'er, kode og skabelonfil. Den generelle
funktion opret_plan_mapping() bruger denne konfiguration. Nye typer må først
tilføjes, når en rigtig RAW-resource har dokumenteret strukturen.

LEVERANDØR
----------
RehabilitationPlanMapping har ingen dokumenteret leverandør. Leverandør er
 derfor ikke et input til denne funktion. Leverandør hører til de ressourcer,
hvor feltet faktisk er dokumenteret, eksempelvis CarePlan eller ProcedureRequest.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from q_cura_api.api_client import get, post


SKABELON_MAPPE = Path(__file__).resolve().parent.parent / "skabeloner"

PLAN_MAPPING_TYPER = {
    "rehabilitation_plan": {
        "skabelon": "rehabilitation_plan_mapping.json",
        "mapping_resource_type": "Basic",
        "mapping_profile": "http://curafhir.dk/p/RehabilitationPlanMapping",
        "mapping_code_system": "http://curafhir.dk/p",
        "mapping_code": "RehabilitationPlanMapping",
        "plan_resource_type": "Communication",
        "plan_profile": "http://curafhir.dk/p/CuraRehabilitationPlan",
        "target_resource_type": "CarePlan",
        "target_profile": "http://curafhir.dk/p/CuraCarePlan",
        "plan_extension_url": (
            "http://curafhir.dk/x/RehabilitationPlanMapping/rehabilitationPlan"
        ),
        "target_extension_url": (
            "http://curafhir.dk/x/RehabilitationPlanMapping/relatesTo"
        ),
        "active_extension_url": (
            "http://curafhir.dk/x/RehabilitationPlanMapping/isActive"
        ),
    },
}


def _required_text(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} skal angives.")
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst.")
    validated = value.strip()
    if not validated:
        raise ValueError(f"{field_name} må ikke være tom.")
    return validated


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst eller None.")
    return value.strip() or None


def _validate_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} skal være True eller False.")
    return value


def _strip_reference_prefix(value: str, resource_type: str) -> str:
    value = _required_text(value, resource_type.lower() + "_id")
    prefix = f"{resource_type}/"
    return value[len(prefix):].strip() if value.startswith(prefix) else value


def _get_profiles(resource: dict) -> list[str]:
    meta = resource.get("meta", {})
    if not isinstance(meta, dict):
        return []
    profiles = meta.get("profile", [])
    if not isinstance(profiles, list):
        return []
    return [str(profile) for profile in profiles]


def _get_reference(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("reference") or "").strip()
    return ""


def _get_extensions(resource: dict) -> list:
    extensions = resource.get("extension")
    if not isinstance(extensions, list):
        extensions = []
        resource["extension"] = extensions
    return extensions


def _find_extension(resource: dict, extension_url: str) -> dict | None:
    for extension in _get_extensions(resource):
        if isinstance(extension, dict) and extension.get("url") == extension_url:
            return extension
    return None


def _require_extension(resource: dict, extension_url: str) -> dict:
    extension = _find_extension(resource, extension_url)
    if extension is None:
        raise ValueError(f"Skabelonen eller ressourcen mangler extension: {extension_url}")
    return extension


def _extension_reference(resource: dict, extension_url: str) -> str:
    extension = _find_extension(resource, extension_url)
    if extension is None:
        return ""
    return _get_reference(extension.get("valueReference"))


def _extension_boolean(resource: dict, extension_url: str) -> bool | None:
    extension = _find_extension(resource, extension_url)
    if extension is None:
        return None
    value = extension.get("valueBoolean")
    return value if isinstance(value, bool) else None


def _load_template(file_name: str) -> dict:
    path = SKABELON_MAPPE / _required_text(file_name, "file_name")
    if not path.is_file():
        raise FileNotFoundError(f"Mapping-skabelonen findes ikke: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Mapping-skabelonen er tom: {path}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Mapping-skabelonen indeholder ugyldig JSON: {path}. "
            f"Linje {error.lineno}, kolonne {error.colno}: {error.msg}"
        ) from error
    if not isinstance(data, dict):
        raise TypeError("Mapping-skabelonen skal indeholde et JSON-objekt.")
    return deepcopy(data)


def _clean_server_fields(resource: dict) -> None:
    resource.pop("id", None)
    resource.pop("identifier", None)
    resource.pop("implicitRules", None)
    meta = resource.get("meta")
    if isinstance(meta, dict):
        for field_name in ("versionId", "lastUpdated", "security", "extension"):
            meta.pop(field_name, None)


def _validate_resource(
    resource: Any,
    *,
    expected_resource_type: str,
    expected_profile: str,
    expected_subject: str,
    label: str,
) -> dict:
    if not isinstance(resource, dict):
        raise RuntimeError(f"{label} blev ikke returneret som en dictionary.")
    if resource.get("resourceType") != expected_resource_type:
        raise RuntimeError(
            f"{label} har forkert resourceType. Forventet: {expected_resource_type}. "
            f"Fundet: {resource.get('resourceType')}."
        )
    profiles = _get_profiles(resource)
    if expected_profile not in profiles:
        raise ValueError(
            f"{label} mangler den forventede profil {expected_profile!r}. "
            f"Fundne profiler: {profiles}."
        )
    actual_subject = _get_reference(resource.get("subject"))
    if actual_subject != expected_subject:
        raise ValueError(
            f"{label} tilhører ikke den forventede borger. "
            f"Forventet: {expected_subject}. Fundet: {actual_subject}."
        )
    return resource


def _get_mapping_config(mapping_type: str) -> dict:
    validated_type = _required_text(mapping_type, "mapping_type")
    config = PLAN_MAPPING_TYPER.get(validated_type)
    if config is None:
        raise ValueError(
            f"Ukendt mapping_type: {validated_type!r}. "
            f"Tilladte værdier: {sorted(PLAN_MAPPING_TYPER)}"
        )
    return config


def hent_tilgængelige_mappingtyper() -> list[str]:
    return sorted(PLAN_MAPPING_TYPER)


def build_plan_mapping(
    mapping_type: str,
    borger_id: str,
    plan_id: str,
    target_id: str,
    *,
    is_active: bool = True,
) -> dict:
    """Bygger en komplet mapping-resource uden at sende API-kald."""
    config = _get_mapping_config(mapping_type)
    borger_id = _strip_reference_prefix(borger_id, "Patient")
    plan_id = _strip_reference_prefix(plan_id, config["plan_resource_type"])
    target_id = _strip_reference_prefix(target_id, config["target_resource_type"])
    is_active = _validate_bool(is_active, "is_active")

    body = _load_template(config["skabelon"])
    if body.get("resourceType") != config["mapping_resource_type"]:
        raise ValueError("Mapping-skabelonens resourceType matcher ikke konfigurationen.")
    profiles = _get_profiles(body)
    if config["mapping_profile"] not in profiles:
        raise ValueError("Mapping-skabelonen mangler den konfigurerede mapping-profil.")

    body["subject"] = {"reference": f"Patient/{borger_id}"}
    _require_extension(body, config["plan_extension_url"])["valueReference"] = {
        "reference": f"{config['plan_resource_type']}/{plan_id}"
    }
    _require_extension(body, config["target_extension_url"])["valueReference"] = {
        "reference": f"{config['target_resource_type']}/{target_id}"
    }
    _require_extension(body, config["active_extension_url"])["valueBoolean"] = is_active
    _clean_server_fields(body)
    return body


def _normalise_mapping(resource: dict, mapping_type: str) -> dict:
    config = _get_mapping_config(mapping_type)
    mapping_id = str(resource.get("id") or "").strip()
    subject_reference = _get_reference(resource.get("subject"))
    plan_reference = _extension_reference(resource, config["plan_extension_url"])
    target_reference = _extension_reference(resource, config["target_extension_url"])
    return {
        "mapping_type": mapping_type,
        "mapping_id": mapping_id,
        "mapping_reference": f"Basic/{mapping_id}" if mapping_id else "",
        "plan_reference": plan_reference,
        "plan_id": plan_reference.split("/", 1)[1] if "/" in plan_reference else "",
        "target_reference": target_reference,
        "target_id": target_reference.split("/", 1)[1] if "/" in target_reference else "",
        "borger_reference": subject_reference,
        "borger_id": subject_reference.split("/", 1)[1] if "/" in subject_reference else "",
        "is_active": _extension_boolean(resource, config["active_extension_url"]),
        "raw_resource": resource,
    }


def _matches_mapping(
    resource: dict,
    *,
    mapping_type: str,
    borger_reference: str,
    plan_reference: str,
    target_reference: str,
    expected_active: bool | None,
) -> bool:
    config = _get_mapping_config(mapping_type)
    if resource.get("resourceType") != config["mapping_resource_type"]:
        return False
    if config["mapping_profile"] not in _get_profiles(resource):
        return False
    if _get_reference(resource.get("subject")) != borger_reference:
        return False
    if _extension_reference(resource, config["plan_extension_url"]) != plan_reference:
        return False
    if _extension_reference(resource, config["target_extension_url"]) != target_reference:
        return False
    if (
        expected_active is not None
        and _extension_boolean(resource, config["active_extension_url"]) is not expected_active
    ):
        return False
    return True


def find_existing_plan_mappings(
    mapping_type: str,
    borger_id: str,
    plan_id: str,
    target_id: str,
    *,
    active_only: bool = True,
) -> list[dict]:
    """
    Henter mappingprofilens Basic-resourcer og filtrerer lokalt på præcise
    referencer. Funktionen opfinder ikke profilspecifikke søgeparametre.
    """
    config = _get_mapping_config(mapping_type)
    borger_id = _strip_reference_prefix(borger_id, "Patient")
    plan_id = _strip_reference_prefix(plan_id, config["plan_resource_type"])
    target_id = _strip_reference_prefix(target_id, config["target_resource_type"])
    endpoint = "Basic?" + urlencode(
        [("_profile", config["mapping_profile"]), ("_count", "1000")],
        doseq=True,
    )
    bundle = get(endpoint, raw=True)
    if not isinstance(bundle, dict):
        raise RuntimeError("CURA returnerede ikke et Bundle som dictionary.")
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        raise RuntimeError("CURA Bundle.entry er ikke en liste.")
    expected = {
        "borger_reference": f"Patient/{borger_id}",
        "plan_reference": f"{config['plan_resource_type']}/{plan_id}",
        "target_reference": f"{config['target_resource_type']}/{target_id}",
    }
    matches = []
    for entry in entries:
        resource = entry.get("resource", {}) if isinstance(entry, dict) else {}
        if not isinstance(resource, dict):
            continue
        if _matches_mapping(
            resource,
            mapping_type=mapping_type,
            expected_active=True if active_only else None,
            **expected,
        ):
            matches.append(_normalise_mapping(resource, mapping_type))
    return matches


def _extract_created_id(post_response: dict) -> tuple[str, str]:
    location = str(
        post_response.get("location")
        or post_response.get("content_location")
        or ""
    ).strip()
    clean = location.split("?", 1)[0].rstrip("/")
    resource_id = ""
    if clean:
        parts = clean.split("/")
        resource_id = parts[-3] if len(parts) >= 3 and parts[-2] == "_history" else parts[-1]
    data = post_response.get("data")
    if not resource_id and isinstance(data, dict):
        resource_id = str(data.get("id") or "").strip()
    return resource_id, location


def opret_plan_mapping(
    mapping_type: str,
    borger_id: str,
    plan_id: str,
    target_id: str,
    *,
    is_active: bool = True,
    dry_run: bool = True,
    existing_mapping_id: str | None = None,
    raw: bool = False,
) -> dict:
    """
    Validerer, bygger og opretter en plan-mapping.

    dry_run=True udfører kun GET-kald og returnerer request_body.
    dry_run=False udfører ét POST Basic og et efterfølgende kontrol-GET.
    """
    config = _get_mapping_config(mapping_type)
    borger_id = _strip_reference_prefix(borger_id, "Patient")
    plan_id = _strip_reference_prefix(plan_id, config["plan_resource_type"])
    target_id = _strip_reference_prefix(target_id, config["target_resource_type"])
    is_active = _validate_bool(is_active, "is_active")
    dry_run = _validate_bool(dry_run, "dry_run")
    existing_mapping_id = _optional_text(existing_mapping_id, "existing_mapping_id")

    borger_reference = f"Patient/{borger_id}"
    plan_reference = f"{config['plan_resource_type']}/{plan_id}"
    target_reference = f"{config['target_resource_type']}/{target_id}"

    plan_resource = get(plan_reference, raw=True)
    _validate_resource(
        plan_resource,
        expected_resource_type=config["plan_resource_type"],
        expected_profile=config["plan_profile"],
        expected_subject=borger_reference,
        label="Planressourcen",
    )
    target_resource = get(target_reference, raw=True)
    _validate_resource(
        target_resource,
        expected_resource_type=config["target_resource_type"],
        expected_profile=config["target_profile"],
        expected_subject=borger_reference,
        label="Målressourcen",
    )

    if existing_mapping_id:
        known = get(f"Basic/{existing_mapping_id}", raw=True)
        if not isinstance(known, dict):
            raise RuntimeError("existing_mapping_id returnerede ikke en dictionary.")
        if _matches_mapping(
            known,
            mapping_type=mapping_type,
            borger_reference=borger_reference,
            plan_reference=plan_reference,
            target_reference=target_reference,
            expected_active=True,
        ):
            normalised = _normalise_mapping(known, mapping_type)
            return {
                "success": True,
                "created": False,
                "verified": True,
                "dry_run": dry_run,
                "already_exists": True,
                "message": "Den aktive mapping findes allerede.",
                **normalised,
            }
        raise ValueError("existing_mapping_id peger ikke på den forventede aktive mapping.")

    existing = find_existing_plan_mappings(
        mapping_type,
        borger_id,
        plan_id,
        target_id,
        active_only=True,
    )
    if existing:
        return {
            "success": True,
            "created": False,
            "verified": True,
            "dry_run": dry_run,
            "already_exists": True,
            "message": "En aktiv identisk mapping findes allerede.",
            "existing_mappings": existing,
        }

    body = build_plan_mapping(
        mapping_type,
        borger_id,
        plan_id,
        target_id,
        is_active=is_active,
    )
    base_result = {
        "success": True,
        "created": False,
        "verified": False,
        "dry_run": dry_run,
        "already_exists": False,
        "mapping_type": mapping_type,
        "borger_id": borger_id,
        "borger_reference": borger_reference,
        "plan_id": plan_id,
        "plan_reference": plan_reference,
        "target_id": target_id,
        "target_reference": target_reference,
        "is_active": is_active,
        "request_body": body,
    }
    if dry_run:
        return {
            **base_result,
            "message": "Dry run gennemført. Ingen POST blev sendt til CURA.",
        }

    post_response = post("Basic", body, raw=True)
    if not isinstance(post_response, dict):
        raise RuntimeError("CURA returnerede ikke et forståeligt POST-resultat.")
    mapping_id, location = _extract_created_id(post_response)
    if not mapping_id:
        raise RuntimeError(
            "Mappingen blev muligvis oprettet, men POST-svaret indeholdt ikke et id. "
            "Kør ikke oprettelsen igen, før miljøet er undersøgt med GET."
        )
    verified = get(f"Basic/{mapping_id}", raw=True)
    if not isinstance(verified, dict):
        raise RuntimeError("Kontrol-GET returnerede ikke en dictionary.")
    if not _matches_mapping(
        verified,
        mapping_type=mapping_type,
        borger_reference=borger_reference,
        plan_reference=plan_reference,
        target_reference=target_reference,
        expected_active=is_active,
    ):
        raise RuntimeError("Den oprettede mapping bestod ikke kontrol af de direkte referencer.")
    normalised = _normalise_mapping(verified, mapping_type)
    result = {
        "success": True,
        "created": True,
        "verified": True,
        "dry_run": False,
        "already_exists": False,
        "message": "Mappingen blev oprettet og verificeret.",
        "post_status_code": post_response.get("status_code"),
        "location": location,
        **normalised,
    }
    if raw:
        result["request_body"] = body
        result["post_response"] = post_response
    return result


def opret_rehabilitation_plan_mapping(
    borger_id: str,
    communication_id: str,
    care_plan_id: str,
    *,
    is_active: bool = True,
    dry_run: bool = True,
    existing_mapping_id: str | None = None,
    raw: bool = False,
) -> dict:
    """Opretter en verificeret RehabilitationPlanMapping."""
    return opret_plan_mapping(
        mapping_type="rehabilitation_plan",
        borger_id=borger_id,
        plan_id=communication_id,
        target_id=care_plan_id,
        is_active=is_active,
        dry_run=dry_run,
        existing_mapping_id=existing_mapping_id,
        raw=raw,
    )

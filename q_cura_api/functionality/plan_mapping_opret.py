"""Opretter, henter og opdaterer plan-mappings i CURA."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from q_cura_api.api_client import get, post, put


SKABELON_MAPPE = Path(__file__).resolve().parent.parent / "skabeloner"

PROFILE_REHABILITATION_PLAN_MAPPING = (
    "http://curafhir.dk/p/RehabilitationPlanMapping"
)
PROFILE_REHABILITATION_PLAN = (
    "http://curafhir.dk/p/CuraRehabilitationPlan"
)
PROFILE_CARE_PLAN = "http://curafhir.dk/p/CuraCarePlan"

EXTENSION_REHABILITATION_PLAN = (
    "http://curafhir.dk/x/"
    "RehabilitationPlanMapping/rehabilitationPlan"
)
EXTENSION_RELATES_TO = (
    "http://curafhir.dk/x/"
    "RehabilitationPlanMapping/relatesTo"
)
EXTENSION_IS_ACTIVE = (
    "http://curafhir.dk/x/"
    "RehabilitationPlanMapping/isActive"
)

PLAN_MAPPING_TYPER = {
    "rehabilitation_plan": {
        "skabelon": "rehabilitation_plan_mapping.json",
        "mapping_resource_type": "Basic",
        "mapping_profile": PROFILE_REHABILITATION_PLAN_MAPPING,
        "plan_resource_type": "Communication",
        "plan_profile": PROFILE_REHABILITATION_PLAN,
        "target_resource_type": "CarePlan",
        "target_profile": PROFILE_CARE_PLAN,
        "plan_extension_url": EXTENSION_REHABILITATION_PLAN,
        "target_extension_url": EXTENSION_RELATES_TO,
        "active_extension_url": EXTENSION_IS_ACTIVE,
    },
}


def _required_text(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} skal angives.")
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst.")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} må ikke være tom.")
    return value


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst eller None.")
    return value.strip() or None


def _required_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} skal være True eller False.")
    return value


def _strip_prefix(value: str, resource_type: str, field_name: str) -> str:
    value = _required_text(value, field_name)
    prefix = f"{resource_type}/"
    if value.startswith(prefix):
        value = value[len(prefix):].strip()
    if not value or "/" in value:
        raise ValueError(
            f"{field_name} skal være et teknisk id eller {prefix}<id>."
        )
    return value


def _profiles(resource: dict) -> list[str]:
    meta = resource.get("meta")
    if not isinstance(meta, dict):
        return []
    profiles = meta.get("profile")
    if not isinstance(profiles, list):
        return []
    return [str(profile) for profile in profiles]


def _reference(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("reference") or "").strip()
    return ""


def _extensions(resource: dict) -> list:
    extensions = resource.get("extension")
    if not isinstance(extensions, list):
        extensions = []
        resource["extension"] = extensions
    return extensions


def _find_extension(resource: dict, url: str) -> dict | None:
    return next(
        (
            extension
            for extension in _extensions(resource)
            if isinstance(extension, dict)
            and extension.get("url") == url
        ),
        None,
    )


def _require_extension(resource: dict, url: str) -> dict:
    extension = _find_extension(resource, url)
    if extension is None:
        raise ValueError(f"Ressourcen mangler extension: {url}")
    return extension


def _extension_reference(resource: dict, url: str) -> str:
    extension = _find_extension(resource, url)
    if extension is None:
        return ""
    return _reference(extension.get("valueReference"))


def _extension_boolean(resource: dict, url: str) -> bool | None:
    extension = _find_extension(resource, url)
    if extension is None:
        return None
    value = extension.get("valueBoolean")
    return value if isinstance(value, bool) else None


def _set_reference_extension(resource: dict, url: str, reference: str) -> dict:
    extension = _find_extension(resource, url)
    if extension is None:
        extension = {"url": url}
        _extensions(resource).append(extension)
    extension["valueReference"] = {"reference": reference}
    return resource


def _set_boolean_extension(resource: dict, url: str, value: bool) -> dict:
    extension = _find_extension(resource, url)
    if extension is None:
        extension = {"url": url}
        _extensions(resource).append(extension)
    extension["valueBoolean"] = value
    return resource


def _get_config(mapping_type: str) -> dict:
    mapping_type = _required_text(mapping_type, "mapping_type")
    config = PLAN_MAPPING_TYPER.get(mapping_type)
    if config is None:
        raise ValueError(
            f"Ukendt mapping_type {mapping_type!r}. "
            f"Tilladte værdier: {sorted(PLAN_MAPPING_TYPER)}"
        )
    return config


def _load_template(file_name: str) -> dict:
    path = SKABELON_MAPPE / _required_text(file_name, "file_name")
    if not path.is_file():
        raise FileNotFoundError(f"Mapping-skabelonen findes ikke: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Ugyldig JSON i {path}. "
            f"Linje {error.lineno}, kolonne {error.colno}: {error.msg}"
        ) from error
    if not isinstance(data, dict):
        raise TypeError("Mapping-skabelonen skal være et JSON-objekt.")
    return deepcopy(data)


def _validate_fhir_resource(
    resource: Any,
    *,
    expected_resource_type: str,
    expected_profile: str,
    expected_subject: str | None = None,
    label: str,
) -> dict:
    if not isinstance(resource, dict):
        raise RuntimeError(f"{label} blev ikke returneret som en dictionary.")
    if resource.get("resourceType") != expected_resource_type:
        raise RuntimeError(
            f"{label} har forkert resourceType. "
            f"Forventet {expected_resource_type!r}, "
            f"fundet {resource.get('resourceType')!r}."
        )
    if expected_profile not in _profiles(resource):
        raise ValueError(
            f"{label} mangler profilen {expected_profile!r}. "
            f"Fundne profiler: {_profiles(resource)}"
        )
    if expected_subject is not None:
        actual_subject = _reference(resource.get("subject"))
        if actual_subject != expected_subject:
            raise ValueError(
                f"{label} tilhører ikke den forventede borger. "
                f"Forventet {expected_subject!r}, fundet {actual_subject!r}."
            )
    return resource


def _bundle_resources(bundle: Any, resource_type: str) -> list[dict]:
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise RuntimeError("CURA returnerede ikke et FHIR Bundle.")
    links = bundle.get("link", [])
    if not isinstance(links, list):
        raise RuntimeError("Bundle.link er ikke en liste.")
    if any(
        isinstance(link, dict) and link.get("relation") == "next"
        for link in links
    ):
        raise RuntimeError(
            "CURA returnerede flere sider. Søgeresultatet er derfor ikke "
            "sikkert komplet, og mappinghandlingen stoppes."
        )
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        raise RuntimeError("Bundle.entry er ikke en liste.")
    resources = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Et Bundle.entry har uventet format.")
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            raise RuntimeError("Et entry.resource har uventet format.")
        if resource.get("resourceType") == resource_type:
            resources.append(resource)
    return resources


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
        if len(parts) >= 3 and parts[-2] == "_history":
            resource_id = parts[-3]
        else:
            resource_id = parts[-1]
    data = post_response.get("data")
    if not resource_id and isinstance(data, dict):
        resource_id = str(data.get("id") or "").strip()
    return resource_id, location


def hent_tilgængelige_mappingtyper() -> list[str]:
    return sorted(PLAN_MAPPING_TYPER)


def normalise_mapping(
    resource: dict,
    mapping_type: str = "rehabilitation_plan",
) -> dict:
    config = _get_config(mapping_type)
    _validate_fhir_resource(
        resource,
        expected_resource_type=config["mapping_resource_type"],
        expected_profile=config["mapping_profile"],
        label="Mappingressourcen",
    )
    mapping_id = str(resource.get("id") or "").strip()
    plan_reference = _extension_reference(
        resource,
        config["plan_extension_url"],
    )
    target_reference = _extension_reference(
        resource,
        config["target_extension_url"],
    )
    subject_reference = _reference(resource.get("subject"))
    return {
        "mapping_type": mapping_type,
        "mapping_id": mapping_id,
        "mapping_reference": f"Basic/{mapping_id}" if mapping_id else "",
        "communication_reference": plan_reference,
        "communication_id": (
            plan_reference.split("/", 1)[1]
            if plan_reference.startswith("Communication/")
            else ""
        ),
        "plan_reference": plan_reference,
        "plan_id": plan_reference.split("/", 1)[1] if "/" in plan_reference else "",
        "forloeb_reference": target_reference,
        "forloeb_id": (
            target_reference.split("/", 1)[1]
            if target_reference.startswith("CarePlan/")
            else ""
        ),
        "target_reference": target_reference,
        "target_id": target_reference.split("/", 1)[1] if "/" in target_reference else "",
        "borger_reference": subject_reference,
        "borger_id": (
            subject_reference.split("/", 1)[1]
            if subject_reference.startswith("Patient/")
            else ""
        ),
        "is_active": _extension_boolean(
            resource,
            config["active_extension_url"],
        ),
        "raw_resource": resource,
    }


def get_mapping_by_id(
    mapping_id: str,
    *,
    mapping_type: str = "rehabilitation_plan",
    raw: bool = False,
) -> dict:
    mapping_id = _strip_prefix(mapping_id, "Basic", "mapping_id")
    resource = get(f"Basic/{mapping_id}", raw=True)
    normalised = normalise_mapping(resource, mapping_type)
    return resource if raw else normalised


def test_mapping_profile_search(
    mapping_type: str = "rehabilitation_plan",
    *,
    require_results: bool = True,
    raw: bool = False,
) -> dict:
    """Tester det midlertidige profilopslag og fejler ved nul resultater."""
    config = _get_config(mapping_type)
    require_results = _required_bool(require_results, "require_results")
    endpoint = "Basic?" + urlencode(
        [
            ("_profile", config["mapping_profile"]),
            ("_count", "1000"),
        ],
        doseq=True,
    )
    bundle = get(endpoint, raw=True)
    resources = _bundle_resources(bundle, config["mapping_resource_type"])
    matching_profile_resources = [
        resource
        for resource in resources
        if config["mapping_profile"] in _profiles(resource)
    ]
    if require_results and not matching_profile_resources:
        raise RuntimeError(
            "Profilopslaget blev accepteret, men returnerede nul "
            "RehabilitationPlanMapping-resourcer. Indtil opslaget er "
            "verificeret med mindst ét kendt resultat, må det ikke bruges "
            "som dubletkontrol eller før oprettelse."
        )
    result = {
        "success": True,
        "mapping_type": mapping_type,
        "endpoint": endpoint,
        "bundle_total": bundle.get("total"),
        "resource_count": len(matching_profile_resources),
        "mappings": [
            normalise_mapping(resource, mapping_type)
            for resource in matching_profile_resources
        ],
    }
    if raw:
        result["raw_bundle"] = bundle
    return result


def _matches_mapping(
    resource: dict,
    *,
    mapping_type: str,
    borger_reference: str,
    plan_reference: str,
    target_reference: str,
    expected_active: bool | None,
) -> bool:
    config = _get_config(mapping_type)
    if resource.get("resourceType") != config["mapping_resource_type"]:
        return False
    if config["mapping_profile"] not in _profiles(resource):
        return False
    if _reference(resource.get("subject")) != borger_reference:
        return False
    if _extension_reference(resource, config["plan_extension_url"]) != plan_reference:
        return False
    if _extension_reference(resource, config["target_extension_url"]) != target_reference:
        return False
    if (
        expected_active is not None
        and _extension_boolean(resource, config["active_extension_url"])
        is not expected_active
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
    require_nonempty_profile_search: bool = True,
) -> list[dict]:
    """
    Søger via profil og filtrerer lokalt på præcise referencer.

    Midlertidig sikkerhedsregel: Hvis profilopslaget returnerer nul resources,
    fejler funktionen. Reglen kan ændres, når opslaget er verificeret.
    """
    config = _get_config(mapping_type)
    borger_id = _strip_prefix(borger_id, "Patient", "borger_id")
    plan_id = _strip_prefix(
        plan_id,
        config["plan_resource_type"],
        "plan_id",
    )
    target_id = _strip_prefix(
        target_id,
        config["target_resource_type"],
        "target_id",
    )
    active_only = _required_bool(active_only, "active_only")
    require_nonempty_profile_search = _required_bool(
        require_nonempty_profile_search,
        "require_nonempty_profile_search",
    )
    search_result = test_mapping_profile_search(
        mapping_type,
        require_results=require_nonempty_profile_search,
        raw=False,
    )
    expected = {
        "borger_reference": f"Patient/{borger_id}",
        "plan_reference": f"{config['plan_resource_type']}/{plan_id}",
        "target_reference": f"{config['target_resource_type']}/{target_id}",
    }
    return [
        mapping
        for mapping in search_result["mappings"]
        if _matches_mapping(
            mapping["raw_resource"],
            mapping_type=mapping_type,
            expected_active=True if active_only else None,
            **expected,
        )
    ]


def build_plan_mapping(
    mapping_type: str,
    borger_id: str,
    plan_id: str,
    target_id: str,
    *,
    is_active: bool = True,
) -> dict:
    config = _get_config(mapping_type)
    borger_id = _strip_prefix(borger_id, "Patient", "borger_id")
    plan_id = _strip_prefix(
        plan_id,
        config["plan_resource_type"],
        "plan_id",
    )
    target_id = _strip_prefix(
        target_id,
        config["target_resource_type"],
        "target_id",
    )
    is_active = _required_bool(is_active, "is_active")
    body = _load_template(config["skabelon"])
    _validate_fhir_resource(
        body,
        expected_resource_type=config["mapping_resource_type"],
        expected_profile=config["mapping_profile"],
        label="Mapping-skabelonen",
    )
    body.pop("id", None)
    meta = body.get("meta")
    if isinstance(meta, dict):
        for field_name in (
            "versionId",
            "lastUpdated",
            "security",
            "extension",
        ):
            meta.pop(field_name, None)
    body["subject"] = {"reference": f"Patient/{borger_id}"}
    _set_reference_extension(
        body,
        config["plan_extension_url"],
        f"{config['plan_resource_type']}/{plan_id}",
    )
    _set_reference_extension(
        body,
        config["target_extension_url"],
        f"{config['target_resource_type']}/{target_id}",
    )
    _set_boolean_extension(
        body,
        config["active_extension_url"],
        is_active,
    )
    return body


def build_mapping(
    borger_id: str,
    communication_id: str,
    forloeb_id: str,
    *,
    is_active: bool = True,
) -> dict:
    """Bagudkompatibelt navn fra det slettede mappingmodul."""
    return build_plan_mapping(
        "rehabilitation_plan",
        borger_id,
        communication_id,
        forloeb_id,
        is_active=is_active,
    )


def opret_plan_mapping(
    mapping_type: str,
    borger_id: str,
    plan_id: str,
    target_id: str,
    *,
    is_active: bool = True,
    dry_run: bool = True,
    existing_mapping_id: str | None = None,
    require_nonempty_profile_search: bool = True,
    raw: bool = False,
) -> dict:
    config = _get_config(mapping_type)
    borger_id = _strip_prefix(borger_id, "Patient", "borger_id")
    plan_id = _strip_prefix(
        plan_id,
        config["plan_resource_type"],
        "plan_id",
    )
    target_id = _strip_prefix(
        target_id,
        config["target_resource_type"],
        "target_id",
    )
    is_active = _required_bool(is_active, "is_active")
    dry_run = _required_bool(dry_run, "dry_run")
    require_nonempty_profile_search = _required_bool(
        require_nonempty_profile_search,
        "require_nonempty_profile_search",
    )
    existing_mapping_id = _optional_text(
        existing_mapping_id,
        "existing_mapping_id",
    )
    borger_reference = f"Patient/{borger_id}"
    plan_reference = f"{config['plan_resource_type']}/{plan_id}"
    target_reference = f"{config['target_resource_type']}/{target_id}"

    plan_resource = get(plan_reference, raw=True)
    _validate_fhir_resource(
        plan_resource,
        expected_resource_type=config["plan_resource_type"],
        expected_profile=config["plan_profile"],
        expected_subject=borger_reference,
        label="Planressourcen",
    )
    target_resource = get(target_reference, raw=True)
    _validate_fhir_resource(
        target_resource,
        expected_resource_type=config["target_resource_type"],
        expected_profile=config["target_profile"],
        expected_subject=borger_reference,
        label="Målressourcen",
    )

    if existing_mapping_id:
        known = get_mapping_by_id(
            existing_mapping_id,
            mapping_type=mapping_type,
            raw=True,
        )
        if _matches_mapping(
            known,
            mapping_type=mapping_type,
            borger_reference=borger_reference,
            plan_reference=plan_reference,
            target_reference=target_reference,
            expected_active=True,
        ):
            return {
                "success": True,
                "created": False,
                "verified": True,
                "dry_run": dry_run,
                "already_exists": True,
                "message": "Den aktive mapping findes allerede.",
                **normalise_mapping(known, mapping_type),
            }
        raise ValueError(
            "existing_mapping_id peger ikke på den forventede aktive mapping."
        )

    existing = find_existing_plan_mappings(
        mapping_type,
        borger_id,
        plan_id,
        target_id,
        active_only=True,
        require_nonempty_profile_search=(
            require_nonempty_profile_search
        ),
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
            "Mappingen blev muligvis oprettet, men POST-svaret indeholdt "
            "ikke et id. Kør ikke oprettelsen igen før GET-kontrol."
        )
    verified = get(f"Basic/{mapping_id}", raw=True)
    if not _matches_mapping(
        verified,
        mapping_type=mapping_type,
        borger_reference=borger_reference,
        plan_reference=plan_reference,
        target_reference=target_reference,
        expected_active=is_active,
    ):
        raise RuntimeError(
            "Den oprettede mapping bestod ikke kontrol af referencer og status."
        )
    result = {
        "success": True,
        "created": True,
        "verified": True,
        "dry_run": False,
        "already_exists": False,
        "message": "Mappingen blev oprettet og verificeret.",
        "post_status_code": post_response.get("status_code"),
        "location": location,
        **normalise_mapping(verified, mapping_type),
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
    require_nonempty_profile_search: bool = True,
    raw: bool = False,
) -> dict:
    return opret_plan_mapping(
        "rehabilitation_plan",
        borger_id,
        communication_id,
        care_plan_id,
        is_active=is_active,
        dry_run=dry_run,
        existing_mapping_id=existing_mapping_id,
        require_nonempty_profile_search=require_nonempty_profile_search,
        raw=raw,
    )


def create_mapping(
    borger_id: str,
    communication_id: str,
    forloeb_id: str,
    *,
    raw: bool = False,
) -> dict:
    """Bagudkompatibel oprettelsesfunktion med de nye sikkerhedskontroller."""
    return opret_rehabilitation_plan_mapping(
        borger_id,
        communication_id,
        forloeb_id,
        dry_run=False,
        raw=raw,
    )


def update_mapping_forloeb(
    mapping_id: str,
    forloeb_id: str,
    *,
    raw: bool = False,
) -> dict:
    mapping_id = _strip_prefix(mapping_id, "Basic", "mapping_id")
    forloeb_id = _strip_prefix(forloeb_id, "CarePlan", "forloeb_id")
    resource = get_mapping_by_id(mapping_id, raw=True)
    current = normalise_mapping(resource)
    care_plan = get(f"CarePlan/{forloeb_id}", raw=True)
    _validate_fhir_resource(
        care_plan,
        expected_resource_type="CarePlan",
        expected_profile=PROFILE_CARE_PLAN,
        expected_subject=current["borger_reference"],
        label="Det nye forløb",
    )
    if current["forloeb_id"] == forloeb_id:
        return resource if raw else {
            **current,
            "changed": False,
            "verified": True,
        }
    body = deepcopy(resource)
    _set_reference_extension(
        body,
        EXTENSION_RELATES_TO,
        f"CarePlan/{forloeb_id}",
    )
    put(f"Basic/{mapping_id}", body, raw=False)
    verified = get(f"Basic/{mapping_id}", raw=True)
    result = normalise_mapping(verified)
    if result["forloeb_id"] != forloeb_id:
        raise RuntimeError("Mappingen peger ikke på det forventede forløb.")
    if result["borger_reference"] != current["borger_reference"]:
        raise RuntimeError("Mappingens borgerreference blev uventet ændret.")
    return verified if raw else {
        **result,
        "changed": True,
        "verified": True,
    }


def set_mapping_active(
    mapping_id: str,
    is_active: bool,
    *,
    raw: bool = False,
) -> dict:
    mapping_id = _strip_prefix(mapping_id, "Basic", "mapping_id")
    is_active = _required_bool(is_active, "is_active")
    resource = get_mapping_by_id(mapping_id, raw=True)
    current = normalise_mapping(resource)
    if current["is_active"] is is_active:
        return resource if raw else {
            **current,
            "changed": False,
            "verified": True,
        }
    body = deepcopy(resource)
    _set_boolean_extension(
        body,
        EXTENSION_IS_ACTIVE,
        is_active,
    )
    put(f"Basic/{mapping_id}", body, raw=False)
    verified = get(f"Basic/{mapping_id}", raw=True)
    result = normalise_mapping(verified)
    if result["is_active"] is not is_active:
        raise RuntimeError("Mappingens aktive status blev ikke gemt korrekt.")
    return verified if raw else {
        **result,
        "changed": True,
        "verified": True,
    }

from __future__ import annotations

from urllib.parse import urlencode

from q_cura_api.api_client import get


# ------------------------------------------------------------
# CURA SIMPLE TASK
# ------------------------------------------------------------
#
# Det følgende er verificeret med faktiske svar fra Haderslevs CURA:
#
# - CuraSimpleTask er en FHIR Basic-resource.
# - CuraSimpleTask/for peger på borgeren:
#       Patient/<borger-id>
# - Basic.subject peger på den Communication, som opgaven hører til:
#       Communication/<communication-id>
# - Basic.id er opgavens tekniske id.
# - CuraSimpleTask/type kan fx være "incoming communication".
# - http://curafhir.dk/x/task/status indeholder opgavens status.
#
# Modulet er bevidst afgrænset til CuraSimpleTask. Andre opgavetyper
# skal først tilføjes, når deres relationer og søgefelter er verificeret.
CURA_SIMPLE_TASK_PROFILE = "http://curafhir.dk/p/CuraSimpleTask"

EXTENSION_TYPE = "http://curafhir.dk/x/CuraSimpleTask/type"
EXTENSION_STATUS = "http://curafhir.dk/x/task/status"
EXTENSION_REQUESTER = "http://curafhir.dk/x/CuraSimpleTask/requester"
EXTENSION_FOR = "http://curafhir.dk/x/CuraSimpleTask/for"
EXTENSION_MANAGING_ORGANIZATION = (
    "http://curafhir.dk/x/CuraSimpleTask/managingOrganization"
)
META_CREATED_TIMESTAMP = "http://curafhir.dk/x/meta/systemCreatedTimestamp"
TIMESTAMP_INSTANT = "http://curafhir.dk/x/CuraTimestamp/instant"


# ------------------------------------------------------------
# VALIDERING
# ------------------------------------------------------------
def _required_text(value, field_name: str) -> str:
    """Validerer et obligatorisk tekstinput."""
    if value is None:
        raise ValueError(f"{field_name} skal angives.")
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst.")

    validated = value.strip()
    if not validated:
        raise ValueError(f"{field_name} må ikke være tom.")

    return validated


def _validate_count(count: int) -> int:
    """Validerer det maksimale antal resurser i CURA-kaldet."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count skal være et helt tal.")
    if not 1 <= count <= 1000:
        raise ValueError("count skal være mellem 1 og 1000.")
    return count


# ------------------------------------------------------------
# FHIR-HJÆLPERE
# ------------------------------------------------------------
def _get_entries(bundle: dict) -> list:
    """Returnerer Bundle.entry som en sikker liste."""
    if not isinstance(bundle, dict):
        return []

    entries = bundle.get("entry", [])
    return entries if isinstance(entries, list) else []


def _get_profiles(resource: dict) -> list:
    """Returnerer resource.meta.profile som en sikker liste."""
    meta = resource.get("meta", {})
    if not isinstance(meta, dict):
        return []

    profiles = meta.get("profile", [])
    return profiles if isinstance(profiles, list) else []


def _get_reference(value) -> str:
    """Henter hele FHIR-referencen fra tekst, dictionary eller liste."""
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        return str(value.get("reference") or "").strip()

    if isinstance(value, list):
        for item in value:
            reference = _get_reference(item)
            if reference:
                return reference

    return ""


def _get_reference_id(value) -> str:
    """Henter id-delen fra en FHIR-reference."""
    reference = _get_reference(value)
    return reference.rstrip("/").split("/")[-1] if reference else ""


def _find_extension(resource: dict, extension_url: str) -> dict:
    """Finder den første extension med den præcise URL."""
    extensions = resource.get("extension", [])
    if not isinstance(extensions, list):
        return {}

    for extension in extensions:
        if isinstance(extension, dict) and extension.get("url") == extension_url:
            return extension

    return {}


def _get_extension_value(resource: dict, extension_url: str):
    """
    Henter værdien fra en extension.

    Understøtter fx valueCode, valueString, valueBoolean,
    valueDateTime og valueReference.
    """
    extension = _find_extension(resource, extension_url)
    if not extension:
        return ""

    for key, value in extension.items():
        if key.startswith("value"):
            return value

    nested = extension.get("extension", [])
    return nested if isinstance(nested, list) else ""


def _get_extension_reference(resource: dict, extension_url: str) -> str:
    """Henter reference fra en extensions valueReference."""
    value = _get_extension_value(resource, extension_url)
    return _get_reference(value)


def _get_created_timestamp(resource: dict) -> str:
    """
    Henter CURAs systemoprettelsestidspunkt fra meta.extension.

    Feltet er observeret på den verificerede CuraSimpleTask.
    Hvis feltet mangler, returneres en tom tekst.
    """
    meta = resource.get("meta", {})
    if not isinstance(meta, dict):
        return ""

    created_extension = _find_extension(meta, META_CREATED_TIMESTAMP)
    nested_extensions = created_extension.get("extension", [])
    if not isinstance(nested_extensions, list):
        return ""

    for extension in nested_extensions:
        if not isinstance(extension, dict):
            continue
        if extension.get("url") == TIMESTAMP_INSTANT:
            return str(extension.get("valueInstant") or "")

    return ""


def _is_cura_simple_task(resource: dict) -> bool:
    """Kontrollerer resourceType og CuraSimpleTask-profilen."""
    return (
        isinstance(resource, dict)
        and resource.get("resourceType") == "Basic"
        and CURA_SIMPLE_TASK_PROFILE in _get_profiles(resource)
    )


# ------------------------------------------------------------
# NORMALISERING
# ------------------------------------------------------------
def _normalise_task(resource: dict) -> dict:
    """
    Returnerer fælles og verificerede felter fra en CuraSimpleTask.

    raw_resource bevares, så processer kan tilgå alle øvrige felter.
    Nye opgavetyper skal have deres egen dokumenterede normalisering.
    """
    if not _is_cura_simple_task(resource):
        raise ValueError("Ressourcen er ikke en CuraSimpleTask.")

    meta = resource.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    communication_reference = _get_reference(resource.get("subject"))
    citizen_reference = _get_extension_reference(resource, EXTENSION_FOR)
    requester_reference = _get_extension_reference(resource, EXTENSION_REQUESTER)
    managing_organization_reference = _get_extension_reference(
        resource,
        EXTENSION_MANAGING_ORGANIZATION,
    )

    return {
        "task_id": str(resource.get("id") or ""),
        "resource_type": str(resource.get("resourceType") or ""),
        "profile": CURA_SIMPLE_TASK_PROFILE,
        "profiles": _get_profiles(resource),
        "version_id": str(meta.get("versionId") or ""),
        "last_updated": str(meta.get("lastUpdated") or ""),
        "created": _get_created_timestamp(resource),
        "type": _get_extension_value(resource, EXTENSION_TYPE),
        "status": _get_extension_value(resource, EXTENSION_STATUS),
        "communication_reference": communication_reference,
        "communication_id": _get_reference_id(communication_reference),
        "borger_reference": citizen_reference,
        "borger_id": _get_reference_id(citizen_reference),
        "requester_reference": requester_reference,
        "requester_id": _get_reference_id(requester_reference),
        "managing_organization_reference": managing_organization_reference,
        "managing_organization_id": _get_reference_id(
            managing_organization_reference
        ),
        "raw_resource": resource,
    }


# ------------------------------------------------------------
# 1. HENT OPGAVER FOR BORGER
# ------------------------------------------------------------
def get_tasks_for_citizen(
    borger_id: str,
    *,
    count: int = 1000,
    raw: bool = False,
) -> dict:
    """
    Henter CuraSimpleTask-opgaver for én borger.

    Input:
        borger_id:
            Borgerens tekniske CURA-id uden "Patient/".

        count:
            Maksimalt antal resurser i CURA-kaldet. 1 til 1000.

        raw:
            True returnerer det rå FHIR Bundle.
            False returnerer et normaliseret resultat.

    Verificeret CURA-kald:
        Basic
        ?_profile=http://curafhir.dk/p/CuraSimpleTask
        &for=Patient/<borger-id>

    Der bruges ikke _lastUpdated, fordi CURAs søgeunderstøttelse kan
    variere mellem de enkelte Basic-profiler.
    """
    validated_borger_id = _required_text(borger_id, "borger_id")
    validated_count = _validate_count(count)
    citizen_reference = f"Patient/{validated_borger_id}"

    endpoint = "Basic?" + urlencode(
        {
            "_profile": CURA_SIMPLE_TASK_PROFILE,
            "for": citizen_reference,
            "_count": validated_count,
        }
    )

    bundle = get(endpoint, raw=True)
    if raw:
        return bundle

    tasks = []

    for entry in _get_entries(bundle):
        if not isinstance(entry, dict):
            continue

        resource = entry.get("resource", {})
        if not _is_cura_simple_task(resource):
            continue

        normalised_task = _normalise_task(resource)

        # Ekstra kontrol: behold kun tasken, hvis den returnerede
        # for-reference faktisk peger på den valgte borger.
        if normalised_task["borger_reference"] != citizen_reference:
            continue

        tasks.append(normalised_task)

    tasks.sort(
        key=lambda task: str(task.get("created") or task.get("last_updated") or ""),
        reverse=True,
    )

    return {
        "found": bool(tasks),
        "count": len(tasks),
        "borger_id": validated_borger_id,
        "borger_reference": citizen_reference,
        "tasks": tasks,
    }


# ------------------------------------------------------------
# 2. HENT ÉN OPGAVE VIA ID
# ------------------------------------------------------------
def get_task_by_id(
    task_id: str,
    *,
    raw: bool = False,
) -> dict:
    """
    Henter én CuraSimpleTask via dens tekniske Basic-id.

    Input:
        task_id:
            Taskens Basic.id.

        raw:
            True returnerer Basic-ressourcen uændret.
            False returnerer det normaliserede resultat.
    """
    validated_task_id = _required_text(task_id, "task_id")
    resource = get(f"Basic/{validated_task_id}", raw=True)

    if not isinstance(resource, dict):
        raise RuntimeError("CURA returnerede ikke en dictionary.")
    if not _is_cura_simple_task(resource):
        raise ValueError("Basic-ressourcen er ikke en CuraSimpleTask.")

    return resource if raw else _normalise_task(resource)


# ------------------------------------------------------------
# 3. HENT OPGAVE FOR COMMUNICATION
# ------------------------------------------------------------
def get_tasks_for_communication(
    communication_id: str,
    borger_id: str,
    *,
    count: int = 1000,
    raw: bool = False,
) -> dict:
    """
    Finder CuraSimpleTask-opgaver, som hører til én Communication.

    Input:
        communication_id:
            Communication.id for beskeden.

        borger_id:
            Borgerens tekniske CURA-id. Inputtet er nødvendigt, fordi
            CURA-opslaget efter CuraSimpleTask er verificeret via
            CuraSimpleTask/for = Patient/<borger-id>.

        count:
            Maksimalt antal borgeropgaver, der hentes før lokal filtrering.

        raw:
            False returnerer normaliserede task-resultater.
            True returnerer de matchende rå Basic-resurser.

    Flow:
        1. Hent borgerens CuraSimpleTask-opgaver.
        2. Sammenlign Basic.subject.reference med
           Communication/<communication-id>.
        3. Returnér alle match. Der antages ikke, at der altid kun er ét.
    """
    validated_communication_id = _required_text(
        communication_id,
        "communication_id",
    )
    validated_borger_id = _required_text(borger_id, "borger_id")
    expected_reference = f"Communication/{validated_communication_id}"

    citizen_result = get_tasks_for_citizen(
        validated_borger_id,
        count=count,
        raw=False,
    )

    matching_tasks = [
        task
        for task in citizen_result["tasks"]
        if task.get("communication_reference") == expected_reference
    ]

    if raw:
        returned_tasks = [task["raw_resource"] for task in matching_tasks]
    else:
        returned_tasks = matching_tasks

    return {
        "found": bool(returned_tasks),
        "count": len(returned_tasks),
        "communication_id": validated_communication_id,
        "communication_reference": expected_reference,
        "borger_id": validated_borger_id,
        "borger_reference": f"Patient/{validated_borger_id}",
        "tasks": returned_tasks,
    }

from __future__ import annotations

from copy import deepcopy
from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA"

BORGER_ID = (
    "39dde427-b1fc-42b3-9e85-fccf727ee3bf"
)

COMMUNICATION_ID = (
    "ffacfccc-a589-44c5-9119-ff5093a88013"
)

YDELSE_ID = (
    "aad64bd6-d24c-4650-b28a-f52d763d5b99"
)

FORLOEB_ID = (
    "3e0bdb88-cc81-45dc-b34f-ab8bd9c46c8f"
)

COUNT = 1000

TASK_PROFILES = {
    "CuraRequestTask": (
        "http://curafhir.dk/p/"
        "CuraRequestTask"
    ),
    "CuraSimpleTask": (
        "http://curafhir.dk/p/"
        "CuraSimpleTask"
    ),
    "CuraCareHomeTask": (
        "http://curafhir.dk/p/"
        "CuraCareHomeTask"
    ),
    "CuraOrganizationalTask": (
        "http://curafhir.dk/p/"
        "CuraOrganizationalTask"
    ),
}

# Profilerne bruger ikke nødvendigvis samme søgeparameter
# til borgeren.
PROFILE_SEARCH_FIELDS = {
    "CuraRequestTask": (
        "for",
    ),
    "CuraSimpleTask": (
        "subject",
        "for",
    ),
    "CuraCareHomeTask": (
        "subject",
    ),
    "CuraOrganizationalTask": (
        "subject",
        "for",
    ),
}

SENSITIVE_CONTENT_KEYS = {
    "contentString",
    "content_strings",
}


# ------------------------------------------------------------
# BUNDLE-HJÆLPERE
# ------------------------------------------------------------

def _get_entries(
    bundle: dict,
) -> list:
    """
    Henter Bundle.entry som en sikker liste.

    Output:
        Liste med Bundle.entry-elementer.
    """
    if not isinstance(bundle, dict):
        return []

    entries = bundle.get(
        "entry",
        [],
    )

    if not isinstance(entries, list):
        return []

    return entries


def _get_basic_resources(
    bundle: dict,
) -> list:
    """
    Henter alle Basic-resurser fra et FHIR Bundle.

    Output:
        Liste med Basic-resurser.
    """
    resources = []

    for entry in _get_entries(bundle):
        if not isinstance(entry, dict):
            continue

        resource = entry.get(
            "resource",
            {},
        )

        if not isinstance(resource, dict):
            continue

        if resource.get("resourceType") != "Basic":
            continue

        resources.append(resource)

    return resources


def _get_profiles(
    resource: dict,
) -> list:
    """
    Henter resource.meta.profile som en sikker liste.
    """
    meta = resource.get(
        "meta",
        {},
    )

    if not isinstance(meta, dict):
        return []

    profiles = meta.get(
        "profile",
        [],
    )

    if not isinstance(profiles, list):
        return []

    return profiles


# ------------------------------------------------------------
# SIKKER UDSKRIFT
# ------------------------------------------------------------

def _remove_message_content(
    value,
):
    """
    Opretter en kopi uden beskedens fritekstindhold.

    Følgende felter erstattes med en markering:
        contentString
        content_strings

    Andre metadata og referencer bevares.
    """
    if isinstance(value, dict):
        cleaned = {}

        for key, child_value in value.items():
            if key in SENSITIVE_CONTENT_KEYS:
                cleaned[key] = (
                    "<udeladt fra testudskrift>"
                )
                continue

            cleaned[key] = (
                _remove_message_content(
                    child_value
                )
            )

        return cleaned

    if isinstance(value, list):
        return [
            _remove_message_content(item)
            for item in value
        ]

    return value


# ------------------------------------------------------------
# REKURSIV DATAUNDERSØGELSE
# ------------------------------------------------------------

def _normalise_string(
    value: str,
) -> str:
    """
    Normaliserer tekst til sammenligning.

    Der ændres ikke på den oprindelige resource.
    """
    return str(
        value
        or ""
    ).strip()


def _build_search_values() -> dict:
    """
    Bygger alle værdier, som testen skal lede efter.

    Der søges både efter:
        Ressourcetype/id
        Det bare tekniske id

    Det gør testen robust, hvis Cura gemmer relationen
    i et identifier-felt eller en extension.
    """
    return {
        "communication_reference": (
            f"Communication/{COMMUNICATION_ID}"
        ),
        "communication_id": COMMUNICATION_ID,
        "ydelse_reference": (
            f"ProcedureRequest/{YDELSE_ID}"
        ),
        "ydelse_id": YDELSE_ID,
        "forloeb_reference": (
            f"CarePlan/{FORLOEB_ID}"
        ),
        "forloeb_id": FORLOEB_ID,
        "borger_reference": (
            f"Patient/{BORGER_ID}"
        ),
        "borger_id": BORGER_ID,
    }


def _find_values_recursive(
    value,
    search_values: dict,
    path: str = "resource",
) -> list:
    """
    Gennemgår hele ressourcen rekursivt.

    Funktionen finder værdier i blandt andet:
        reference
        valueReference.reference
        identifier.value
        valueString
        valueUri
        extension
        subject
        basedOn
        context
        for

    Beskedindholdet springes over.

    Output:
        Liste med:
            match_name
            expected_value
            actual_value
            path
    """
    matches = []

    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in SENSITIVE_CONTENT_KEYS:
                continue

            child_path = f"{path}.{key}"

            matches.extend(
                _find_values_recursive(
                    child_value,
                    search_values,
                    child_path,
                )
            )

        return matches

    if isinstance(value, list):
        for index, child_value in enumerate(value):
            child_path = (
                f"{path}[{index}]"
            )

            matches.extend(
                _find_values_recursive(
                    child_value,
                    search_values,
                    child_path,
                )
            )

        return matches

    if not isinstance(value, str):
        return matches

    actual_value = _normalise_string(
        value
    )

    if not actual_value:
        return matches

    for (
        match_name,
        expected_value,
    ) in search_values.items():
        if actual_value != expected_value:
            continue

        matches.append(
            {
                "match_name": match_name,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "path": path,
            }
        )

    return matches


def _find_reference_values(
    value,
    path: str = "resource",
) -> list:
    """
    Finder alle tekstværdier, der ligner FHIR-referencer.

    Det giver et overblik over andre ressourcer, som Tasken
    eller beskeden peger på.
    """
    references = []

    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in SENSITIVE_CONTENT_KEYS:
                continue

            references.extend(
                _find_reference_values(
                    child_value,
                    f"{path}.{key}",
                )
            )

        return references

    if isinstance(value, list):
        for index, child_value in enumerate(value):
            references.extend(
                _find_reference_values(
                    child_value,
                    f"{path}[{index}]",
                )
            )

        return references

    if not isinstance(value, str):
        return references

    text = value.strip()

    prefixes = (
        "Communication/",
        "ProcedureRequest/",
        "CarePlan/",
        "Patient/",
        "Basic/",
        "Task/",
        "Organization/",
        "Practitioner/",
    )

    if text.startswith(prefixes):
        references.append(
            {
                "path": path,
                "reference": text,
            }
        )

    return references


def _remove_duplicate_dicts(
    values: list,
) -> list:
    """
    Fjerner dubletter fra en liste med dictionaries.
    """
    result = []
    seen = set()

    for value in values:
        if not isinstance(value, dict):
            continue

        key = tuple(
            sorted(
                (
                    str(item_key),
                    repr(item_value),
                )
                for (
                    item_key,
                    item_value,
                ) in value.items()
            )
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


# ------------------------------------------------------------
# API-OPSLAG
# ------------------------------------------------------------

def _get_communication() -> dict:
    """
    Henter den konkrete Communication direkte via id.

    Der udføres kun GET.
    """
    resource = get(
        f"Communication/{COMMUNICATION_ID}",
        raw=True,
    )

    if not isinstance(resource, dict):
        raise RuntimeError(
            "CURA returnerede ikke en dictionary "
            "for Communication."
        )

    if (
        resource.get("resourceType")
        != "Communication"
    ):
        raise ValueError(
            "Den hentede resource er ikke "
            "en Communication."
        )

    return resource


def _build_task_endpoint(
    profile: str,
    citizen_field: str,
    citizen_value: str,
) -> str:
    """
    Bygger et læsende Basic-opslag for én Task-profil.
    """
    return (
        "Basic?"
        + urlencode(
            [
                (
                    "_profile",
                    profile,
                ),
                (
                    citizen_field,
                    citizen_value,
                ),
                (
                    "_count",
                    str(COUNT),
                ),
            ],
            doseq=True,
        )
    )


def _run_task_search(
    profile_name: str,
    profile: str,
    citizen_field: str,
    citizen_value: str,
) -> dict:
    """
    Kører ét Task-opslag.

    Fejl gemmes i resultatet, så de andre søgevarianter
    stadig bliver kørt.
    """
    endpoint = _build_task_endpoint(
        profile=profile,
        citizen_field=citizen_field,
        citizen_value=citizen_value,
    )

    print()
    print("=" * 100)
    print(
        f"TASKSØGNING: {profile_name}"
    )
    print("=" * 100)
    print(
        f"Borgerfelt: {citizen_field}"
    )
    print(
        f"Borgerværdi: {citizen_value}"
    )
    print(
        f"Endpoint: {endpoint}"
    )

    try:
        bundle = get(
            endpoint,
            raw=True,
        )

    except Exception as error:
        print(
            "Opslaget fejlede, men testen "
            "fortsætter."
        )
        print(
            f"Fejltype: "
            f"{type(error).__name__}"
        )
        print(str(error))

        return {
            "profile_name": profile_name,
            "profile": profile,
            "citizen_field": citizen_field,
            "citizen_value": citizen_value,
            "endpoint": endpoint,
            "error": str(error),
            "resources": [],
        }

    resources = _get_basic_resources(
        bundle
    )

    print(
        "Antal Bundle.entries: "
        f"{len(_get_entries(bundle))}"
    )
    print(
        "Antal Basic-resurser: "
        f"{len(resources)}"
    )

    return {
        "profile_name": profile_name,
        "profile": profile,
        "citizen_field": citizen_field,
        "citizen_value": citizen_value,
        "endpoint": endpoint,
        "error": "",
        "resources": resources,
    }


def _get_all_candidate_tasks() -> list:
    """
    Henter Task-kandidater med de kendte profiler.

    Der afprøves både:
        Patient/<id>
        <id>

    Samme resource kan blive fundet flere gange.
    Dubletter fjernes med Basic.id.
    """
    citizen_values = (
        f"Patient/{BORGER_ID}",
        BORGER_ID,
    )

    search_results = []

    for (
        profile_name,
        profile,
    ) in TASK_PROFILES.items():
        search_fields = (
            PROFILE_SEARCH_FIELDS.get(
                profile_name,
                (),
            )
        )

        for citizen_field in search_fields:
            for citizen_value in citizen_values:
                search_results.append(
                    _run_task_search(
                        profile_name=profile_name,
                        profile=profile,
                        citizen_field=citizen_field,
                        citizen_value=citizen_value,
                    )
                )

    resources_by_id = {}

    for search_result in search_results:
        for resource in search_result.get(
            "resources",
            [],
        ):
            resource_id = str(
                resource.get("id")
                or ""
            )

            key = (
                resource_id
                or repr(resource)
            )

            resources_by_id[key] = resource

    return list(
        resources_by_id.values()
    )


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main():
    """
    Undersøger koblingen:

        Communication
        Basic/Task
        ProcedureRequest
        CarePlan

    Testen udfører kun GET.
    Der udføres ingen POST eller PUT.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    search_values = (
        _build_search_values()
    )

    print()
    print("=" * 100)
    print(
        "DIAGNOSTIK AF BESKED, OPGAVE, "
        "YDELSE OG FORLØB"
    )
    print("=" * 100)
    print(
        f"Miljø:          "
        f"{CURA_CREDENTIAL}"
    )
    print(
        f"Borger-ID:      "
        f"{BORGER_ID}"
    )
    print(
        f"Communication:  "
        f"{COMMUNICATION_ID}"
    )
    print(
        f"Ydelse:         "
        f"{YDELSE_ID}"
    )
    print(
        f"Forløb:         "
        f"{FORLOEB_ID}"
    )

    # --------------------------------------------------------
    # 1. HENT OG UNDERSØG DEN KONKRETE BESKED
    # --------------------------------------------------------

    communication = (
        _get_communication()
    )

    communication_matches = (
        _remove_duplicate_dicts(
            _find_values_recursive(
                communication,
                search_values,
            )
        )
    )

    communication_references = (
        _remove_duplicate_dicts(
            _find_reference_values(
                communication
            )
        )
    )

    print()
    print("=" * 100)
    print("DEN KONKRETE COMMUNICATION")
    print("=" * 100)
    print(
        "ResourceType: "
        f"{communication.get('resourceType', '')}"
    )
    print(
        "ID:           "
        f"{communication.get('id', '')}"
    )
    print(
        "Profiler:     "
        f"{_get_profiles(communication)}"
    )
    print(
        "Received:     "
        f"{communication.get('received', '')}"
    )
    print(
        "Sent:         "
        f"{communication.get('sent', '')}"
    )

    print()
    print("Match i Communication:")
    pprint(
        communication_matches,
        width=180,
        sort_dicts=False,
    )

    print()
    print("Alle FHIR-referencer i Communication:")
    pprint(
        communication_references,
        width=180,
        sort_dicts=False,
    )

    print()
    print(
        "Communication uden contentString:"
    )
    pprint(
        _remove_message_content(
            deepcopy(communication)
        ),
        width=200,
        sort_dicts=False,
    )

    # --------------------------------------------------------
    # 2. HENT OG UNDERSØG TASKS
    # --------------------------------------------------------

    tasks = _get_all_candidate_tasks()

    print()
    print("=" * 100)
    print("SAMLET TASK-RESULTAT")
    print("=" * 100)
    print(
        f"Antal unikke Basic-resurser: "
        f"{len(tasks)}"
    )

    tasks_with_communication = []
    tasks_with_ydelse = []
    tasks_with_forloeb = []
    tasks_with_multiple_links = []

    for task in tasks:
        matches = _remove_duplicate_dicts(
            _find_values_recursive(
                task,
                search_values,
            )
        )

        match_names = {
            match.get("match_name")
            for match in matches
        }

        has_communication = bool(
            {
                "communication_reference",
                "communication_id",
            }
            & match_names
        )

        has_ydelse = bool(
            {
                "ydelse_reference",
                "ydelse_id",
            }
            & match_names
        )

        has_forloeb = bool(
            {
                "forloeb_reference",
                "forloeb_id",
            }
            & match_names
        )

        if has_communication:
            tasks_with_communication.append(
                task
            )

        if has_ydelse:
            tasks_with_ydelse.append(
                task
            )

        if has_forloeb:
            tasks_with_forloeb.append(
                task
            )

        if (
            has_communication
            and (
                has_ydelse
                or has_forloeb
            )
        ):
            tasks_with_multiple_links.append(
                task
            )

        # Vis kun relevante tasks.
        if not (
            has_communication
            or has_ydelse
            or has_forloeb
        ):
            continue

        references = (
            _remove_duplicate_dicts(
                _find_reference_values(
                    task
                )
            )
        )

        print()
        print("-" * 100)
        print(
            "RELEVANT BASIC/TASK: "
            f"{task.get('id', '')}"
        )
        print("-" * 100)
        print(
            "Profiler:"
        )
        pprint(
            _get_profiles(task),
            width=180,
            sort_dicts=False,
        )

        print()
        print("Præcise match:")
        pprint(
            matches,
            width=180,
            sort_dicts=False,
        )

        print()
        print("Alle FHIR-referencer:")
        pprint(
            references,
            width=180,
            sort_dicts=False,
        )

        print()
        print("Rå Task-resource:")
        pprint(
            _remove_message_content(
                deepcopy(task)
            ),
            width=200,
            sort_dicts=False,
        )

    # --------------------------------------------------------
    # 3. KONKLUSION
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("KONKLUSION")
    print("=" * 100)
    print(
        "Tasks med Communication-match: "
        f"{len(tasks_with_communication)}"
    )
    print(
        "Tasks med ydelsesmatch: "
        f"{len(tasks_with_ydelse)}"
    )
    print(
        "Tasks med forløbsmatch: "
        f"{len(tasks_with_forloeb)}"
    )
    print(
        "Tasks med både Communication og "
        "ydelse/forløb: "
        f"{len(tasks_with_multiple_links)}"
    )

    if tasks_with_multiple_links:
        print()
        print(
            "Der blev fundet mindst én Task, "
            "som fungerer som bindeled."
        )
        print(
            "Se feltstierne under "
            "'Præcise match' ovenfor."
        )

    elif tasks_with_communication:
        print()
        print(
            "Der blev fundet Task-kobling til "
            "Communication, men ikke til de to "
            "testede ydelses-/forløbs-id'er."
        )
        print(
            "Taskens øvrige referencer ovenfor "
            "skal sammenholdes med Cura-dataene."
        )

    else:
        print()
        print(
            "Der blev ikke fundet en Task med "
            "den konkrete Communication-reference."
        )
        print(
            "Så skal næste undersøgelse rette sig "
            "mod andre Basic-profiler eller en "
            "separat relationsresource."
        )

    print()
    print(
        "Testen var kun læsende. "
        "Der blev ikke udført POST eller PUT."
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

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

CONTENT_FIELDS = {
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
    Returnerer Bundle.entry som en sikker liste.
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


def _get_resources(
    bundle: dict,
) -> list:
    """
    Henter alle gyldige resources fra Bundle.entry.

    Output:
        En liste med FHIR-resurser.
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
# REKURSIV SØGNING
# ------------------------------------------------------------

def _get_search_values() -> dict:
    """
    Returnerer de tekniske værdier, testen leder efter.

    Der søges både efter fulde FHIR-referencer og bare id'er.
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


def _find_matches(
    value,
    search_values: dict,
    path: str = "resource",
) -> list:
    """
    Gennemgår dictionaries og lister rekursivt.

    Beskedens contentString undersøges ikke.

    Output:
        [
            {
                "name": "communication_reference",
                "value": "Communication/<id>",
                "path": "resource.subject.reference",
            }
        ]
    """
    matches = []

    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in CONTENT_FIELDS:
                continue

            child_path = (
                f"{path}.{key}"
            )

            matches.extend(
                _find_matches(
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
                _find_matches(
                    child_value,
                    search_values,
                    child_path,
                )
            )

        return matches

    if not isinstance(value, str):
        return matches

    actual_value = value.strip()

    for name, expected_value in search_values.items():
        if actual_value != expected_value:
            continue

        matches.append(
            {
                "name": name,
                "value": actual_value,
                "path": path,
            }
        )

    return matches


def _find_fhir_references(
    value,
    path: str = "resource",
) -> list:
    """
    Finder alle tekstværdier, der ligner FHIR-referencer.
    """
    references = []

    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in CONTENT_FIELDS:
                continue

            references.extend(
                _find_fhir_references(
                    child_value,
                    f"{path}.{key}",
                )
            )

        return references

    if isinstance(value, list):
        for index, child_value in enumerate(value):
            references.extend(
                _find_fhir_references(
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
        "Device/",
    )

    if text.startswith(prefixes):
        references.append(
            {
                "path": path,
                "reference": text,
            }
        )

    return references


def _remove_duplicates(
    values: list,
) -> list:
    """
    Fjerner dubletter fra en liste med dictionaries.
    """
    result = []
    seen = set()

    for value in values:
        key = repr(value)

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


# ------------------------------------------------------------
# UDSKRIFT
# ------------------------------------------------------------

def _print_resource_result(
    title: str,
    resource: dict,
    search_values: dict,
):
    """
    Udskriver metadata, match og referencer for én resource.

    contentString udskrives ikke.
    """
    matches = _remove_duplicates(
        _find_matches(
            resource,
            search_values,
        )
    )

    references = _remove_duplicates(
        _find_fhir_references(
            resource
        )
    )

    print()
    print("-" * 100)
    print(title)
    print("-" * 100)
    print(
        "ResourceType: "
        f"{resource.get('resourceType', '')}"
    )
    print(
        "ID:           "
        f"{resource.get('id', '')}"
    )
    print(
        "Profiler:     "
        f"{_get_profiles(resource)}"
    )

    print()
    print("Præcise match:")
    pprint(
        matches,
        width=180,
        sort_dicts=False,
    )

    print()
    print("FHIR-referencer:")
    pprint(
        references,
        width=180,
        sort_dicts=False,
    )


# ------------------------------------------------------------
# API-KALD
# ------------------------------------------------------------

def _get_resource(
    endpoint: str,
    expected_resource_type: str,
) -> dict:
    """
    Henter én FHIR-resource direkte via id.
    """
    resource = get(
        endpoint,
        raw=True,
    )

    if not isinstance(resource, dict):
        raise RuntimeError(
            f"CURA returnerede ikke en dictionary "
            f"for {endpoint}."
        )

    resource_type = resource.get(
        "resourceType"
    )

    if resource_type != expected_resource_type:
        raise ValueError(
            f"Forventede {expected_resource_type}, "
            f"men modtog {resource_type!r}."
        )

    return resource


def _run_basic_search(
    search_name: str,
    parameter_name: str,
    parameter_value: str,
) -> dict:
    """
    Søger bredt i Basic uden profilfilter.

    Der udføres kun GET.
    """
    endpoint = (
        "Basic?"
        + urlencode(
            [
                (
                    parameter_name,
                    parameter_value,
                ),
                (
                    "_count",
                    str(COUNT),
                ),
            ],
            doseq=True,
        )
    )

    print()
    print("=" * 100)
    print(search_name)
    print("=" * 100)
    print(f"Endpoint: {endpoint}")

    try:
        bundle = get(
            endpoint,
            raw=True,
        )

    except Exception as error:
        print(
            f"Fejltype: "
            f"{type(error).__name__}"
        )
        print(str(error))

        return {
            "endpoint": endpoint,
            "error": str(error),
            "resources": [],
        }

    resources = _get_resources(
        bundle
    )

    print(
        "Antal Bundle.entries: "
        f"{len(_get_entries(bundle))}"
    )
    print(
        "Antal resources:      "
        f"{len(resources)}"
    )

    return {
        "endpoint": endpoint,
        "error": "",
        "resources": resources,
    }


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main():
    """
    Undersøger:

        1. Den konkrete ProcedureRequest.
        2. Den konkrete CarePlan.
        3. Alle Basic-resurser med beskeden som subject.
        4. Alle Basic-resurser med beskeden som for.
        5. Alle Basic-resurser for borgeren uden profilfilter.

    Testen udfører kun GET.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    search_values = (
        _get_search_values()
    )

    print()
    print("=" * 100)
    print(
        "BRED SØGNING EFTER BESKEDRELATION"
    )
    print("=" * 100)
    print(
        f"Communication: {COMMUNICATION_ID}"
    )
    print(
        f"Ydelse:        {YDELSE_ID}"
    )
    print(
        f"Forløb:        {FORLOEB_ID}"
    )
    print(
        f"Borger:        {BORGER_ID}"
    )

    # --------------------------------------------------------
    # 1. HENT YDELSEN DIREKTE
    # --------------------------------------------------------

    ydelse = _get_resource(
        f"ProcedureRequest/{YDELSE_ID}",
        "ProcedureRequest",
    )

    _print_resource_result(
        title="DIREKTE PROCEDUREREQUEST",
        resource=ydelse,
        search_values=search_values,
    )

    # --------------------------------------------------------
    # 2. HENT FORLØBET DIREKTE
    # --------------------------------------------------------

    forloeb = _get_resource(
        f"CarePlan/{FORLOEB_ID}",
        "CarePlan",
    )

    _print_resource_result(
        title="DIREKTE CAREPLAN",
        resource=forloeb,
        search_values=search_values,
    )

    # --------------------------------------------------------
    # 3. BREDE BASIC-SØGNINGER
    # --------------------------------------------------------

    searches = [
        _run_basic_search(
            search_name=(
                "ALLE BASIC MED BESKED SOM SUBJECT"
            ),
            parameter_name="subject",
            parameter_value=(
                f"Communication/{COMMUNICATION_ID}"
            ),
        ),
        _run_basic_search(
            search_name=(
                "ALLE BASIC MED BESKED SOM FOR"
            ),
            parameter_name="for",
            parameter_value=(
                f"Communication/{COMMUNICATION_ID}"
            ),
        ),
        _run_basic_search(
            search_name=(
                "ALLE BASIC MED BORGER SOM SUBJECT"
            ),
            parameter_name="subject",
            parameter_value=(
                f"Patient/{BORGER_ID}"
            ),
        ),
        _run_basic_search(
            search_name=(
                "ALLE BASIC MED BORGER SOM FOR"
            ),
            parameter_name="for",
            parameter_value=(
                f"Patient/{BORGER_ID}"
            ),
        ),
    ]

    resources_by_key = {}

    for search_result in searches:
        for resource in search_result.get(
            "resources",
            [],
        ):
            resource_type = str(
                resource.get("resourceType")
                or ""
            )

            resource_id = str(
                resource.get("id")
                or ""
            )

            key = (
                resource_type,
                resource_id,
            )

            resources_by_key[key] = resource

    resources = list(
        resources_by_key.values()
    )

    print()
    print("=" * 100)
    print("RELEVANTE BASIC-RESSOURCER")
    print("=" * 100)
    print(
        f"Antal unikke resources: "
        f"{len(resources)}"
    )

    relevant_count = 0

    for resource in resources:
        matches = _find_matches(
            resource,
            search_values,
        )

        match_names = {
            match.get("name")
            for match in matches
        }

        has_message = bool(
            {
                "communication_reference",
                "communication_id",
            }
            & match_names
        )

        has_service = bool(
            {
                "ydelse_reference",
                "ydelse_id",
            }
            & match_names
        )

        has_care_plan = bool(
            {
                "forloeb_reference",
                "forloeb_id",
            }
            & match_names
        )

        if not (
            has_message
            or has_service
            or has_care_plan
        ):
            continue

        relevant_count += 1

        _print_resource_result(
            title=(
                "RELEVANT BASIC "
                f"{resource.get('id', '')}"
            ),
            resource=resource,
            search_values=search_values,
        )

    print()
    print("=" * 100)
    print("KONKLUSION")
    print("=" * 100)
    print(
        "Antal Basic-resurser med besked-, "
        "ydelses- eller forløbsmatch: "
        f"{relevant_count}"
    )

    print()
    print(
        "Testen var kun læsende. "
        "Der blev ikke udført POST eller PUT."
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time
from pprint import pprint
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------
CURA_CREDENTIAL = "API_CURA"

BORGER_ID = (
    "b8fd9b01-5d85-4794-"
    "b1a7-5cd3c8e27a03"
)

CONTENT_PREVIEW_LENGTH = 50

COPENHAGEN_TIMEZONE = ZoneInfo(
    "Europe/Copenhagen"
)

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

# Profilerne bruger ikke nødvendigvis samme felt
# til borgeren.
#
# CuraCareHomeTask:
#     subject.reference peger på Patient/<borger-id>.
#
# CuraRequestTask:
#     for-extensionen peger på borgeren.
#     subject kan pege på den Communication, som
#     opgaven er oprettet i forbindelse med.
#
# CuraSimpleTask:
#     Repræsenterer en borgerrelateret opgave.
#     Testen afprøver både subject og for.
#
# CuraOrganizationalTask:
#     Er ifølge profilen ikke en borgeropgave.
#     Den medtages kun diagnostisk.
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
    ),
}


# ------------------------------------------------------------
# DATO FOR I DAG
# ------------------------------------------------------------
def get_today_period() -> tuple[str, str]:
    """
    Returnerer starten og slutningen af i dag
    i dansk tidszone.
    """
    today = datetime.now(
        COPENHAGEN_TIMEZONE
    ).date()

    start = datetime.combine(
        today,
        time.min,
        tzinfo=COPENHAGEN_TIMEZONE,
    )

    end = datetime.combine(
        today,
        time.max,
        tzinfo=COPENHAGEN_TIMEZONE,
    ).replace(
        microsecond=0
    )

    return (
        start.isoformat(),
        end.isoformat(),
    )


# ------------------------------------------------------------
# FORKORT KUN TESTUDSKRIFTEN
# ------------------------------------------------------------
def shorten_content_for_print(
    value,
):
    """
    Laver en separat kopi til print.

    Kun content_strings og contentString forkortes
    til 50 tegn.

    De originale API-data ændres ikke.
    """
    if isinstance(value, dict):
        printable = {}

        for key, child_value in value.items():
            if (
                key == "content_strings"
                and isinstance(
                    child_value,
                    list,
                )
            ):
                printable[key] = [
                    str(
                        content_string
                    )[
                        :CONTENT_PREVIEW_LENGTH
                    ]
                    for content_string
                    in child_value
                ]

            elif key == "contentString":
                printable[key] = str(
                    child_value
                )[
                    :CONTENT_PREVIEW_LENGTH
                ]

            else:
                printable[key] = (
                    shorten_content_for_print(
                        child_value
                    )
                )

        return printable

    if isinstance(value, list):
        return [
            shorten_content_for_print(
                item
            )
            for item in value
        ]

    return value


# ------------------------------------------------------------
# FHIR-HJÆLPERE
# ------------------------------------------------------------
def get_entries(
    bundle: dict,
) -> list:
    """
    Returnerer Bundle.entry som en sikker liste.

    Kun de faktiske entry-elementer tælles.
    Bundle.total bruges ikke som antal fund.
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


def get_profiles(
    resource: dict,
) -> list:
    """
    Returnerer resource.meta.profile.
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


def get_basic_resources(
    bundle: dict,
) -> list:
    """
    Henter Basic-ressourcerne fra et Bundle.
    """
    resources = []

    for entry in get_entries(bundle):
        if not isinstance(entry, dict):
            continue

        resource = entry.get(
            "resource",
            {},
        )

        if not isinstance(resource, dict):
            continue

        if (
            resource.get("resourceType")
            == "Basic"
        ):
            resources.append(
                resource
            )

    return resources


def contains_patient_reference(
    value,
    borger_id: str,
) -> bool:
    """
    Kontrollerer rekursivt, om ressourcen indeholder
    borgerreferencen.

    Funktionen finder både:
        Patient/<borger-id>
        <borger-id>

    Kontrollen foretages efter API-kaldet. Det beskytter
    imod, at CURA eventuelt ignorerer et ukendt filter.
    """
    expected_values = {
        borger_id,
        f"Patient/{borger_id}",
    }

    if isinstance(value, dict):
        reference = value.get(
            "reference"
        )

        if reference in expected_values:
            return True

        return any(
            contains_patient_reference(
                child_value,
                borger_id,
            )
            for child_value
            in value.values()
        )

    if isinstance(value, list):
        return any(
            contains_patient_reference(
                item,
                borger_id,
            )
            for item in value
        )

    return value in expected_values


# ------------------------------------------------------------
# ENDPOINT
# ------------------------------------------------------------
def build_endpoint(
    *,
    profile: str,
    citizen_field: str,
    citizen_value: str,
    start_datetime: str,
    end_datetime: str,
) -> str:
    """
    Bygger et opslag efter:

        - én Task-profil
        - én borger
        - dagens periode

    Datoen afgrænses med _lastUpdated.
    """
    parameters = [
        (
            "_profile",
            profile,
        ),
        (
            citizen_field,
            citizen_value,
        ),
        (
            "_lastUpdated",
            f"ge{start_datetime}",
        ),
        (
            "_lastUpdated",
            f"le{end_datetime}",
        ),
        (
            "_count",
            "1000",
        ),
    ]

    return (
        "Basic?"
        + urlencode(
            parameters,
            doseq=True,
        )
    )


# ------------------------------------------------------------
# KØR ÉT OPSLAG
# ------------------------------------------------------------
def run_search(
    *,
    profile_name: str,
    profile_url: str,
    citizen_field: str,
    citizen_value: str,
    start_datetime: str,
    end_datetime: str,
) -> dict:
    """
    Kører ét læsende opslag.

    Hvis CURA afviser én søgevariant, fortsætter testen
    med de øvrige varianter.
    """
    endpoint = build_endpoint(
        profile=profile_url,
        citizen_field=citizen_field,
        citizen_value=citizen_value,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )

    print("")
    print("=" * 100)
    print(
        f"{profile_name}: "
        f"{citizen_field}={citizen_value}"
    )
    print("=" * 100)
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
            f"Fejltype: "
            f"{type(error).__name__}"
        )
        print(str(error))

        return {
            "profile_name": profile_name,
            "citizen_field": citizen_field,
            "citizen_value": citizen_value,
            "endpoint": endpoint,
            "error": str(error),
            "resources": [],
        }

    resources = get_basic_resources(
        bundle
    )

    # Behold kun ressourcer, som faktisk indeholder
    # den valgte borgerreference.
    verified_resources = [
        resource
        for resource in resources
        if contains_patient_reference(
            resource,
            BORGER_ID,
        )
    ]

    print(
        "Antal entries fra CURA: "
        f"{len(get_entries(bundle))}"
    )
    print(
        "Antal verificeret på borgeren: "
        f"{len(verified_resources)}"
    )

    return {
        "profile_name": profile_name,
        "citizen_field": citizen_field,
        "citizen_value": citizen_value,
        "endpoint": endpoint,
        "error": "",
        "resources": verified_resources,
    }


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------
def main():
    """
    Henter dagens Task-ressourcer for én bestemt borger.

    Testen afprøver:

        Patient/<borger-id>
        <borger-id>

    Kombineret med de søgefelter, som profilerne
    forventes at bruge.

    Testen udfører kun GET-kald.
    Testen ændrer intet i CURA.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    (
        start_datetime,
        end_datetime,
    ) = get_today_period()

    print("")
    print("=" * 100)
    print(
        "HENTER DAGENS TASK-RESSOURCER "
        "FOR ÉN BORGER"
    )
    print("=" * 100)
    print(
        f"Miljø:     {CURA_CREDENTIAL}"
    )
    print(
        f"Borger-ID: {BORGER_ID}"
    )
    print(
        f"Fra:       {start_datetime}"
    )
    print(
        f"Til:       {end_datetime}"
    )
    print(
        "Kun testudskriften forkorter "
        "content_strings og contentString "
        "til 50 tegn."
    )

    citizen_values = (
        f"Patient/{BORGER_ID}",
        BORGER_ID,
    )

    search_results = []

    for (
        profile_name,
        profile_url,
    ) in TASK_PROFILES.items():
        citizen_fields = (
            PROFILE_SEARCH_FIELDS[
                profile_name
            ]
        )

        for citizen_field in citizen_fields:
            for citizen_value in citizen_values:
                search_results.append(
                    run_search(
                        profile_name=(
                            profile_name
                        ),
                        profile_url=(
                            profile_url
                        ),
                        citizen_field=(
                            citizen_field
                        ),
                        citizen_value=(
                            citizen_value
                        ),
                        start_datetime=(
                            start_datetime
                        ),
                        end_datetime=(
                            end_datetime
                        ),
                    )
                )

    # --------------------------------------------------------
    # FJERN DUBLETTER
    # --------------------------------------------------------
    #
    # Samme opgave kan blive returneret af flere
    # søgevarianter.
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

            resources_by_id[
                key
            ] = resource

    resources = list(
        resources_by_id.values()
    )

    # Nyeste ændringer vises først.
    resources.sort(
        key=lambda resource: str(
            (
                resource
                .get("meta", {})
                .get(
                    "lastUpdated",
                    "",
                )
            )
            if isinstance(
                resource.get("meta"),
                dict,
            )
            else ""
        ),
        reverse=True,
    )

    print("")
    print("=" * 100)
    print(
        "SAMLET RESULTAT FOR BORGEREN"
    )
    print("=" * 100)
    print(
        "Antal unikke Task-ressourcer: "
        f"{len(resources)}"
    )

    if not resources:
        print("")
        print(
            "Der blev ikke fundet Task-ressourcer, "
            "som både blev returneret af CURA og "
            "indeholdt borgerreferencen."
        )
        return

    # --------------------------------------------------------
    # PRINT KUN BORGERENS OPGAVER
    # --------------------------------------------------------
    for number, resource in enumerate(
        resources,
        start=1,
    ):
        print("")
        print("-" * 100)
        print(
            f"TASK {number} "
            f"AF {len(resources)}"
        )
        print("-" * 100)
        print(
            f"ID:       "
            f"{resource.get('id', '')}"
        )
        print(
            f"Profiler: "
            f"{get_profiles(resource)}"
        )

        printable_resource = (
            shorten_content_for_print(
                deepcopy(resource)
            )
        )

        pprint(
            printable_resource,
            width=180,
            sort_dicts=False,
        )


if __name__ == "__main__":
    main()
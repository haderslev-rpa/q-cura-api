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
# KONFIGURATION TIL TESTEN
# ------------------------------------------------------------
CURA_CREDENTIAL = "API_CURA"

CONTENT_PREVIEW_LENGTH = 50

COPENHAGEN_TIMEZONE = ZoneInfo(
    "Europe/Copenhagen"
)

# De fire Task-profiler, vi undersøger først.
#
# Alle profiler er implementeret som Basic-ressourcer
# i CURA.
TASK_PROFILES = {
    "CuraRequestTask": (
        "http://curafhir.dk/p/"
        "CuraRequestTask"
    ),
    "CuraSimpleTask": (
        "http://curafhir.dk/p/"
        "CuraSimpleTask"
    ),
    "CuraOrganizationalTask": (
        "http://curafhir.dk/p/"
        "CuraOrganizationalTask"
    ),
    "CuraCareHomeTask": (
        "http://curafhir.dk/p/"
        "CuraCareHomeTask"
    ),
}


# ------------------------------------------------------------
# DATO FOR I DAG
# ------------------------------------------------------------
def get_today_period() -> tuple[str, str]:
    """
    Returnerer starten og slutningen af dags dato
    i dansk tidszone.

    Eksempel:
        2026-10-07T00:00:00+02:00
        2026-10-07T23:59:59+02:00
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
    Laver en kopi til testudskrift.

    Kun felter med navnet content_strings eller
    contentString forkortes til de første 50 tegn.

    API-svaret og de oprindelige ressourcer
    ændres ikke.
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

    Bundle.total bruges ikke som antal returnerede
    ressourcer. Kun de faktiske entry-elementer tælles.
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
    Returnerer resource.meta.profile som en sikker liste.
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
    Henter alle Basic-ressourcer fra et Bundle.
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
            != "Basic"
        ):
            continue

        resources.append(
            resource
        )

    return resources


# ------------------------------------------------------------
# BYG ENDPOINT
# ------------------------------------------------------------
def build_endpoint(
    start_datetime: str,
    end_datetime: str,
    profile: str | None = None,
) -> str:
    """
    Bygger et læsende opslag efter Basic-ressourcer,
    der er ændret i dag.

    _lastUpdated bruges til at afgrænse perioden.

    Hvis profile angives, begrænses opslaget til
    én Task-profil.
    """
    parameters = [
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

    if profile:
        parameters.insert(
            0,
            (
                "_profile",
                profile,
            ),
        )

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
    search_name: str,
    start_datetime: str,
    end_datetime: str,
    profile: str | None = None,
) -> dict:
    """
    Kører ét diagnostisk GET-opslag.

    En eventuel fejl gemmes i resultatet, så testen
    kan fortsætte med de øvrige profiler.
    """
    endpoint = build_endpoint(
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        profile=profile,
    )

    print("")
    print("=" * 100)
    print(search_name)
    print("=" * 100)
    print(
        f"Profil:   "
        f"{profile or 'Ingen profil, alle Basic'}"
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
        print("")
        print("OPSLAGET FEJLEDE")
        print(
            f"Fejltype: "
            f"{type(error).__name__}"
        )
        print(str(error))

        return {
            "search_name": search_name,
            "profile": profile,
            "endpoint": endpoint,
            "error": str(error),
            "resources": [],
        }

    resources = get_basic_resources(
        bundle
    )

    bundle_total = None

    if isinstance(bundle, dict):
        bundle_total = bundle.get(
            "total"
        )

    print("")
    print(
        f"Bundle total:   {bundle_total}"
    )
    print(
        f"Antal entries:  "
        f"{len(get_entries(bundle))}"
    )
    print(
        f"Basic-resurser: "
        f"{len(resources)}"
    )

    return {
        "search_name": search_name,
        "profile": profile,
        "endpoint": endpoint,
        "error": "",
        "resources": resources,
    }


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------
def main():
    """
    Henter Task-lignende Basic-ressourcer,
    som er ændret i dag.

    Flow:
        1. Afprøv alle Basic-ressourcer uden profilfilter.
        2. Afprøv hver kendt Task-profil separat.
        3. Saml og fjern dubletter.
        4. Print alle felter.
        5. Forkort kun contentString i testudskriften.

    Testen udfører kun GET-kald.
    Testen ændrer ikke data i CURA.
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
        "HENTER TASK-RESSOURCER FRA I DAG"
    )
    print("=" * 100)
    print(
        f"Miljø: {CURA_CREDENTIAL}"
    )
    print(
        f"Fra:   {start_datetime}"
    )
    print(
        f"Til:   {end_datetime}"
    )
    print(
        "Bemærk: Kun testudskriften forkorter "
        "content_strings og contentString "
        "til 50 tegn."
    )

    search_results = []

    # --------------------------------------------------------
    # TEST 1: ALLE BASIC
    # --------------------------------------------------------
    #
    # CURA kan vælge at afvise så bredt et opslag.
    # Hvis opslaget fejler, fortsætter testen automatisk
    # med de profilspecifikke opslag.
    search_results.append(
        run_search(
            search_name=(
                "TEST 1: ALLE BASIC-RESSOURCER "
                "ÆNDRET I DAG"
            ),
            start_datetime=(
                start_datetime
            ),
            end_datetime=end_datetime,
            profile=None,
        )
    )

    # --------------------------------------------------------
    # TEST 2 OG FREM: ÉN TASK-PROFIL AD GANGEN
    # --------------------------------------------------------
    for (
        profile_name,
        profile_url,
    ) in TASK_PROFILES.items():
        search_results.append(
            run_search(
                search_name=(
                    f"TASK-PROFIL: "
                    f"{profile_name}"
                ),
                start_datetime=(
                    start_datetime
                ),
                end_datetime=(
                    end_datetime
                ),
                profile=profile_url,
            )
        )

    # --------------------------------------------------------
    # SAML OG FJERN DUBLETTER
    # --------------------------------------------------------
    #
    # En ressource kan både være fundet i det brede opslag
    # og i et profilspecifikt opslag.
    resources_by_key = {}

    for search_result in search_results:
        for resource in search_result.get(
            "resources",
            [],
        ):
            resource_id = str(
                resource.get("id")
                or ""
            )

            profiles = tuple(
                get_profiles(resource)
            )

            if resource_id:
                key = (
                    resource_id,
                    profiles,
                )
            else:
                key = repr(resource)

            resources_by_key[key] = (
                resource
            )

    resources = list(
        resources_by_key.values()
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
    print("SAMLET RESULTAT")
    print("=" * 100)
    print(
        "Antal unikke Basic/Task-ressourcer: "
        f"{len(resources)}"
    )

    if not resources:
        print("")
        print(
            "Ingen ressourcer blev returneret."
        )
        print(
            "Se fejlteksten under hvert opslag "
            "for at afgøre, om CURA afviste "
            "_lastUpdated eller opslagets bredde."
        )
        return

    # --------------------------------------------------------
    # PRINT ALLE RETURNEREDE RESSOURCER
    # --------------------------------------------------------
    for number, resource in enumerate(
        resources,
        start=1,
    ):
        print("")
        print("-" * 100)
        print(
            f"RESOURCE {number} "
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

        # Der laves en separat kopi til print.
        # Den oprindelige resource ændres ikke.
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
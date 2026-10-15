import os
from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)

CURA_CREDENTIAL = "API_CURA"
BORGER_ID = "39dde427-b1fc-42b3-9e85-fccf727ee3bf"

CARE_PLAN_PROFILE = (
    "http://curafhir.dk/p/CuraCarePlan"
)


def build_endpoint(
    subject_value: str,
    include_profile: bool,
) -> str:
    """Bygger et CarePlan-opslag for én subject-variant."""
    parameters = [
        (
            "subject",
            subject_value,
        ),
        (
            "_count",
            "1000",
        ),
    ]

    if include_profile:
        parameters.append(
            (
                "_profile",
                CARE_PLAN_PROFILE,
            )
        )

    return (
        "CarePlan?"
        + urlencode(
            parameters,
            doseq=True,
        )
    )


def get_bundle_summary(
    resultat,
) -> dict:
    """Returnerer en lille teknisk oversigt over et råt FHIR Bundle."""
    if not isinstance(resultat, dict):
        raise RuntimeError(
            "Det rå CURA-svar er ikke en dictionary."
        )

    if resultat.get("resourceType") != "Bundle":
        raise RuntimeError(
            "Forventede et FHIR Bundle, men fik "
            f"{resultat.get('resourceType')!r}."
        )

    entries = resultat.get(
        "entry",
        [],
    )

    links = resultat.get(
        "link",
        [],
    )

    if not isinstance(entries, list):
        raise RuntimeError(
            "Bundle.entry er ikke en liste."
        )

    if not isinstance(links, list):
        raise RuntimeError(
            "Bundle.link er ikke en liste."
        )

    care_plan_count = 0

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        resource = entry.get(
            "resource",
            {},
        )

        if (
            isinstance(resource, dict)
            and resource.get("resourceType")
            == "CarePlan"
        ):
            care_plan_count += 1

    return {
        "bundle_total": resultat.get(
            "total"
        ),
        "entry_count": len(
            entries
        ),
        "care_plan_count": (
            care_plan_count
        ),
        "link_relations": [
            link.get("relation")
            for link in links
            if isinstance(link, dict)
        ],
    }


def run_search(
    label: str,
    subject_value: str,
    include_profile: bool,
) -> dict:
    """Kører ét læsende CarePlan-opslag og bevarer hele råsvaret."""
    endpoint = build_endpoint(
        subject_value=subject_value,
        include_profile=include_profile,
    )

    try:
        resultat = get(
            endpoint,
            raw=True,
        )

        return {
            "label": label,
            "endpoint": endpoint,
            "success": True,
            "summary": get_bundle_summary(
                resultat
            ),
            "raw_result": resultat,
        }

    except Exception as error:
        return {
            "label": label,
            "endpoint": endpoint,
            "success": False,
            "error_type": (
                type(error).__name__
            ),
            "error": str(error),
            "raw_result": None,
        }


def main():
    """Afprøver fire måder at hente borgerens CuraCarePlan-forløb.

    Der prøves:
        1. subject=<borger-id>, uden profil
        2. subject=<borger-id>, med CuraCarePlan-profil
        3. subject=Patient/<borger-id>, uden profil
        4. subject=Patient/<borger-id>, med CuraCarePlan-profil

    Hele det rå svar printes for hver variant, så id, extensions,
    subject, status, periode og øvrige felter kan sammenlignes med
    de rå ProcedureRequest-ydelser.
    """
    borger_id = os.getenv(
        "BORGER_ID",
        BORGER_ID,
    ).strip()

    if (
        not borger_id
        or borger_id == "SKRIV_BORGER_ID_HER"
    ):
        raise ValueError(
            "Skriv borgerens Cura-ID i testfilen "
            "eller angiv BORGER_ID i .env."
        )

    set_cura_credential(
        CURA_CREDENTIAL
    )

    searches = [
        run_search(
            label=(
                "Rent borger-id uden profil"
            ),
            subject_value=borger_id,
            include_profile=False,
        ),
        run_search(
            label=(
                "Rent borger-id med "
                "CuraCarePlan-profil"
            ),
            subject_value=borger_id,
            include_profile=True,
        ),
        run_search(
            label=(
                "Patient-reference uden profil"
            ),
            subject_value=(
                f"Patient/{borger_id}"
            ),
            include_profile=False,
        ),
        run_search(
            label=(
                "Patient-reference med "
                "CuraCarePlan-profil"
            ),
            subject_value=(
                f"Patient/{borger_id}"
            ),
            include_profile=True,
        ),
    ]

    for number, search in enumerate(
        searches,
        start=1,
    ):
        print("\n" + "=" * 100)
        print(
            f"FORLØBSSØGNING {number}: "
            f"{search['label']}"
        )
        print("=" * 100)

        print(
            f"Endpoint: {search['endpoint']}"
        )

        print(
            "Søgning lykkedes: "
            f"{search['success']}"
        )

        if search["success"]:
            print("Oversigt:")

            pprint(
                search["summary"],
                width=180,
                sort_dicts=False,
            )

            print("\nRåt CURA-svar:")

            pprint(
                search["raw_result"],
                width=180,
                sort_dicts=False,
            )

        else:
            print(
                "Fejltype: "
                f"{search['error_type']}"
            )

            print(
                f"Fejl: {search['error']}"
            )

    print(
        "\nTesten er kun læsende. "
        "Der udføres ingen POST eller PUT."
    )


if __name__ == "__main__":
    main()
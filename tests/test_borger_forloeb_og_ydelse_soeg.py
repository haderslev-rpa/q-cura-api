from __future__ import annotations

from datetime import datetime
from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# KONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA_TEST"

BORGER_ID = "0f5403d0-1575-4e9c-842e-d399ff55198a" # Rune robot brugeren.
# Sæt tidspunktet til lige før den manuelle oprettelse.
#
# Eksempel:
# OPRETTET_EFTER = "2026-10-14T13:30:00+02:00"
#
# Brug altid tidszone i værdien.
OPRETTET_EFTER = (
    "2026-10-14T12:00:00+02:00"
)

# Hvis forløbet har en tydelig startdato, kan den bruges
# som ekstra lokalt filter.
#
# Sæt til None, hvis startdatoen ikke skal bruges.
FORLOEB_STARTDATO = "2026-10-14"

# Første gang skal værdien være None.
#
# Når det nye forløbs-id er fundet, indsættes id'et her.
# Derefter kan testen finde ydelsen, som peger på forløbet.
FORLOEB_ID = None

# Begrænser kun udskriften.
MAKS_ANTAL_RESULTATER = 20


# ------------------------------------------------------------
# CURA-PROFILER OG EXTENSIONS
# ------------------------------------------------------------

CARE_PLAN_PROFILE = (
    "http://curafhir.dk/p/CuraCarePlan"
)

YDELSE_PROFILE = (
    "http://curafhir.dk/p/"
    "CuraGrantedProcedureRequest"
)

EXTENSION_PATHWAY = (
    "http://curafhir.dk/x/"
    "CuraGrantedProcedureRequest/pathway"
)


# ------------------------------------------------------------
# GENERELLE HJÆLPEFUNKTIONER
# ------------------------------------------------------------


def parse_datetime(
    value: str | None,
) -> datetime | None:
    """
    Konverterer et ISO-tidspunkt til datetime.

    Returnerer None, hvis værdien er tom eller ugyldig.
    """
    value = str(
        value
        or ""
    ).strip()

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        return None


def get_bundle_resources(
    bundle: dict,
    resource_type: str,
) -> list[dict]:
    """
    Henter resources af en bestemt type fra et
    råt FHIR Bundle.
    """
    if not isinstance(bundle, dict):
        return []

    resources = []

    for entry in bundle.get("entry") or []:
        if not isinstance(entry, dict):
            continue

        resource = entry.get("resource")

        if not isinstance(resource, dict):
            continue

        if (
            resource.get("resourceType")
            != resource_type
        ):
            continue

        resources.append(
            resource
        )

    return resources


def get_profiles(
    resource: dict,
) -> list[str]:
    """
    Henter meta.profile som en liste.
    """
    meta = resource.get("meta")

    if not isinstance(meta, dict):
        return []

    profiles = meta.get("profile")

    if not isinstance(profiles, list):
        return []

    return [
        str(profile)
        for profile in profiles
        if profile
    ]


def get_last_updated(
    resource: dict,
) -> str:
    """
    Henter meta.lastUpdated som tekst.
    """
    meta = resource.get("meta")

    if not isinstance(meta, dict):
        return ""

    return str(
        meta.get("lastUpdated")
        or ""
    )


def is_created_after(
    resource: dict,
    created_after: str,
) -> bool:
    """
    Kontrollerer om meta.lastUpdated er lig med eller
    efter det valgte tidspunkt.
    """
    resource_datetime = parse_datetime(
        get_last_updated(resource)
    )

    filter_datetime = parse_datetime(
        created_after
    )

    if resource_datetime is None:
        return False

    if filter_datetime is None:
        raise ValueError(
            "OPRETTET_EFTER er ikke et gyldigt "
            "ISO-tidspunkt."
        )

    return (
        resource_datetime
        >= filter_datetime
    )


def find_extension(
    resource: dict,
    extension_url: str,
) -> dict | None:
    """
    Finder en extension ud fra dens fulde URL.
    """
    extensions = resource.get("extension")

    if not isinstance(extensions, list):
        return None

    for extension in extensions:
        if not isinstance(extension, dict):
            continue

        if extension.get("url") == extension_url:
            return extension

    return None


def get_reference(
    reference_data,
) -> str:
    """
    Returnerer en FHIR-reference som tekst.
    """
    if isinstance(reference_data, str):
        return reference_data.strip()

    if isinstance(reference_data, dict):
        return str(
            reference_data.get("reference")
            or ""
        ).strip()

    return ""


def get_extension_reference(
    resource: dict,
    extension_url: str,
) -> str:
    """
    Henter valueReference.reference fra en extension.
    """
    extension = find_extension(
        resource,
        extension_url,
    )

    if extension is None:
        return ""

    return get_reference(
        extension.get("valueReference")
    )


def get_code_display(
    resource: dict,
) -> str:
    """
    Henter første display eller code fra resource.code.
    """
    code_data = resource.get("code")

    if not isinstance(code_data, dict):
        return ""

    if code_data.get("text"):
        return str(
            code_data["text"]
        )

    codings = code_data.get("coding")

    if not isinstance(codings, list):
        return ""

    for coding in codings:
        if not isinstance(coding, dict):
            continue

        return str(
            coding.get("display")
            or coding.get("code")
            or ""
        )

    return ""


# ------------------------------------------------------------
# HENT FORLØB
# ------------------------------------------------------------


def hent_forloeb_for_borger(
    borger_id: str,
) -> list[dict]:
    """
    Henter borgerens CarePlan-resurser.

    Funktionen forsøger først samme subject-format,
    som den eksisterende ydelsesfunktion anvender.

    Hvis CURA ikke accepterer det, forsøges den fulde
    Patient-reference.
    """
    queries = [
        [
            (
                "subject",
                borger_id,
            ),
            (
                "_profile",
                CARE_PLAN_PROFILE,
            ),
        ],
        [
            (
                "subject",
                f"Patient/{borger_id}",
            ),
            (
                "_profile",
                CARE_PLAN_PROFILE,
            ),
        ],
    ]

    errors = []

    for query_parameters in queries:
        endpoint = (
            "CarePlan?"
            + urlencode(query_parameters)
        )

        try:
            bundle = get(
                endpoint,
                raw=True,
            )

            return get_bundle_resources(
                bundle,
                "CarePlan",
            )

        except RuntimeError as error:
            errors.append(
                str(error)
            )

    raise RuntimeError(
        "Ingen af CarePlan-opslagene blev accepteret "
        "af CURA.\n\n"
        + "\n\n".join(errors)
    )


def filter_nye_forloeb(
    resources: list[dict],
) -> list[dict]:
    """
    Filtrerer forløb lokalt på:

    - CuraCarePlan-profil
    - meta.lastUpdated
    - eventuelt period.start
    """
    matches = []

    for resource in resources:
        profiles = get_profiles(
            resource
        )

        if CARE_PLAN_PROFILE not in profiles:
            continue

        if not is_created_after(
            resource,
            OPRETTET_EFTER,
        ):
            continue

        period = resource.get("period")

        if not isinstance(period, dict):
            period = {}

        start = str(
            period.get("start")
            or ""
        )

        if (
            FORLOEB_STARTDATO
            and not start.startswith(
                FORLOEB_STARTDATO
            )
        ):
            continue

        matches.append(
            resource
        )

    matches.sort(
        key=get_last_updated,
        reverse=True,
    )

    return matches


def normaliser_forloeb(
    resource: dict,
) -> dict:
    """
    Laver en kort udskrift af et CarePlan.
    """
    subject_reference = get_reference(
        resource.get("subject")
    )

    period = resource.get("period")

    if not isinstance(period, dict):
        period = {}

    return {
        "forloeb_id": str(
            resource.get("id")
            or ""
        ),
        "reference": (
            "CarePlan/"
            f"{resource.get('id', '')}"
        ),
        "last_updated": get_last_updated(
            resource
        ),
        "status": resource.get("status"),
        "borger_reference": (
            subject_reference
        ),
        "start": period.get("start"),
        "end": period.get("end"),
        "title": resource.get("title"),
        "description": (
            resource.get("description")
        ),
    }


# ------------------------------------------------------------
# HENT YDELSER
# ------------------------------------------------------------


def hent_ydelser_for_borger(
    borger_id: str,
) -> list[dict]:
    """
    Henter borgerens CuraGrantedProcedureRequest-
    resurser.

    Endpointet følger mønstret fra den eksisterende
    borger_ydelser.py.
    """
    endpoint = (
        "ProcedureRequest?"
        + urlencode(
            [
                (
                    "subject",
                    borger_id,
                ),
                (
                    "_profile",
                    YDELSE_PROFILE,
                ),
                (
                    "_sort",
                    "orderedOn",
                ),
            ]
        )
    )

    bundle = get(
        endpoint,
        raw=True,
    )

    return get_bundle_resources(
        bundle,
        "ProcedureRequest",
    )


def filter_ydelser_til_forloeb(
    resources: list[dict],
    forloeb_id: str,
) -> list[dict]:
    """
    Beholder kun ydelser med:

    pathway = CarePlan/<forløbs-id>

    Der filtreres desuden lokalt på meta.lastUpdated.
    """
    expected_reference = (
        f"CarePlan/{forloeb_id}"
    )

    matches = []

    for resource in resources:
        profiles = get_profiles(
            resource
        )

        if YDELSE_PROFILE not in profiles:
            continue

        pathway_reference = (
            get_extension_reference(
                resource,
                EXTENSION_PATHWAY,
            )
        )

        if (
            pathway_reference
            != expected_reference
        ):
            continue

        if not is_created_after(
            resource,
            OPRETTET_EFTER,
        ):
            continue

        matches.append(
            resource
        )

    matches.sort(
        key=get_last_updated,
        reverse=True,
    )

    return matches


def normaliser_ydelse(
    resource: dict,
) -> dict:
    """
    Laver en kort udskrift af en ProcedureRequest.
    """
    pathway_reference = (
        get_extension_reference(
            resource,
            EXTENSION_PATHWAY,
        )
    )

    return {
        "ydelse_id": str(
            resource.get("id")
            or ""
        ),
        "reference": (
            "ProcedureRequest/"
            f"{resource.get('id', '')}"
        ),
        "last_updated": get_last_updated(
            resource
        ),
        "status": resource.get("status"),
        "ordered_on": (
            resource.get("orderedOn")
        ),
        "navn": get_code_display(
            resource
        ),
        "borger_reference": get_reference(
            resource.get("subject")
        ),
        "performer_reference": get_reference(
            resource.get("performer")
        ),
        "forloeb_reference": (
            pathway_reference
        ),
    }


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def main():
    """
    Testen udfører kun GET-kald.

    Første kørsel:
        FORLOEB_ID = None

        Testen viser nye CarePlan-kandidater.

    Anden kørsel:
        Indsæt det fundne CarePlan-id i FORLOEB_ID.

        Testen viser kun ydelser, som peger på
        dette konkrete CarePlan.
    """
    if BORGER_ID == "INDSAET_BORGER_ID":
        raise ValueError(
            "Udfyld BORGER_ID"
        )

    set_cura_credential(
        CURA_CREDENTIAL
    )

    print()
    print("=" * 100)
    print("SØG EFTER NYT FORLØB")
    print("=" * 100)
    print(f"Borger-id:       {BORGER_ID}")
    print(f"Oprettet efter:  {OPRETTET_EFTER}")
    print(f"Startdato:       {FORLOEB_STARTDATO}")

    alle_forloeb = hent_forloeb_for_borger(
        BORGER_ID
    )

    nye_forloeb = filter_nye_forloeb(
        alle_forloeb
    )

    print()
    print(
        "Antal CarePlan-resurser fra CURA: "
        f"{len(alle_forloeb)}"
    )
    print(
        "Antal kandidater efter lokalt filter: "
        f"{len(nye_forloeb)}"
    )

    for index, resource in enumerate(
        nye_forloeb[:MAKS_ANTAL_RESULTATER],
        start=1,
    ):
        print()
        print("-" * 100)
        print(f"FORLØBSKANDIDAT {index}")
        print("-" * 100)

        pprint(
            normaliser_forloeb(resource),
            width=180,
            sort_dicts=False,
        )

    if not nye_forloeb:
        print()
        print(
            "Der blev ikke fundet et nyt forløb. "
            "Kontrollér OPRETTET_EFTER og "
            "FORLOEB_STARTDATO."
        )

    if not FORLOEB_ID:
        print()
        print("=" * 100)
        print("NÆSTE TRIN")
        print("=" * 100)
        print(
            "Find det rigtige forloeb_id ovenfor, "
            "og indsæt det i FORLOEB_ID."
        )
        print(
            "Opret derefter ydelsen manuelt på netop "
            "dette forløb og kør testen igen."
        )
        print(
            "Der blev kun udført GET-kald."
        )
        return

    print()
    print("=" * 100)
    print("SØG EFTER YDELSE PÅ DET VALGTE FORLØB")
    print("=" * 100)
    print(
        f"Forløbsreference: CarePlan/{FORLOEB_ID}"
    )

    alle_ydelser = hent_ydelser_for_borger(
        BORGER_ID
    )

    nye_ydelser = filter_ydelser_til_forloeb(
        alle_ydelser,
        FORLOEB_ID,
    )

    print()
    print(
        "Antal ProcedureRequest-resurser fra CURA: "
        f"{len(alle_ydelser)}"
    )
    print(
        "Antal ydelser på det valgte forløb: "
        f"{len(nye_ydelser)}"
    )

    for index, resource in enumerate(
        nye_ydelser[:MAKS_ANTAL_RESULTATER],
        start=1,
    ):
        print()
        print("-" * 100)
        print(f"YDELSESKANDIDAT {index}")
        print("-" * 100)

        pprint(
            normaliser_ydelse(resource),
            width=180,
            sort_dicts=False,
        )

    if not nye_ydelser:
        print()
        print(
            "Der blev ikke fundet en ny ydelse med "
            f"pathway = CarePlan/{FORLOEB_ID}."
        )

    print()
    print("=" * 100)
    print("TESTEN ER FÆRDIG")
    print("=" * 100)
    print(
        "Der blev kun udført GET-kald. "
        "Ingen ressourcer blev ændret."
    )


if __name__ == "__main__":
    main()
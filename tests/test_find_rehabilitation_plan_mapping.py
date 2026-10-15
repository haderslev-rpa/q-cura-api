"""
LÆSENDE TEST AF REHABILITATIONPLANMAPPING
=========================================

Testen undersøger, om CURA allerede har oprettet en Basic-resource med en
RehabilitationPlanMapping-profil, som refererer til det valgte CarePlan,
den oprettede ProcedureRequest eller borgeren.

Testen udfører kun GET-kald. Den udfører ingen POST eller PUT.

De præcise profilnavne er endnu ikke dokumenteret i q-cura-api. Derfor prøver
testen to eksplicitte profilkandidater og viser tydeligt, hvilke endpoints CURA
accepterer eller afviser. Et fund accepteres kun, hvis ressourcen samtidig
indeholder reference til det valgte CarePlan eller den valgte ProcedureRequest.
"""

from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import get, set_cura_credential


# ------------------------------------------------------------
# TESTDATA
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA_TEST"

BORGER_ID = "0f5403d0-1575-4e9c-842e-d399ff55198a"
FORLOEB_ID = "32c60a31-f496-44c7-9524-27720116afe7"
YDELSE_ID = "e76a414c-6b3c-4178-bbdd-df912f830070"

# Profilkandidater. Der gættes ikke på resultatet. Testen viser,
# hvilken profil CURA faktisk accepterer og returnerer.
PROFILE_KANDIDATER = (
    "http://curafhir.dk/p/RehabilitationPlanMapping",
    "http://curafhir.dk/p/CuraRehabilitationPlanMapping",
)


# ------------------------------------------------------------
# HJÆLPEFUNKTIONER
# ------------------------------------------------------------


def get_entries(bundle: dict) -> list:
    """Returnerer Bundle.entry som en sikker liste."""
    if not isinstance(bundle, dict):
        return []

    entries = bundle.get("entry", [])
    return entries if isinstance(entries, list) else []


def get_profiles(resource: dict) -> list[str]:
    """Returnerer resource.meta.profile som en liste."""
    meta = resource.get("meta", {})

    if not isinstance(meta, dict):
        return []

    profiles = meta.get("profile", [])

    if not isinstance(profiles, list):
        return []

    return [str(profile) for profile in profiles]


def contains_exact_value(value, expected_values: set[str]) -> bool:
    """
    Søger rekursivt efter en præcis reference eller id-værdi.

    Funktionen fortolker ikke ukendte felter. Den kontrollerer kun,
    om en dictionary, liste eller tekst indeholder en af de præcise
    værdier, som testen leder efter.
    """
    if isinstance(value, dict):
        return any(
            contains_exact_value(child, expected_values)
            for child in value.values()
        )

    if isinstance(value, list):
        return any(
            contains_exact_value(child, expected_values)
            for child in value
        )

    if isinstance(value, str):
        return value.strip() in expected_values

    return False


def build_endpoint(profile: str) -> str:
    """Bygger et læsende Basic-opslag for én profil."""
    return "Basic?" + urlencode(
        [
            ("_profile", profile),
            ("_count", "1000"),
        ],
        doseq=True,
    )


def run_profile_search(profile: str) -> dict:
    """Kører ét GET-opslag og samler fund, der matcher testens id'er."""
    endpoint = build_endpoint(profile)

    print()
    print("=" * 100)
    print(f"PROFIL:   {profile}")
    print(f"ENDPOINT: {endpoint}")
    print("=" * 100)

    try:
        bundle = get(endpoint, raw=True)
    except Exception as error:
        print(f"CURA afviste opslaget: {type(error).__name__}: {error}")
        return {
            "profile": profile,
            "endpoint": endpoint,
            "accepted": False,
            "error": str(error),
            "resources": [],
            "matching_resources": [],
        }

    if not isinstance(bundle, dict):
        raise RuntimeError("CURA returnerede ikke en dictionary.")

    entries = get_entries(bundle)
    resources = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        resource = entry.get("resource", {})

        if not isinstance(resource, dict):
            continue

        resources.append(resource)

    expected_references = {
        BORGER_ID,
        f"Patient/{BORGER_ID}",
        FORLOEB_ID,
        f"CarePlan/{FORLOEB_ID}",
        YDELSE_ID,
        f"ProcedureRequest/{YDELSE_ID}",
    }

    matching_resources = [
        resource
        for resource in resources
        if contains_exact_value(resource, expected_references)
    ]

    print(f"Bundle entries:              {len(entries)}")
    print(f"Basic-resourcer:             {len(resources)}")
    print(f"Match på testens referencer: {len(matching_resources)}")

    if matching_resources:
        print()
        print("MATCHENDE RESSOURCER")
        print("-" * 100)

        for resource in matching_resources:
            print(
                f"Basic-id: {resource.get('id')} | "
                f"Profiler: {get_profiles(resource)}"
            )
            pprint(resource, width=180, sort_dicts=False)
            print("-" * 100)

    return {
        "profile": profile,
        "endpoint": endpoint,
        "accepted": True,
        "bundle_total": bundle.get("total"),
        "entry_count": len(entries),
        "resource_count": len(resources),
        "resources": resources,
        "matching_resources": matching_resources,
    }


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def main() -> None:
    """Undersøger læsende, om mappingen allerede findes."""
    if CURA_CREDENTIAL != "API_CURA_TEST":
        raise ValueError(
            "Testen må kun køres med CURA_CREDENTIAL='API_CURA_TEST'."
        )

    for field_name, value in (
        ("BORGER_ID", BORGER_ID),
        ("FORLOEB_ID", FORLOEB_ID),
        ("YDELSE_ID", YDELSE_ID),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} skal være udfyldt.")

    set_cura_credential(CURA_CREDENTIAL)

    print()
    print("=" * 100)
    print("SØGER EFTER REHABILITATIONPLANMAPPING")
    print("=" * 100)
    print(f"Credential: {CURA_CREDENTIAL}")
    print(f"Borger:     Patient/{BORGER_ID}")
    print(f"Forløb:     CarePlan/{FORLOEB_ID}")
    print(f"Ydelse:     ProcedureRequest/{YDELSE_ID}")
    print("Testen udfører kun GET-kald.")

    results = [
        run_profile_search(profile)
        for profile in PROFILE_KANDIDATER
    ]

    matching_resources = []
    seen_ids = set()

    for result in results:
        for resource in result["matching_resources"]:
            resource_id = str(resource.get("id") or "")
            identity = resource_id or repr(resource)

            if identity in seen_ids:
                continue

            seen_ids.add(identity)
            matching_resources.append(resource)

    accepted_profiles = [
        result["profile"]
        for result in results
        if result["accepted"]
    ]

    print()
    print("=" * 100)
    print("SAMLET RESULTAT")
    print("=" * 100)
    print(f"Accepterede profilopslag: {accepted_profiles}")
    print(f"Entydige matchende resources: {len(matching_resources)}")

    if matching_resources:
        print()
        print(
            "RESULTAT: Der blev fundet mindst én eksisterende Basic-resource, "
            "som har en af profilkandidaterne og refererer til testens borger, "
            "forløb eller ydelse. Undersøg RAW-resource ovenfor for den præcise "
            "relation, før der udvikles oprettelseslogik."
        )
    else:
        print()
        print(
            "RESULTAT: Testen fandt ingen RehabilitationPlanMapping med de "
            "afprøvede profiler og referencer. Det beviser ikke alene, at mappingen "
            "mangler. Profilnavn, resourceType eller søgemodel kan være anderledes. "
            "Opret derfor ikke mappingen endnu. Næste trin er at sammenligne med "
            "en mapping, som er oprettet manuelt i CURA, og hente dens RAW-resource."
        )


if __name__ == "__main__":
    main()

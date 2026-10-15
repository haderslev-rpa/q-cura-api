from pprint import pprint

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA"

MAPPING_BASIC_ID = (
    "c967c694-19f3-4b72-"
    "9903-c4318fef8fd4"
)


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main():
    """
    Henter den konkrete mapping-resource direkte fra
    CURAs FHIR API.

    Testen udfører kun GET og udskriver hele ressourcen RAW.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    endpoint = (
        f"Basic/{MAPPING_BASIC_ID}"
    )

    print()
    print("=" * 100)
    print("RAW REHABILITATIONPLAN MAPPING - BASIC")
    print("=" * 100)
    print(f"Mapping-id: {MAPPING_BASIC_ID}")
    print(f"Endpoint:   {endpoint}")
    print()

    raw_mapping = get(
        endpoint,
        raw=True,
    )

    pprint(
        raw_mapping,
        width=200,
        sort_dicts=False,
    )

    print()
    print("=" * 100)
    print("TESTEN ER FÆRDIG")
    print("=" * 100)
    print(
        "Der blev kun udført ét GET-kald. "
        "Ingen ressourcer blev ændret."
    )


if __name__ == "__main__":
    main()
from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.kommunikation import (
    set_rehabilitation_plan_subtype,
)

# Opsætning for denne manuelle test.
CURA_CREDENTIAL_NAME = "API_CURA"
COMMUNICATION_ID = "9cfa0f85-431a-4625-8b72-6e610127c049"
SUBTYPE_CODE = "BASIC"  # BASIC eller ADVANCED


def main():
    """Kalder produktionsfunktionen og viser resultatet.

    OBS: Dette er en rigtig opdatering i det valgte CURA-miljø.
    """
    set_cura_credential(CURA_CREDENTIAL_NAME)

    print(f"Ønsket undertype: {SUBTYPE_CODE}")
    print("Kalder produktionsfunktionen med rigtig opdatering.")

    result = set_rehabilitation_plan_subtype(
        communication_id=COMMUNICATION_ID,
        subtype_code=SUBTYPE_CODE,
    )

    print()
    print("=" * 100)
    print("RESULTAT FRA PRODUKTIONSFUNKTIONEN")
    print("=" * 100)
    pprint(result, width=180, sort_dicts=False)

    if (
        result.get("verified") is not True
        or result.get("stored_subtype") != SUBTYPE_CODE
    ):
        raise RuntimeError("Den ønskede undertype blev ikke verificeret.")

    if result.get("changed") is True:
        print("Undertypen blev ændret og verificeret i CURA.")
    else:
        print("Undertypen var allerede korrekt. Ingen PUT var nødvendig.")


if __name__ == "__main__":
    main()
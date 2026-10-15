import os
from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_ydelser import (
    borger_ydelser_hent,
)

CURA_CREDENTIAL = "API_CURA_TEST"
BORGER_ID = "0f5403d0-1575-4e9c-842e-d399ff55198a"


def get_bundle_entries(resultat) -> list:
    """Henter Bundle.entry fra det rå CURA-svar."""
    if not isinstance(resultat, dict):
        raise RuntimeError(
            "Det rå CURA-svar er ikke en dictionary."
        )

    if resultat.get("resourceType") != "Bundle":
        raise RuntimeError(
            "Forventede et FHIR Bundle, men fik "
            f"{resultat.get('resourceType')!r}."
        )

    entries = resultat.get("entry", [])

    if not isinstance(entries, list):
        raise RuntimeError(
            "Bundle.entry er ikke en liste."
        )

    return entries


def main():
    """Henter og printer borgerens ydelser som råt FHIR Bundle.

    Ved raw=True returnerer borger_ydelser_hent() det rå CURA-svar.
    Derfor findes felterne borger_id, antal_ydelser og found ikke på
    resultatets øverste niveau. Testen beregner i stedet antal ud fra
    Bundle.entry og printer derefter hele det rå svar uændret.
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

    resultat = borger_ydelser_hent(
        borger_id=borger_id,
        raw=True,
    )

    entries = get_bundle_entries(
        resultat
    )

    ydelser = []

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
            == "ProcedureRequest"
        ):
            ydelser.append(
                resource
            )

    print("\n" + "=" * 100)
    print(
        "RÅ YDELSER FRA BORGER_YDELSER_HENT"
    )
    print("=" * 100)
    print(
        f"Borger-ID:              {borger_id}"
    )
    print(
        "Bundle.total:           "
        f"{resultat.get('total')}"
    )
    print(
        "Antal Bundle entries:   "
        f"{len(entries)}"
    )
    print(
        "Antal ProcedureRequest: "
        f"{len(ydelser)}"
    )
    print("=" * 100 + "\n")

    pprint(
        resultat,
        width=180,
        sort_dicts=False,
    )

    print(
        "\nTesten er kun læsende. "
        "Der udføres ingen POST eller PUT."
    )


if __name__ == "__main__":
    main()

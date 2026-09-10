import os
from pprint import pprint

from q_cura_api.functionality.borger_ydelser import (
    borger_ydelser_hent,
)


def main():
    """
    Tester borger_ydelser_hent mod Cura.

    Output:
        Printer resultatet som almindelige Python-dictionaries og lister.
        Funktionen gemmer ikke noget på disk.
    """

    # Mulighed 1: Skriv borgerens Cura-ID direkte her.
    borger_id = "SKRIV_BORGER_ID_HER"

    # Mulighed 2: Hent borgerens Cura-ID fra .env.
    # Hvis BORGER_ID findes i .env, overskriver det værdien ovenfor.
    borger_id = os.getenv("BORGER_ID", borger_id).strip()

    if not borger_id or borger_id == "SKRIV_BORGER_ID_HER":
        raise ValueError(
            "Skriv borgerens Cura-ID i testfilen eller angiv BORGER_ID i .env"
        )

    resultat = borger_ydelser_hent(
        borger_id=borger_id,
        raw=False,
    )

    print("\n" + "=" * 80)
    print("RESULTAT FRA BORGER_YDELSER_HENT")
    print("=" * 80)
    print(f"Borger-ID: {resultat['borger_id']}")
    print(f"Antal ydelser: {resultat['antal_ydelser']}")
    print(f"Ydelser fundet: {resultat['found']}")
    print("=" * 80 + "\n")

    pprint(
        resultat,
        width=140,
        sort_dicts=False,
    )


if __name__ == "__main__":
    main()

import os
from pprint import pprint

from q_cura_api.functionality.borger_ydelser import (
    borger_ydelser_hent,
)


def _print_ydelser_struktureret(resultat: dict):
    """
    Printer ydelserne i en enkel og læsevenlig struktur.

    Output:
        Én overskuelig tekstblok pr. ydelse med de kendte felter
        fra Blue Prism.

        Funktionen returnerer ikke data og ændrer ikke resultatet.
    """

    ydelser = resultat.get("ydelser", [])

    print("\n" + "=" * 100)
    print("STRUKTURERET OVERSIGT OVER YDELSER")
    print("=" * 100)

    if not ydelser:
        print("Borgeren har ingen ydelser.")
        print("=" * 100)
        return

    for nummer, ydelse in enumerate(
        ydelser,
        start=1,
    ):
        print(f"\nYDELSE {nummer} AF {len(ydelser)}")
        print("-" * 100)

        print(f"ID:                       {ydelse.get('id', '')}")
        print(f"Ydelsesnavn:              {ydelse.get('ydelsesnavn', '')}")
        print(f"Ydelseskode:              {ydelse.get('ydelseskode', '')}")
        print(f"Sagstype:                 {ydelse.get('sagstype', '')}")
        print(f"Paragraf:                 {ydelse.get('paragraf', '')}")
        print(f"Status:                   {ydelse.get('status', '')}")
        print(f"Startdato:                {ydelse.get('startdato', '')}")
        print(f"Slutdato:                 {ydelse.get('slutdato', '')}")
        print(f"Borger-ID:                {ydelse.get('borger_id', '')}")
        print(f"Organisations-ID:         {ydelse.get('organization_id', '')}")
        print(f"Takst:                    {ydelse.get('takst', '')}")
        print(f"Takstenhed:               {ydelse.get('takstenhed', '')}")
        print(f"Oprettet dato:            {ydelse.get('oprettet_dato', '')}")
        print(f"Oprettet af:              {ydelse.get('oprettet_af', '')}")

        # Hjælpemiddeloplysninger vises kun, hvis mindst ét felt
        # indeholder en værdi.
        hmi_felter = [
            ydelse.get("hmi_status"),
            ydelse.get("hmi_nummer"),
            ydelse.get("hmi_loebenummer"),
            ydelse.get("hmi_navn"),
            ydelse.get("hmi_product_number"),
            ydelse.get("iso_group"),
            ydelse.get("iso_group_beskrivelse"),
            ydelse.get("leveringsdato"),
        ]

        if any(hmi_felter):
            print("\nHJÆLPEMIDDELOPLYSNINGER")
            print(f"HMI-status:               {ydelse.get('hmi_status', '')}")
            print(f"HMI-nummer:               {ydelse.get('hmi_nummer', '')}")
            print(f"HMI-løbenummer:           {ydelse.get('hmi_loebenummer', '')}")
            print(f"HMI-navn:                 {ydelse.get('hmi_navn', '')}")
            print(
                f"HMI-produktnummer:        "
                f"{ydelse.get('hmi_product_number', '')}"
            )
            print(f"ISO-gruppe:               {ydelse.get('iso_group', '')}")
            print(
                f"ISO-gruppebeskrivelse:    "
                f"{ydelse.get('iso_group_beskrivelse', '')}"
            )
            print(f"Leveringsdato:            {ydelse.get('leveringsdato', '')}")

    print("\n" + "=" * 100)


def main():
    """
    Tester borger_ydelser_hent mod Cura.

    Output:
        1. En læsevenlig oversigt inspireret af Blue Prism.
        2. Hele resultatet som almindelige Python-dictionaries og lister.

    Funktionen gemmer ikke noget på disk.
    """

    # Mulighed 1:
    # Skriv borgerens Cura-ID direkte her.
    borger_id = "SKRIV_BORGER_ID_HER"

    # Mulighed 2:
    # Hvis BORGER_ID findes i .env, bruges denne værdi i stedet.
    borger_id = os.getenv(
        "BORGER_ID",
        borger_id,
    ).strip()

    if not borger_id or borger_id == "SKRIV_BORGER_ID_HER":
        raise ValueError(
            "Skriv borgerens Cura-ID i testfilen "
            "eller angiv BORGER_ID i .env"
        )

    resultat = borger_ydelser_hent(
        borger_id=borger_id,
        raw=False,
    )

    # --------------------------------------------------------
    # OVERORDNET RESULTAT
    # --------------------------------------------------------
    print("\n" + "=" * 100)
    print("RESULTAT FRA BORGER_YDELSER_HENT")
    print("=" * 100)
    print(f"Borger-ID:       {resultat.get('borger_id', '')}")
    print(f"Ydelser fundet:  {resultat.get('found', False)}")
    print(f"Antal ydelser:   {resultat.get('antal_ydelser', 0)}")
    print("=" * 100)

    # --------------------------------------------------------
    # LÆSEVENLIG BLUE PRISM-LIGNENDE OVERSIGT
    # --------------------------------------------------------
    _print_ydelser_struktureret(resultat)

    # --------------------------------------------------------
    # HELE RESULTATET
    # --------------------------------------------------------
    print("\n" + "=" * 100)
    print("HELE RESULTATET INKLUSIVE RAW_RESOURCE")
    print("=" * 100 + "\n")

    pprint(
        resultat,
        width=140,
        sort_dicts=False,
    )


if __name__ == "__main__":
    main()
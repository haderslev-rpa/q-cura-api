from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA"

BORGER_ID = (
    "0a8a6458-695b-4c43-ba4f-6b8705600c74"
)

TASK_PROFILE = (
    "http://curafhir.dk/p/"
    "CuraSimpleTask"
)

COUNT = 1000


# ------------------------------------------------------------
# BYG ENDPOINT
# ------------------------------------------------------------

def build_endpoint() -> str:
    """
    Bygger opslaget efter CuraSimpleTask-opgaver for borgeren.

    Endpointet bliver:

        Basic
        ?_profile=http://curafhir.dk/p/CuraSimpleTask
        &for=Patient/<borger-id>
        &_count=1000

    Output:
        Det færdige endpoint som tekst.
    """
    return (
        "Basic?"
        + urlencode(
            [
                (
                    "_profile",
                    TASK_PROFILE,
                ),
                (
                    "for",
                    f"Patient/{BORGER_ID}",
                ),
                (
                    "_count",
                    str(COUNT),
                ),
            ],
            doseq=True,
        )
    )


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main():
    """
    Henter alle returnerede CuraSimpleTask-opgaver
    for én borger.

    Testen:

        - udfører kun GET
        - bruger ingen datobegrænsning
        - udskriver hele CURAs rå Bundle
        - normaliserer ikke resultatet
        - ændrer ingen ressourcer
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    endpoint = build_endpoint()

    print()
    print("=" * 100)
    print("RAW OPGAVER FOR BORGER")
    print("=" * 100)
    print(f"Miljø:    {CURA_CREDENTIAL}")
    print(f"Borger:   {BORGER_ID}")
    print(f"Profil:   {TASK_PROFILE}")
    print(f"Maksimum: {COUNT}")
    print(f"Endpoint: {endpoint}")
    print()

    raw_result = get(
        endpoint,
        raw=True,
    )

    pprint(
        raw_result,
        width=200,
        sort_dicts=False,
    )

    print()
    print("=" * 100)
    print("TESTEN ER FÆRDIG")
    print("=" * 100)
    print(
        "Der blev kun udført GET-kald. "
        "Ingen opgaver blev ændret."
    )


if __name__ == "__main__":
    main()
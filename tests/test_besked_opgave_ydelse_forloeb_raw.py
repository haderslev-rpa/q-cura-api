from pprint import pprint

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA"

YDELSE_ID = (
    "9ebcc39c-4fe7-491e-8dd7-b2df19c3a2ba" #
)

FORLOEB_ID = (
    "4c63d090-4bb9-48f8-bdce-3c637126c7fb" #
)

BESKED_ID = (
    "de4cc915-353e-4011-995a-5e1c069502c4" # "4fa45748-e748-4573-a7af-887289819b24"
)

OPGAVE_ID = (
    "3fec685d-9ce8-45a8-b980-9c64737be9da" #
)

BORGER_ID = (
    "b8fd9b01-5d85-4794-b1a7-5cd3c8e27a03" #
)


# ------------------------------------------------------------
# HJÆLPEFUNKTION TIL UDSKRIFT
# ------------------------------------------------------------

def print_raw_resource(
    title: str,
    endpoint: str,
):
    """
    Henter og udskriver én rå FHIR-resource.

    Output:
        Funktionen returnerer ressourcen præcis, som den
        modtages fra CURA.

        Funktionen normaliserer, filtrerer eller ændrer
        ikke data.
    """
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(f"Endpoint: {endpoint}")
    print()

    resource = get(
        endpoint,
        raw=True,
    )

    pprint(
        resource,
        width=200,
        sort_dicts=False,
    )

    return resource


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main():
    """
    Henter fire konkrete ressourcer direkte via deres id:

        ProcedureRequest
        CarePlan
        Communication
        Basic

    Testen udfører kun GET-kald.
    Der foretages ingen normalisering eller sammenligning.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    print()
    print("=" * 100)
    print("RAW DATA FRA CURA")
    print("=" * 100)
    print(f"Miljø:    {CURA_CREDENTIAL}")
    print(f"Borger:   {BORGER_ID}")
    print(f"Ydelse:   {YDELSE_ID}")
    print(f"Forløb:   {FORLOEB_ID}")
    print(f"Besked:   {BESKED_ID}")
    print(f"Opgave:   {OPGAVE_ID}")

    # --------------------------------------------------------
    # RAW YDELSE
    # --------------------------------------------------------

    print_raw_resource(
        title="RAW YDELSE - PROCEDUREREQUEST",
        endpoint=(
            f"ProcedureRequest/{YDELSE_ID}"
        ),
    )

    # --------------------------------------------------------
    # RAW FORLØB
    # --------------------------------------------------------

    print_raw_resource(
        title="RAW FORLØB - CAREPLAN",
        endpoint=(
            f"CarePlan/{FORLOEB_ID}"
        ),
    )

    # --------------------------------------------------------
    # RAW BESKED
    # --------------------------------------------------------

    print_raw_resource(
        title="RAW BESKED - COMMUNICATION",
        endpoint=(
            f"Communication/{BESKED_ID}"
        ),
    )

    # --------------------------------------------------------
    # RAW OPGAVE
    # --------------------------------------------------------

    print_raw_resource(
        title="RAW OPGAVE - BASIC",
        endpoint=(
            f"Basic/{OPGAVE_ID}"
        ),
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
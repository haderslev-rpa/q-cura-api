from pprint import pprint

from q_cura_api.api_client import (
    set_cura_credential,
)
from q_cura_api.functionality.kommunikation import (
    get_communications_in_period,
)


def main():
    """
    Henter genoptræningsplaner i en periode.

    Resultatet printes præcis, som funktionen returnerer det.

    Bemærk:
        Resultatet kan være stort, fordi hver Communication
        indeholder både:
            - content_strings
            - raw_resource
    """
    set_cura_credential(
        "API_CURA"
    )

    result = get_communications_in_period(
        received_from=(
            "2026-10-07T11:00:00+02:00"
        ),
        received_to=(
            "2026-10-07T23:59:59+02:00"
        ),
        message_type=(
            "rehabilitation_plan"
        ),
        raw=False,
    )

    print("")
    print("=" * 100)
    print("RESULTAT PRÆCIS SOM FUNKTIONEN RETURNERER DET")
    print("=" * 100)

    pprint(
        result,
        width=180,
        sort_dicts=False,
    )


if __name__ == "__main__":
    main()
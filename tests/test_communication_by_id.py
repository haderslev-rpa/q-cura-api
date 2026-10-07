from __future__ import annotations

from copy import deepcopy
from pprint import pprint

from q_cura_api.api_client import (
    set_cura_credential,
)
from q_cura_api.functionality.kommunikation import (
    get_communication_by_id,
)


COMMUNICATION_ID = (
    "de4cc915-353e-4011-"
    "995a-5e1c069502c4"
)

CONTENT_PREVIEW_LENGTH = 50


def _shorten_content_strings_for_print(
    value,
):
    """
    Laver en kopi til testudskrift.

    Kun felter med navnet content_strings eller
    contentString forkortes.

    API-funktionens oprindelige resultat ændres ikke.

    Det betyder:
        result indeholder stadig hele teksten.

        printable_result indeholder kun de første
        50 tegn til udskrift i terminalen.
    """
    if isinstance(value, dict):
        printable = {}

        for key, child_value in value.items():
            if (
                key == "content_strings"
                and isinstance(
                    child_value,
                    list,
                )
            ):
                printable[key] = [
                    str(
                        content_string
                    )[
                        :CONTENT_PREVIEW_LENGTH
                    ]
                    for content_string
                    in child_value
                ]

            elif key == "contentString":
                printable[key] = str(
                    child_value
                )[
                    :CONTENT_PREVIEW_LENGTH
                ]

            else:
                printable[key] = (
                    _shorten_content_strings_for_print(
                        child_value
                    )
                )

        return printable

    if isinstance(value, list):
        return [
            _shorten_content_strings_for_print(
                item
            )
            for item in value
        ]

    return value


def main():
    """
    Henter én Communication via id.

    Funktionen returnerer hele resultatet.

    Kun testens udskrift forkorter:
        - content_strings
        - contentString

    til de første 50 tegn.
    """
    set_cura_credential(
        "API_CURA"
    )

    result = get_communication_by_id(
        COMMUNICATION_ID,
        raw=False,
    )

    # Lav en separat kopi til print.
    #
    # deepcopy sikrer, at result ikke ændres.
    printable_result = (
        _shorten_content_strings_for_print(
            deepcopy(result)
        )
    )

    print("")
    print("=" * 100)
    print(
        "RESULTAT FRA "
        "GET_COMMUNICATION_BY_ID"
    )
    print("=" * 100)
    print(
        "Bemærk: Kun testudskriften forkorter "
        "content_strings til 50 tegn."
    )

    pprint(
        printable_result,
        width=180,
        sort_dicts=False,
    )


if __name__ == "__main__":
    main()
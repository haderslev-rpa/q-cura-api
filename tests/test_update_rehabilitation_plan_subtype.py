from pprint import pprint

from q_cura_api.api_client import (
    set_cura_credential,
)
from q_cura_api.functionality.kommunikation import (
    update_rehabilitation_plan_subtype,
)


COMMUNICATION_ID = (
    "de4cc915-353e-4011-"
    "995a-5e1c069502c4"
)


def main():
    """
    Tester opdateringen som dry run.

    Der sendes ingen PUT til CURA.

    Resultatet printes præcis, som funktionen returnerer det.
    """
    set_cura_credential(
        "API_CURA"
    )

    result = (
        update_rehabilitation_plan_subtype(
            communication_id=(
                COMMUNICATION_ID
            ),
            # ADVANCED vises som
            # "Avanceret niveau" i CURA UI.
            subtype_code="ADVANCED",
            # BASIC vises som
            # "Basalt niveau" i CURA UI.
            expected_current_subtype=(
                "BASIC"
            ),
            dry_run=True,
            raw=False,
        )
    )

    print("")
    print("=" * 100)
    print("DRY RUN-RESULTAT")
    print("=" * 100)

    pprint(
        result,
        width=180,
        sort_dicts=False,
    )


if __name__ == "__main__":
    main()
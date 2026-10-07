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

# Ekstra sikkerhed.
#
# Testen foretager kun en rigtig PUT, hvis denne værdi
# ændres manuelt til True.
RUN_REAL_PUT = False


def main():
    """
    Udfører en rigtig opdatering og verificerer resultatet.

    Forløb:
        1. Hent Communication.
        2. Kontrollér nuværende subtype.
        3. Ændr BASIC til ADVANCED.
        4. Send hele ressourcen med PUT.
        5. Hent ressourcen igen.
        6. Kontrollér at den gemte subtype er ADVANCED.
    """
    if RUN_REAL_PUT is not True:
        raise RuntimeError(
            "Testen er stoppet med vilje. "
            "Sæt RUN_REAL_PUT = True, hvis du "
            "bevidst vil sende en PUT til CURA."
        )

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
            # PUT udføres kun, hvis den aktuelle
            # værdi stadig er BASIC.
            expected_current_subtype=(
                "BASIC"
            ),
            dry_run=False,
            raw=False,
        )
    )

    print("")
    print("=" * 100)
    print("RESULTAT FRA PUT OG KONTROL-GET")
    print("=" * 100)

    pprint(
        result,
        width=180,
        sort_dicts=False,
    )

    if result.get("verified") is not True:
        raise RuntimeError(
            "Opdateringen blev ikke verificeret."
        )

    print("")
    print(
        "Opdateringen er verificeret. "
        "CURA returnerede den nye værdi ved "
        "det efterfølgende GET-kald."
    )


if __name__ == "__main__":
    main()
"""
TEST AF OPRETTELSE AF REHABILITATIONPLANMAPPING
================================================

Første kørsel skal bruge UDFOER_OPRETTELSE=False. Så udføres kun GET-kald,
og request body vises. Når id'er, profiler, borgerreferencer og request body er
kontrolleret, kan UDFOER_OPRETTELSE ændres til True.

Ved True udføres ét POST Basic og derefter et læsende kontrol-GET.
"""

from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.plan_mapping_opret import (
    opret_rehabilitation_plan_mapping,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

# Brug API_CURA_TEST til testmiljø eller API_CURA til live.
CURA_CREDENTIAL = "API_CURA"

# Alle id'er angives uden resourceType-prefix.
BORGER_ID = "39dde427-b1fc-42b3-9e85-fccf727ee3bf"#"b8fd9b01-5d85-4794-b1a7-5cd3c8e27a03" # 
COMMUNICATION_ID = "1115526a-6419-40ef-9380-95555142cbe1" #"de4cc915-353e-4011-995a-5e1c069502c4" #
CARE_PLAN_ID = "8517030a-84d4-45ec-8481-87a9c5b3cc5f" #"4c63d090-4bb9-48f8-bdce-3c637126c7fb" #


# Udfyld kun hvis mapping-id'et allerede kendes.
EXISTING_MAPPING_ID = None

# False er sikker dry run. True udfører en rigtig oprettelse.
UDFOER_OPRETTELSE = False


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def valider_testdata() -> None:
    if CURA_CREDENTIAL not in {"API_CURA", "API_CURA_TEST"}:
        raise ValueError("CURA_CREDENTIAL skal være API_CURA eller API_CURA_TEST.")
    for field_name, value, forbidden_prefix in (
        ("BORGER_ID", BORGER_ID, "Patient/"),
        ("COMMUNICATION_ID", COMMUNICATION_ID, "Communication/"),
        ("CARE_PLAN_ID", CARE_PLAN_ID, "CarePlan/"),
    ):
        if not isinstance(value, str) or not value.strip() or value.startswith("INDSAET_"):
            raise ValueError(f"Udfyld {field_name} med det tekniske id.")
        if value.startswith(forbidden_prefix):
            raise ValueError(f"{field_name} skal angives uden {forbidden_prefix!r}.")
    if not isinstance(UDFOER_OPRETTELSE, bool):
        raise TypeError("UDFOER_OPRETTELSE skal være True eller False.")


def main() -> None:
    valider_testdata()
    set_cura_credential(CURA_CREDENTIAL)

    print()
    print("=" * 100)
    print("REHABILITATIONPLANMAPPING")
    print("=" * 100)
    print(f"Credential:    {CURA_CREDENTIAL}")
    print(f"Borger:        Patient/{BORGER_ID}")
    print(f"Plan:          Communication/{COMMUNICATION_ID}")
    print(f"Forløb:        CarePlan/{CARE_PLAN_ID}")
    print(f"Eksisterende:  {EXISTING_MAPPING_ID}")
    print(f"Opretter:      {UDFOER_OPRETTELSE}")

    resultat = opret_rehabilitation_plan_mapping(
        borger_id=BORGER_ID,
        communication_id=COMMUNICATION_ID,
        care_plan_id=CARE_PLAN_ID,
        is_active=True,
        dry_run=not UDFOER_OPRETTELSE,
        existing_mapping_id=EXISTING_MAPPING_ID,
        raw=UDFOER_OPRETTELSE,
    )

    print()
    print("RESULTAT")
    print("-" * 100)
    pprint(resultat, width=200, sort_dicts=False)

    if resultat.get("success") is not True:
        raise AssertionError("Resultatet har ikke success=True.")

    if resultat.get("already_exists") is True:
        print()
        print("TEST BESTÅET: Mappingen fandtes allerede. Ingen ny mapping blev oprettet.")
        return

    if not UDFOER_OPRETTELSE:
        if resultat.get("dry_run") is not True:
            raise AssertionError("Dry run-resultatet har ikke dry_run=True.")
        body = resultat.get("request_body")
        if not isinstance(body, dict):
            raise AssertionError("Dry run-resultatet mangler request_body.")
        print()
        print("DRY RUN BESTÅET: Ingen POST blev sendt til CURA.")
        print("Kontrollér request_body. Skift derefter UDFOER_OPRETTELSE til True.")
        return

    if resultat.get("created") is not True:
        raise AssertionError("Resultatet har ikke created=True.")
    if resultat.get("verified") is not True:
        raise AssertionError("Resultatet har ikke verified=True.")
    if resultat.get("plan_reference") != f"Communication/{COMMUNICATION_ID}":
        raise AssertionError("Den gemte planreference matcher ikke Communication-id'et.")
    if resultat.get("target_reference") != f"CarePlan/{CARE_PLAN_ID}":
        raise AssertionError("Den gemte målreference matcher ikke CarePlan-id'et.")
    if resultat.get("borger_reference") != f"Patient/{BORGER_ID}":
        raise AssertionError("Den gemte borgerreference matcher ikke Patient-id'et.")
    if resultat.get("is_active") is not True:
        raise AssertionError("Den gemte mapping er ikke aktiv.")

    print()
    print("TEST BESTÅET")
    print(f"Mapping-id:   {resultat.get('mapping_id')}")
    print(f"Mapping-ref.: {resultat.get('mapping_reference')}")
    print(f"Plan-ref.:    {resultat.get('plan_reference')}")
    print(f"Forløbsref.:  {resultat.get('target_reference')}")
    print(f"Borgerref.:   {resultat.get('borger_reference')}")
    print(f"Aktiv:        {resultat.get('is_active')}")


if __name__ == "__main__":
    main()

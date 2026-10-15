from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.opgaver import (
    get_task_by_id,
    update_task_managing_organization,
)

CURA_CREDENTIAL = "API_CURA"
OPGAVE_ID = "INDSAET_OPGAVE_ID"
NY_ORGANISATION_ID = "INDSAET_ORGANISATION_ID"


def main():
    if OPGAVE_ID.startswith("INDSAET_") or NY_ORGANISATION_ID.startswith("INDSAET_"):
        raise ValueError("Udfyld OPGAVE_ID og NY_ORGANISATION_ID")
    set_cura_credential(CURA_CREDENTIAL)
    print("FØR:")
    pprint(get_task_by_id(OPGAVE_ID, raw=False), sort_dicts=False)
    result = update_task_managing_organization(
        OPGAVE_ID, NY_ORGANISATION_ID, raw=False
    )
    print("EFTER:")
    pprint(result, sort_dicts=False)
    assert result["managing_organization_id"] == NY_ORGANISATION_ID
    print("TEST 1 BESTÅET")


if __name__ == "__main__":
    main()

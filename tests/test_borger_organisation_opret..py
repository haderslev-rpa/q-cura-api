from pprint import pprint
from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_soeg_cpr import get_borger_by_cpr
from q_cura_api.functionality.borger_organisation_opret import add_organization_to_citizen
from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

test_data_credential = Credential.get_credential("Q_CURA_API")

TEST_CPR = test_data_credential.data["cpr-nancy"]  # 👈 dine testdata

set_cura_credential("API_CURA_TEST")

TEST_ORG_ID = "2fcf1a74-a8d6-4923-bcd8-f1b35a27f819"  # 👈 DU sætter denne

print("\n🚀 TEST: OPRET ORGANISATION")

# --------------------------------------------------------
# Hent borger
# --------------------------------------------------------
borger = get_borger_by_cpr(TEST_CPR)

pprint(borger, width=120)

# --------------------------------------------------------
# Stop hvis borger ikke findes
# --------------------------------------------------------
if not borger["findes_borger_i_cura"]:
    print("\n❌ Borger ikke fundet – stopper test")
else:
    borger_id = borger["borger_id"]

    print("\n✅ Borger fundet:", borger_id)
    print("👉 Tilføjer organization:", TEST_ORG_ID)

    # ----------------------------------------------------
    # OPRET ORGANISATION
    # ----------------------------------------------------
    result = add_organization_to_citizen(
        borger_id,
        TEST_ORG_ID,
        raw=True
    )

    # ----------------------------------------------------
    # PRINT RESULT
    # ----------------------------------------------------
    import json
    print("\n--- API RESPONSE ---")
    print(json.dumps(result, indent=2))
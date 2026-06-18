from pprint import pprint
from q_cura_api.api_client import set_cura_credential
from q_cura_api.borger_soeg_cpr import get_borger_by_cpr
from q_cura_api.borger_organisation_update import delete_organization_from_citizen_by_org_id
from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

test_data_credential = Credential.get_credential("Q_CURA_API")

TEST_CPR = test_data_credential.data["cpr-nancy"]  # 👈 dine testdata
set_cura_credential("API_CURA_TEST")

TEST_ORGANIZATION_ID = "2fcf1a74-a8d6-4923-bcd8-f1b35a27f819"  # 👈 DU sætter denne

print("\n🚀 TEST: DELETE ORGANISATION (VIA ORGANIZATION ID)")

# --------------------------------------------------------
# Hent borger
# --------------------------------------------------------
borger = get_borger_by_cpr(TEST_CPR)
pprint(borger, width=120)

if not borger["findes_borger_i_cura"]:
    print("\n❌ Borger ikke fundet – stopper test")
else:
    borger_id = borger["borger_id"]

    print("\n✅ Borger fundet:", borger_id)
    print("👉 Søger efter organization:", TEST_ORGANIZATION_ID)

    # ----------------------------------------------------
    # DELETE via organization_id
    # ----------------------------------------------------
    result = delete_organization_from_citizen_by_org_id(
        borger_id,
        TEST_ORGANIZATION_ID,
        raw=True
    )

    # ----------------------------------------------------
    # PRINT RESULT
    # ----------------------------------------------------
    import json
    print("\n--- API RESPONSE ---")
    print(json.dumps(result, indent=2))
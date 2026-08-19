from pprint import pprint
from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_soeg_cpr import get_borger_by_cpr
from q_cura_api.functionality.borger_organisation_hent import get_organizations_for_citizen
from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

test_data_credential = Credential.get_credential("Q_CURA_API")

TEST_CPR = test_data_credential.data["cpr1"]  # 👈 dine testdata
set_cura_credential("API_CURA")

print("\n🚀 TEST: HENT RAW ORGANISATIONER (INGEN FILTER)")

# --------------------------------------------------------
# Hent borger
# --------------------------------------------------------
borger = get_borger_by_cpr(TEST_CPR)
pprint(borger, width=120)

if not borger["findes_borger_i_cura"]:
    print("\n❌ Borger ikke fundet")
else:
    borger_id = borger["borger_id"]

    print("\n✅ Borger ID:", borger_id)

    # ----------------------------------------------------
    # ✅ HENT KUN RAW DATA (ingen filter)
    # ----------------------------------------------------
    orgs = get_organizations_for_citizen(borger_id, raw=True)

    # ----------------------------------------------------
    # ✅ PRINT ALT
    # ----------------------------------------------------
    pprint(orgs, width=120)
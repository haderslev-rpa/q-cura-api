from pprint import pprint
from q_cura_api.functionality.borger_soeg_cpr import get_borger_by_cpr
from q_cura_api.functionality.borger_kontaktpersoner_hent import get_contacts_for_citizen
from q_cura_api.api_client import set_cura_credential
from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

test_data_credential = Credential.get_credential("Q_CURA_API")

TEST_CPR = test_data_credential.data["cpr-nancy"]  # 👈 dine testdata



set_cura_credential("API_CURA")

# resten af din kode

USE_RAW = False  # 👈 styr her

print("\n🚀 TEST: HENT KONTAKTER")

borger = get_borger_by_cpr(TEST_CPR, raw=USE_RAW)
pprint(borger, width=120)

# --------------------------------------------------------
# ✅ Hvis RAW → stop her
# --------------------------------------------------------
if USE_RAW:
    print("\n✅ RAW mode – stopper efter borger output")
else:
    # ----------------------------------------------------
    # Normal flow
    # ----------------------------------------------------
    if not borger["findes_borger_i_cura"]:
        print("\n❌ Borger ikke fundet")
    else:
        borger_id = borger["borger_id"]

        contacts = get_contacts_for_citizen(borger_id)

        pprint(contacts, width=120)
from pprint import pprint
from q_cura_api.api_client import set_cura_credential
from q_cura_api.borger_soeg_cpr import get_borger_by_cpr
from q_cura_api.borger_interne_kontaktpersoner import get_internal_contacts_for_citizen
from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

test_data_credential = Credential.get_credential("Q_CURA_API")

TEST_CPR = test_data_credential.data["cpr1"]  # 👈 dine testdata

set_cura_credential("API_CURA_TEST")

borger = get_borger_by_cpr(TEST_CPR)

if borger["findes_borger_i_cura"]:
    result = get_internal_contacts_for_citizen(borger["borger_id"])
    pprint(result)

    

from pprint import pprint  # funktion (pæn udskrift)
from q_cura_api.api_client import set_cura_credential
from q_cura_api.borger_soeg_cpr import get_borger_by_cpr  # funktion (borger-søgning)
from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

test_data_credential = Credential.get_credential("Q_CURA_API")

TEST_CPR = test_data_credential.data["cpr-nancy"]  # 👈 dine testdata
set_cura_credential("API_CURA_TEST")


print("\n🚀 LOKAL TEST: SØG BORGER")

result = get_borger_by_cpr(TEST_CPR,raw=True)

pprint(result, width=120)
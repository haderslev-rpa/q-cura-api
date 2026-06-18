from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_soeg_cpr import get_borger_by_cpr
from q_cura_api.functionality.borger_interne_kontaktpersoner import add_internal_contact
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
    result = add_internal_contact(
        borger_id=borger["borger_id"],
        organization_id="9ead7d71-155c-4f2c-a564-c0fa2f88710f",
        practitioner_id="Dicheb",
        role_code="Forebyggelseskonsulent",
        role_display="Forebyggelseskonsulent",
        responsibility="PREVENTIVE_HOMECARE_RESPONSIBLE",
        primary=False
    )

    print(result)
from q_cura_api.api_client import set_cura_credential
from q_cura_api.borger_interne_kontaktpersoner import update_internal_contact_deleted

set_cura_credential("API_CURA_TEST")

TEST_RELATION_ID = "c2482810-1781-4817-85f4-252ae24e20d0"

result = update_internal_contact_deleted(TEST_RELATION_ID, True)

print(result)

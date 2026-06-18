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

TEST_CPR = test_data_credential.data["cpr-nancy"]  # 👈 dine testdata


set_cura_credential("API_CURA_TEST")

TEST_ORGANIZATION_ID = "2fcf1a74-a8d6-4923-bcd8-f1b35a27f819" # 👈 dit organization id
#2fcf1a74-a8d6-4923-bcd8-f1b35a27f819  Id på robotorganisation

print("\n🚀 TEST: HENT ORGANISATIONER + CHECK")

# --------------------------------------------------------
# Hent borger
# --------------------------------------------------------
borger = get_borger_by_cpr(TEST_CPR)
pprint(borger, width=120)

if not borger["findes_borger_i_cura"]:
    print("\n❌ Borger ikke fundet")
else:
    borger_id = borger["borger_id"]

    # ----------------------------------------------------
    # Hent organisationer
    # ----------------------------------------------------
    orgs = get_organizations_for_citizen(borger_id, raw=False)

    pprint(orgs, width=120)

    # ----------------------------------------------------
    # ✅ CHECK OM ORGANISATION FINDES
    # ----------------------------------------------------
    organization_found = False

    for org in orgs["organizationer"]:
        ref = org.get("organization_reference")

        if not ref:
            continue

        # "Organization/xxxx" -> "xxxx"
        org_id = ref.split("/")[-1]

        if org_id == TEST_ORGANIZATION_ID:
            organization_found = True
            break

    print("\n--- RESULTAT ---")
    print("Organisation findes på borger:", organization_found)

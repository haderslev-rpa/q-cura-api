from pprint import pprint  # pæn udskrift
from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.organisation_hent import get_organizations  # din funktion

set_cura_credential("API_CURA")

TEST_SØGNING = "Forebyggende Indsatser for Seniorer"  # 👈 dine testdata

print("\n🚀 TEST: SØG ORGANISATIONER")

# --------------------------------------------------------
# Kør søgning
# --------------------------------------------------------
result = get_organizations(TEST_SØGNING)

# --------------------------------------------------------
# Print resultat
# --------------------------------------------------------
pprint(result, width=120)
from pprint import pprint  # funktion (pæn udskrift)
from q_cura_api.borger_soeg_cpr import get_borger_by_cpr  # funktion (borger-søgning)

TEST_CPR = "????????"  # CPR – kun lokalt

print("\n🚀 LOKAL TEST: SØG BORGER")

result = get_borger_by_cpr(TEST_CPR)

pprint(result, width=120)
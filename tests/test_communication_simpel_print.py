from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.kommunikation import (
    get_communications_in_period,
)


def main():
    """Henter genoptræningsplaner i perioden og printer kun metadata.

    Beskedindhold og rå ressourcer hentes stadig af biblioteket,
    men medtages ikke i den dictionary, der udskrives.
    """
    set_cura_credential("API_CURA")

    result = get_communications_in_period(
        received_from="2026-10-07T11:00:00+02:00",
        received_to="2026-10-07T23:59:59+02:00",
        message_type="rehabilitation_plan",
        raw=False,
    )

    # Vælg udtrykkeligt de felter, der må vises.
    # raw_resource, content_strings og context medtages ikke.
    fields = (
        "communication_id",
        "resource_type",
        "profile",
        "borger_id",
        "received",
        "sent",
        "rehabilitation_type",
        "rehabilitation_subtype",
    )
    output = {
        "found": result["found"],
        "count": result["count"],
        "bundle_total": result.get("bundle_total"),
        "received_from": result["received_from"],
        "received_to": result["received_to"],
        "communications": [
            {field: communication.get(field) for field in fields}
            for communication in result["communications"]
        ],
    }

    print()
    print("=" * 100)
    print("GENOPTRÆNINGSPLANER UDEN BESKEDINDHOLD")
    print("=" * 100)
    pprint(output, width=180, sort_dicts=False)


if __name__ == "__main__":
    main()
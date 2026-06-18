from q_cura_api.api_client import post

# ------------------------------------------------------------
# OPRET ORGANISATION PÅ BORGER
# ------------------------------------------------------------
def add_organization_to_citizen(borger_id: str, organization_id: str, raw: bool = False):
    """
    Opretter en organisation på en borger.
    Returnerer relation_id hvis oprettet.
    """

    endpoint = "Basic"

    body = {
        "resourceType": "Basic",
        "meta": {
            "profile": [
                "http://curafhir.dk/p/CitizenCareProvider"
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://curafhir.dk/p",
                    "code": "CitizenCareProvider"
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{borger_id}"
        },
        "extension": [
            {
                "url": "http://curafhir.dk/x/CitizenCareProvider/organization",
                "valueReference": {
                    "reference": f"Organization/{organization_id}"
                }
            }
        ]
    }

    print("\n--- CREATE ORGANIZATION ---")
    print("Borger ID:", borger_id)
    print("Organization ID:", organization_id)
    print("Endpoint:", endpoint)
    print("Body:", body)
    print("Raw:", raw)

    response = post(endpoint, body, raw=True)

    if raw:
        return response

    # --------------------------------------------------------
    # ✅ HENT relation_id (robust)
    # --------------------------------------------------------
    relation_id = None

    # 1. ✅ Prøv Location header (primær)
    location = response.get("location")
    if location:
        relation_id = location.split("/")[-1]

    # 2. ✅ Fallback: hvis data indeholder id
    elif response.get("data") and isinstance(response["data"], dict):
        relation_id = response["data"].get("id")

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------
    result = {
        "success": True if relation_id or response.get("success") else False,
        "relation_id": relation_id,
        "status_code": response.get("status_code"),
    }

    return result

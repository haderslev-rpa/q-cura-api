
from q_cura_api.api_client import get

# ------------------------------------------------------------
# HENT ORGANISATIONER FOR BORGER
# ------------------------------------------------------------
def get_organizations_for_citizen(borger_id: str, raw: bool = False):
    """
    Henter alle AKTIVE organisationer for en borger.
    """

    endpoint = (
        "Basic"
        f"?subject={borger_id}"
        "&_profile=http://curafhir.dk/p/CitizenCareProvider"
    )

    print("\n--- GET ORGANIZATIONS ---")
    print("Borger ID:", borger_id)
    print("Endpoint:", endpoint)
    print("Raw:", raw)

    data = get(endpoint, raw=raw)

    if raw:
        return data

    result = {
        "found": False,
        "borger_id": borger_id,
        "organizationer": []
    }

    if isinstance(data, list) and len(data) > 0:
        result["found"] = True

    for item in data:

        resource = item.get("resource", {})
        extensions = resource.get("extension", [])

        org_ref = None
        is_deleted = False

        for ext in extensions:
            url = ext.get("url", "")

            if url.endswith("/organization"):
                org_ref = ext.get("valueReference", {}).get("reference")

            if url.endswith("/deleted"):
                is_deleted = ext.get("valueBoolean", False)

        relation_id = resource.get("id")

        organization_id = None
        if org_ref:
            organization_id = org_ref.split("/")[-1]

        result["organizationer"].append({
            "relation_id": relation_id,
            "organization_id": organization_id,
            "organization_reference": org_ref,
            "deleted": is_deleted
        })

        relation_id = resource.get("id")

        organization_id = None
        if org_ref:
            organization_id = org_ref.split("/")[-1]


        result["organizationer"].append({
            "relation_id": relation_id, # id på selve relationen (Basic ressourcen). Bruges til update/delete
            "organization_id": organization_id,
            "organization_reference": org_ref,
            "deleted": is_deleted                   # ✅ MEGET vigtig
        })


    return result
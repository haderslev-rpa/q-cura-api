from q_cura_api.api_client import get


# ------------------------------------------------------------
# HENT ORGANISATIONER FOR BORGER
# ------------------------------------------------------------
def get_organizations_for_citizen(
    borger_id: str,
    raw: bool = False,
    include_deleted: bool = False,
) -> dict:
    """
    Henter organisationer, som er tilknyttet en borger.

    Standard:
        include_deleted=False
        Kun aktive organisationer returneres.

    Hvis include_deleted=True:
        Både aktive og slettede organisationer returneres.

    Hvis raw=True:
        Det rå svar fra Cura returneres direkte.
        I raw-tilstand foretages der ikke filtrering på deleted.

    Eksempel på normalt output:
        {
            "found": True,
            "borger_id": "borger-id",
            "include_deleted": False,
            "organizationer": [
                {
                    "relation_id": "relation-id",
                    "organization_id": "organization-id",
                    "organization_reference": "Organization/organization-id",
                    "deleted": False,
                }
            ],
        }
    """

    endpoint = (
        "Basic"
        f"?subject={borger_id}"
        "&_profile=http://curafhir.dk/p/CitizenCareProvider"
    )

    print("\n--- GET ORGANIZATIONS FOR CITIZEN ---")
    print("Borger ID:", borger_id)
    print("Endpoint:", endpoint)
    print("Raw:", raw)
    print("Include deleted:", include_deleted)

    data = get(endpoint, raw=raw)

    # Ved raw=True returneres Cura-svaret helt uændret.
    if raw:
        return data

    result = {
        "found": False,
        "borger_id": borger_id,
        "include_deleted": include_deleted,
        "organizationer": [],
    }

    # Beskytter mod eksempelvis None eller et uventet dictionary-svar.
    if not isinstance(data, list):
        return result

    for item in data:
        if not isinstance(item, dict):
            continue

        resource = item.get("resource", {})

        if not isinstance(resource, dict):
            continue

        extensions = resource.get("extension", [])

        if not isinstance(extensions, list):
            extensions = []

        relation_id = resource.get("id")
        organization_reference = None
        is_deleted = False

        for extension in extensions:
            if not isinstance(extension, dict):
                continue

            extension_url = str(extension.get("url") or "")

            if extension_url.endswith("/organization"):
                organization_reference = (
                    extension.get("valueReference", {}).get("reference")
                )

            elif extension_url.endswith("/deleted"):
                # Kun den faktiske boolske værdi True tæller som slettet.
                is_deleted = extension.get("valueBoolean") is True

        # Slettede relationer udelades som standard.
        if is_deleted and not include_deleted:
            continue

        organization_id = None

        if organization_reference:
            organization_id = organization_reference.split("/")[-1]

        result["organizationer"].append(
            {
                "relation_id": relation_id,
                "organization_id": organization_id,
                "organization_reference": organization_reference,
                "deleted": is_deleted,
            }
        )

    # found betyder nu, at mindst én organisation bestod filtreringen.
    result["found"] = len(result["organizationer"]) > 0

    return result
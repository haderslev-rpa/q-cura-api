from q_cura_api.api_client import get, put


def delete_organization_from_citizen_by_org_id(
    borger_id: str,
    organization_id: str,
    raw: bool = False
):
    """
    Finder relation via organization_id,
    henter hele resource (raw),
    sætter deleted = true,
    og sender den tilbage med PUT.
    """

    print("\n--- DELETE VIA ORGANIZATION ID (FULL PUT) ---")
    print("Borger ID:", borger_id)
    print("Organization ID:", organization_id)

    # --------------------------------------------------------
    # 1. Hent alle relationer (parsed)
    # --------------------------------------------------------
    from q_cura_api.borger_organisation_hent import get_organizations_for_citizen
    orgs = get_organizations_for_citizen(borger_id)

    if not orgs["found"]:
        return {
            "success": False,
            "error": "Ingen organisationer fundet på borger"
        }

    # --------------------------------------------------------
    # 2. Find relation_id
    # --------------------------------------------------------
    relation_id = None

    for org in orgs["organizationer"]:
        if org.get("organization_id") == organization_id:
            relation_id = org.get("relation_id")
            break

    if not relation_id:
        return {
            "success": False,
            "organization_found": False,
            "message": "Organisation findes ikke på borger"
        }

    # --------------------------------------------------------
    # ✅ 3. HENT HELE RESOURCE (RAW)
    # --------------------------------------------------------
    resource = get(f"Basic/{relation_id}", raw=True)

    # --------------------------------------------------------
    # ✅ 4. ÆNDR deleted extension
    # --------------------------------------------------------
    extensions = resource.get("extension", [])

    deleted_found = False

    for ext in extensions:
        if ext.get("url", "").endswith("/deleted"):
            ext["valueBoolean"] = True
            deleted_found = True
            break

    # hvis den IKKE findes → opret den
    if not deleted_found:
        extensions.append({
            "url": "http://curafhir.dk/x/CitizenCareProvider/deleted",
            "valueBoolean": True
        })

    resource["extension"] = extensions

    # --------------------------------------------------------
    # ✅ 5. PUT HELE RESOURCE TILBAGE
    # --------------------------------------------------------
    response = put(f"Basic/{relation_id}", resource, raw=True)

    if raw:
        return response

    return {
        "success": response.get("success"),
        "relation_id": relation_id,
        "status_code": response.get("status_code"),
    }

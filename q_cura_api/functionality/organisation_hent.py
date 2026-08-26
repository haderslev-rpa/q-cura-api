from q_cura_api.api_client import get


# ------------------------------------------------------------
# HENT ORGANISATIONER (MED VALGFRI SØGNING)
# ------------------------------------------------------------
def get_organizations(search_name: str = None, raw: bool = False):
    """
    Henter organisationer fra Cura.

    Hvis search_name er None → henter alle.
    Hvis search_name er sat → søger + filtrerer i Python.
    """

    # --------------------------------------------------------
    # Build endpoint (API søgning)
    # --------------------------------------------------------
    if search_name:
        # encode specialtegn (samme som din Replace i BP)
        search_encoded = (
            search_name
            .replace("&", "%26")
            .replace("+", "%2B")
        )

        endpoint = (
            "Organization"
            f"?name={search_encoded}"
            "&_profile=http://curafhir.dk/p/CuraOrganization"
        )
    else:
        endpoint = (
            "Organization"
            "?_profile=http://curafhir.dk/p/CuraOrganization"
        )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------
    #print("\n--- GET ORGANIZATIONS (SEARCH) ---")
    #print("Search:", search_name)
    #print("Endpoint:", endpoint)
    #print("Raw:", raw)

    data = get(endpoint, raw=raw)

    if raw:
        return data

    # --------------------------------------------------------
    # Standard output
    # --------------------------------------------------------
    result = {
        "found": False,
        "count": 0,
        "organizationer": []
    }

    if isinstance(data, list) and len(data) > 0:
        result["found"] = True

        for item in data:
            resource = item.get("resource", {})

            org_id = resource.get("id")

            # navn kan ligge her (FHIR standard)
            name = resource.get("name")

            # ------------------------------------------------
            # Ekstra Python filtrering (din idé 👍)
            # ------------------------------------------------
            if search_name:
                if not name:
                    continue

                # case-insensitive "contains"
                if search_name.lower() not in name.lower():
                    continue

            result["organizationer"].append({
                "organization_id": org_id,
                "name": name
            })

    result["count"] = len(result["organizationer"])

    return result
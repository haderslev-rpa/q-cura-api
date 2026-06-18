from q_cura_api.api_client import get  # funktion (GET-kald)


# ------------------------------------------------------------
# GET BORGER VIA CPR
# ------------------------------------------------------------
def get_borger_by_cpr(cpr: str, raw: bool = False):
    """
    Henter borger i CURA via CPR.
    Hvis raw=True → returnerer hele FHIR response.
    """

    # --------------------------------------------------------
    # Fjern bindestreg
    # --------------------------------------------------------
    cpr = cpr.replace("-", "")

    endpoint = (
        "Patient"
        f"?identifier={cpr}"
        "&_profile=http://curafhir.dk/p/CuraCitizen"
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------
    print("\n--- BUILD BORGER REQUEST ---")
    print("CPR efter replace:", cpr)
    print("Endpoint:", endpoint)
    print("Raw:", raw)

    data = get(endpoint, raw=raw)  # ✅ vigtigt

    # --------------------------------------------------------
    # ✅ Returnér RAW hvis ønsket
    # --------------------------------------------------------
    if raw:
        return data

    # --------------------------------------------------------
    # Standard output
    # --------------------------------------------------------
    result = {
        "findes_borger_i_cura": False,
        "CPR": cpr,
        "borger_id": None,
    }

    # --------------------------------------------------------
    # Udtræk borger_id hvis fundet
    # --------------------------------------------------------
    if isinstance(data, list) and len(data) > 0:
        resource = data[0].get("resource", {})
        borger_id = resource.get("id")

        if borger_id:
            result["findes_borger_i_cura"] = True
            result["borger_id"] = borger_id

    return result

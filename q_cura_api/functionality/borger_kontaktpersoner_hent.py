from q_cura_api.api_client import get


# ------------------------------------------------------------
# HENT KONTAKTER FOR BORGER
# ------------------------------------------------------------
def get_contacts_for_citizen(borger_id: str, raw: bool = False):
    """
    Henter alle kontaktpersoner for en borger.
    """

    endpoint = f"Patient/{borger_id}"

    print("\n--- GET CONTACTS ---")
    print("Borger ID:", borger_id)
    print("Endpoint:", endpoint)
    print("Raw:", raw)

    data = get(endpoint, raw=True)  # ✅ altid raw

    if raw:
        return data

    result = {
        "found": False,
        "borger_id": borger_id,
        "contacts": []
    }

    # --------------------------------------------------------
    # contacts ligger direkte på Patient
    # --------------------------------------------------------
    contacts = data.get("contact", [])

    if isinstance(contacts, list) and len(contacts) > 0:
        result["found"] = True

        for contact in contacts:

            contact_id = contact.get("id")

            # navn
            name = None
            if contact.get("name"):
                name = contact["name"].get("text")

            # telefon (første phone)
            phone = None
            telecom = contact.get("telecom", [])
            for t in telecom:
                if t.get("system") == "phone":
                    phone = t.get("value")
                    break

            # relation / type (fra extension)
            relation = None
            extensions = contact.get("extension", [])

            for ext in extensions:
                url = ext.get("url", "")

                if url.endswith("/externalContactAssociation") or url.endswith("/otherContactAssociation"):
                    coding = ext.get("valueCodeableConcept", {}).get("coding", [])
                    if coding:
                        relation = coding[0].get("display")

            result["contacts"].append({
                "contact_id": contact_id,     # ✅ bruges til update
                "name": name,
                "phone": phone,
                "relation": relation
            })

    return result
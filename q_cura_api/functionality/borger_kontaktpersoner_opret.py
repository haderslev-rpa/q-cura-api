from q_cura_api.api_client import get, put
import uuid
import json
import copy


# ------------------------------------------------------------
# SAFE ADD CONTACT (med debug + breakpoint)
# ------------------------------------------------------------
def add_contact_to_citizen_safe(
    borger_id: str,
    name: str,
    phone: str = None,
    relation: str = None
):
    """
    Tilføjer kontakt med fuld debug og breakpoint.
    """

    #print("\n--- SAFE CREATE CONTACT ---")

    # --------------------------------------------------------
    # 1. Hent original resource
    # --------------------------------------------------------
    original = get(f"Patient/{borger_id}", raw=True)

    # lav deep copy så vi ikke ødelægger original
    updated = copy.deepcopy(original)

    # --------------------------------------------------------
    # 2. Byg ny contact
    # --------------------------------------------------------
    contact_id = str(uuid.uuid4())

    new_contact = {
        "id": contact_id,
        "name": {
            "text": name
        }
    }

    if phone:
        new_contact["telecom"] = [
            {
                "system": "phone",
                "value": phone,
                "use": "work",
                "rank": 1
            }
        ]

    if relation:
        new_contact["extension"] = [
            {
                "url": "http://curafhir.dk/x/Contact/externalContactAssociation",
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "display": relation
                        }
                    ]
                }
            }
        ]

    # --------------------------------------------------------
    # 3. Tilføj contact
    # --------------------------------------------------------
    contacts = updated.get("contact", [])
    contacts.append(new_contact)
    updated["contact"] = contacts

    # --------------------------------------------------------
    # ✅ 4. DEBUG OUTPUT (MEGET VIGTIGT)
    # --------------------------------------------------------
    #print("\n--- ORIGINAL (FØR) ---")
    #print(json.dumps(original.get("contact", []), indent=2))

    #print("\n--- UPDATED (EFTER) ---")
    #print(json.dumps(updated.get("contact", []), indent=2))

    #print("\n✅ CHECK:")
    #print(f"- Antal før: {len(original.get('contact', []))}")
    #print(f"- Antal efter: {len(updated.get('contact', []))}")
    #print(f"- Ny contact_id: {contact_id}")

    # --------------------------------------------------------
    # ✅ BREAKPOINT (STOP HER)
    # --------------------------------------------------------
    input("\n🔴 Tryk ENTER for at fortsætte med PUT...")

    # --------------------------------------------------------
    # 5. PUT tilbage
    # --------------------------------------------------------
    response = put(f"Patient/{borger_id}", updated, raw=True)

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------
    return {
        "success": response.get("success"),
        "contact_id": contact_id,
        "status_code": response.get("status_code"),
    }
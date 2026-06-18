from q_cura_api.api_client import get, post, put

# ------------------------------------------------------------
# HENT INTERNAL CONTACTS
# ------------------------------------------------------------
def get_internal_contacts_for_citizen(borger_id: str, raw: bool = False):
    endpoint = (
        "Basic"
        f"?subject={borger_id}"
        "&_profile=http://curafhir.dk/p/CitizenInternalContact"
    )

    data = get(endpoint, raw=raw)

    if raw:
        return data

    result = {
        "found": False,
        "borger_id": borger_id,
        "internal_contacts": []
    }

    if isinstance(data, list) and data:
        result["found"] = True

        for item in data:
            resource = item.get("resource", {})
            extensions = resource.get("extension", [])

            contact = {
                "relation_id": resource.get("id"),
                "organization_id": None,
                "practitioner_id": None,
                "role_code": None,
                "role_display": None,
                "role_system": None,
                "responsibility": None,
                "primary": None,
                "deleted": None
            }

            for ext in extensions:
                url = ext.get("url", "")

                if url.endswith("/organization"):
                    ref = ext.get("valueReference", {}).get("reference")
                    if ref:
                        contact["organization_id"] = ref.split("/")[-1]

                elif url.endswith("/practitioner"):
                    ref = ext.get("valueReference", {}).get("reference")
                    if ref:
                        contact["practitioner_id"] = ref.split("/")[-1]

                elif url.endswith("/role"):
                    coding = ext.get("valueCodeableConcept", {}).get("coding", [])
                    if coding:
                        contact["role_code"] = coding[0].get("code")
                        contact["role_display"] = coding[0].get("display")
                        contact["role_system"] = coding[0].get("system")

                elif url.endswith("/responsibility"):
                    contact["responsibility"] = ext.get("valueCode")

                elif url.endswith("/primaryContact"):
                    contact["primary"] = ext.get("valueBoolean")

                elif url.endswith("/deleted"):
                    contact["deleted"] = ext.get("valueBoolean")

            result["internal_contacts"].append(contact)

    return result

# ------------------------------------------------------------
# OPRET INTERNAL CONTACT
# ------------------------------------------------------------
def add_internal_contact(
    borger_id: str,
    organization_id: str,
    practitioner_id: str,
    role_code: str,
    role_display: str,
    responsibility: str = None,
    primary: bool = False,
    raw: bool = False
):
    endpoint = "Basic"

    extensions = [
        {
            "url": "http://curafhir.dk/x/CitizenInternalContact/organization",
            "valueReference": {"reference": f"Organization/{organization_id}"}
        },
        {
            "url": "http://curafhir.dk/x/CitizenInternalContact/role",
            "valueCodeableConcept": {
                "coding": [{
                    "system": "http://curafhir.dk/cs/PractitionerRole",
                    "code": role_code,
                    "display": role_display
                }]
            }
        },
        {
            "url": "http://curafhir.dk/x/CitizenInternalContact/practitioner",
            "valueReference": {"reference": f"Practitioner/{practitioner_id}"}
        },
        {
            "url": "http://curafhir.dk/x/CitizenInternalContact/primaryContact",
            "valueBoolean": primary
        },
        {
            "url": "http://curafhir.dk/x/CitizenInternalContact/deleted",
            "valueBoolean": False
        }
    ]

    if responsibility:
        extensions.append({
            "url": "http://curafhir.dk/x/CitizenInternalContact/responsibility",
            "valueCode": responsibility
        })

    body = {
        "resourceType": "Basic",
        "meta": {
            "profile": ["http://curafhir.dk/p/CitizenInternalContact"]
        },
        "code": {
            "coding": [{
                "system": "http://curafhir.dk/p",
                "code": "CitizenInternalContact"
            }]
        },
        "subject": {
            "reference": f"Patient/{borger_id}"
        },
        "extension": extensions
    }

    response = post(endpoint, body, raw=True)

    if raw:
        return response

    relation_id = None
    location = response.get("location")
    if location:
        relation_id = location.split("/")[-1]

    return {
        "success": True if relation_id else False,
        "relation_id": relation_id,
        "status_code": response.get("status_code")
    }

# ------------------------------------------------------------
# UPDATE DELETE FLAG
# ------------------------------------------------------------
def update_internal_contact_deleted(
    relation_id: str,
    deleted: bool = True,
    raw: bool = False
):
    resource = get(f"Basic/{relation_id}", raw=True)

    for ext in resource.get("extension", []):
        if ext.get("url", "").endswith("/deleted"):
            ext["valueBoolean"] = deleted

    response = put(f"Basic/{relation_id}", resource, raw=True)

    if raw:
        return response

    return {
        "success": response.get("success"),
        "relation_id": relation_id,
        "deleted": deleted,
        "status_code": response.get("status_code")
    }
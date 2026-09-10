from q_cura_api.api_client import get


# ------------------------------------------------------------
# FASTE CURA-URL'ER
# ------------------------------------------------------------
PROFILE = "http://curafhir.dk/p/CuraGrantedProcedureRequest"

EXTENSION_PERIOD = "http://curafhir.dk/x/CuraGrantedProcedureRequest/period"
EXTENSION_CASE_TYPE = "http://curafhir.dk/x/CuraGrantedProcedureRequest/caseType"
EXTENSION_LEGAL_PARAGRAPH = (
    "http://curafhir.dk/x/CuraGrantedProcedureRequest/legalParagraph"
)
EXTENSION_RATE = "http://curafhir.dk/x/CuraGrantedProcedureRequest/rate"
EXTENSION_RATE_UNIT = "http://curafhir.dk/x/CuraGrantedProcedureRequest/rateUnit"
EXTENSION_AID = "http://curafhir.dk/x/CuraGrantedProcedureRequest/aid"


# ------------------------------------------------------------
# INTERNE HJÆLPEFUNKTIONER
# ------------------------------------------------------------
def _find_extension(extensions: list, extension_url: str) -> dict:
    """
    Finder en Cura-extension ud fra dens fulde URL.

    Output:
        Extension som dictionary, hvis den findes.
        Tom dictionary, hvis den ikke findes.
    """

    if not isinstance(extensions, list):
        return {}

    for extension in extensions:
        if not isinstance(extension, dict):
            continue

        if extension.get("url") == extension_url:
            return extension

    return {}


def _find_extension_by_url_end(data, url_end: str) -> dict:
    """
    Søger rekursivt i dictionaries og lister efter en extension.

    Output:
        Første extension, hvis URL slutter med url_end.
        Tom dictionary, hvis den ikke findes.
    """

    if isinstance(data, dict):
        url = str(data.get("url") or "")

        if url.endswith(url_end):
            return data

        for value in data.values():
            found = _find_extension_by_url_end(value, url_end)

            if found:
                return found

    elif isinstance(data, list):
        for value in data:
            found = _find_extension_by_url_end(value, url_end)

            if found:
                return found

    return {}


def _get_reference_id(reference_data) -> str:
    """
    Henter ID fra en FHIR-reference.

    Eksempler:
        "Patient/123" bliver til "123".
        {"reference": "Organization/456"} bliver til "456".

    Output:
        ID som tekst eller tom tekst.
    """

    reference = ""

    if isinstance(reference_data, str):
        reference = reference_data

    elif isinstance(reference_data, dict):
        reference = str(reference_data.get("reference") or "")

    elif isinstance(reference_data, list):
        for item in reference_data:
            if not isinstance(item, dict):
                continue

            reference = str(item.get("reference") or "")

            if reference:
                break

    if not reference:
        return ""

    return reference.split("/")[-1]


def _get_first_coding_value(code_data: dict, field_name: str):
    """
    Henter en værdi fra det første element i code.coding.

    Output:
        Værdien fra eksempelvis display eller code.
        Tom tekst, hvis værdien ikke findes.
    """

    if not isinstance(code_data, dict):
        return ""

    coding = code_data.get("coding", [])

    if not isinstance(coding, list):
        return ""

    for coding_item in coding:
        if not isinstance(coding_item, dict):
            continue

        value = coding_item.get(field_name)

        if value is not None:
            return value

    return ""


def _get_meta_data(meta: dict) -> dict:
    """
    Henter kendte oplysninger fra ydelsens meta-data.

    Output:
        Dictionary med oprettet_dato og oprettet_af.
    """

    if not isinstance(meta, dict):
        return {
            "oprettet_dato": "",
            "oprettet_af": "",
        }

    created_extension = _find_extension_by_url_end(meta, "/timestamp")
    user_extension = _find_extension_by_url_end(meta, "/user")

    oprettet_dato = (
        created_extension.get("valueInstant")
        or meta.get("lastUpdated")
        or ""
    )

    oprettet_af = _get_reference_id(
        user_extension.get("valueReference", {})
    )

    return {
        "oprettet_dato": oprettet_dato,
        "oprettet_af": oprettet_af,
    }


def _get_aid_data(extensions: list) -> dict:
    """
    Henter kendte hjælpemiddeloplysninger fra aid-extension.

    Output:
        Dictionary med HMI-oplysninger.
        Felterne er tomme, hvis ydelsen ikke er et hjælpemiddel.
    """

    result = {
        "hmi_status": "",
        "hmi_nummer": "",
        "hmi_loebenummer": "",
        "hmi_navn": "",
        "hmi_product_number": "",
        "iso_group": "",
        "iso_group_beskrivelse": "",
        "leveringsdato": "",
    }

    aid_extension = _find_extension(extensions, EXTENSION_AID)

    if not aid_extension:
        return result

    aid_extensions = aid_extension.get("extension", [])

    if not isinstance(aid_extensions, list):
        return result

    for extension in aid_extensions:
        if not isinstance(extension, dict):
            continue

        url = str(extension.get("url") or "")

        if url.endswith("/status"):
            result["hmi_status"] = extension.get("valueCode", "")

        elif url.endswith("/hmiNumber"):
            result["hmi_nummer"] = extension.get("valueString", "")

        elif url.endswith("/entityIdentifierDisplay"):
            result["hmi_loebenummer"] = extension.get("valueString", "")

        elif url.endswith("/hmiName"):
            result["hmi_navn"] = extension.get("valueString", "")

        elif url.endswith("/hmiProductNumber"):
            result["hmi_product_number"] = extension.get("valueInteger", "")

        elif url.endswith("/isoGroupDescription"):
            result["iso_group_beskrivelse"] = extension.get("valueString", "")

        elif url.endswith("/isoGroup"):
            result["iso_group"] = extension.get("valueString", "")

        elif url.endswith("/deliveryDate"):
            result["leveringsdato"] = extension.get("valueDate", "")

    return result


def _normaliser_ydelse(resource: dict) -> dict:
    """
    Omdanner én ProcedureRequest til en læsevenlig dictionary.

    Output:
        Dictionary med kendte felter fra Blue Prism samt hele den
        oprindelige Cura-resource i raw_resource.
    """

    extensions = resource.get("extension", [])

    if not isinstance(extensions, list):
        extensions = []

    period_extension = _find_extension(extensions, EXTENSION_PERIOD)
    period = period_extension.get("valuePeriod", {})

    if not isinstance(period, dict):
        period = {}

    case_type_extension = _find_extension(extensions, EXTENSION_CASE_TYPE)
    paragraph_extension = _find_extension(
        extensions,
        EXTENSION_LEGAL_PARAGRAPH,
    )
    rate_extension = _find_extension(extensions, EXTENSION_RATE)
    rate_unit_extension = _find_extension(extensions, EXTENSION_RATE_UNIT)
    meta_data = _get_meta_data(resource.get("meta", {}))

    ydelse = {
        "id": resource.get("id", ""),
        "ydelsesnavn": _get_first_coding_value(
            resource.get("code", {}),
            "display",
        ),
        "ydelseskode": _get_first_coding_value(
            resource.get("code", {}),
            "code",
        ),
        "sagstype": case_type_extension.get("valueString", ""),
        "paragraf": paragraph_extension.get("valueString", ""),
        "startdato": period.get("start", ""),
        "slutdato": period.get("end", ""),
        "status": resource.get("status", ""),
        "organization_id": _get_reference_id(resource.get("performer")),
        "takst": rate_extension.get("valueDecimal", ""),
        "takstenhed": rate_unit_extension.get("valueCode", ""),
        "oprettet_dato": meta_data.get("oprettet_dato", ""),
        "oprettet_af": meta_data.get("oprettet_af", ""),
        "borger_id": _get_reference_id(resource.get("subject")),

        # Hele den originale ProcedureRequest fra Cura bevares her.
        # Intet bliver gemt på disk.
        "raw_resource": resource,
    }

    ydelse.update(_get_aid_data(extensions))

    return ydelse


# ------------------------------------------------------------
# HENT YDELSER FOR BORGER
# ------------------------------------------------------------
def borger_ydelser_hent(
    borger_id: str,
    raw: bool = False,
):
    """
    Henter alle returnerede ydelser for én borger i Cura.

    Input:
        borger_id:
            Borgerens Cura-ID, ikke CPR-nummeret.

        raw=False:
            Returnerer en opryddet dictionary med en liste af ydelser.
            Hver ydelse indeholder også hele den originale Cura-resource
            i feltet raw_resource.

        raw=True:
            Returnerer API-klientens rå svar uden bearbejdning.

    Output ved raw=False:
        {
            "found": True,
            "borger_id": "123",
            "antal_ydelser": 1,
            "ydelser": [
                {
                    "id": "ydelse-id",
                    "ydelsesnavn": "Ydelsesnavn",
                    "status": "active",
                    "startdato": "2026-01-01",
                    "slutdato": "",
                    "raw_resource": {...},
                    ...
                }
            ]
        }

    Funktionen gemmer ikke filer eller JSON.
    Outputtet består af almindelige Python-dictionaries og lister.
    """

    borger_id = str(borger_id or "").strip()

    if not borger_id:
        raise ValueError("borger_id skal være udfyldt")

    endpoint = (
        "ProcedureRequest"
        f"?subject={borger_id}"
        f"&_profile={PROFILE}"
        "&_sort=orderedOn"
    )

    data = get(endpoint, raw=raw)

    if raw:
        return data

    result = {
        "found": False,
        "borger_id": borger_id,
        "antal_ydelser": 0,
        "ydelser": [],
    }

    if not isinstance(data, list):
        return result

    for item in data:
        if not isinstance(item, dict):
            continue

        # api_client.get() returnerer normalt Bundle.entry-listen.
        # Hvert element har derfor typisk et resource-felt.
        resource = item.get("resource", item)

        if not isinstance(resource, dict):
            continue

        resource_type = resource.get("resourceType")

        if resource_type not in (None, "ProcedureRequest"):
            continue

        result["ydelser"].append(_normaliser_ydelse(resource))

    # ISO-datoer kan sorteres som almindelig tekst.
    result["ydelser"].sort(
        key=lambda ydelse: str(ydelse.get("startdato") or "")
    )

    result["antal_ydelser"] = len(result["ydelser"])
    result["found"] = result["antal_ydelser"] > 0

    return result

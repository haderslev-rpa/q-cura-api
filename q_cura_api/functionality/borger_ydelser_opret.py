"""
OPRET YDELSE PÅ ET §140-FORLØB I CURA
======================================

Modulet opretter én CuraGrantedProcedureRequest med ét POST-kald.
Den offentlige funktion er opret_ydelse().

Inputtet ydelsesnavn er UI-navnet. YDELSESOVERSAETTER oversætter navnet til:
1. en fælles JSON-skabelon og 2. den variant, der indsættes i ServiceVariant.

De understøttede UI-navne er:
- Opstartssamtale §140 Ortopædisk §140
- Opstartssamtale §140 Medicinsk §140
- Opstartssamtale §140 Neurologisk §140
- Opstartssamtale §140 Psykiatrisk §140
- Opstartssamtale §140 Kræft §140

Alle fem bruger skabelonen opstartssamtale_140.json. Forskellen er kun varianten.
Nye ydelser kan tilføjes i YDELSESOVERSAETTER og eventuelt med en ny skabelon.

Denne implementering svarer til UI-handlingen "Gem og bestil alt":
status sendes som requested i det ene POST-kald. Feltet previousOrderedVersions
sendes ikke. Efter POST udføres kun et læsende GET for at verificere ydelsen.

Leverandør og opfølgningsorganisation kan angives som id eller præcist navn.
Ved navn bruges get_organizations() og præcis ét aktivt, eksakt match kræves.
Opfølgning er valgfri, men dato og organisation skal enten begge angives eller
begge være None.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from q_cura_api.api_client import get, post
from q_cura_api.functionality.organisation_hent import get_organizations

PROFILE = "http://curafhir.dk/p/CuraGrantedProcedureRequest"
EXT_SERVICE_VARIANT = "http://curafhir.dk/x/ServiceVariant"
EXT_PERIOD = "http://curafhir.dk/x/CuraGrantedProcedureRequest/period"
EXT_PATHWAY = "http://curafhir.dk/x/CuraGrantedProcedureRequest/pathway"
EXT_FOLLOW_UP_DATE = "http://curafhir.dk/x/CuraGrantedProcedureRequest/followUpDate"
EXT_FOLLOW_UP_ORG = "http://curafhir.dk/x/CuraGrantedProcedureRequest/responsibleFollowupOrganization"

SKABELON_MAPPE = Path(__file__).resolve().parent.parent / "skabeloner"

YDELSESOVERSAETTER = {
    "Opstartssamtale §140 Ortopædisk §140": {
        "skabelon": "ydelse_opstartssamtale_140.json",
        "variant": "Ortopædisk",
    },
    "Opstartssamtale §140 Medicinsk §140": {
        "skabelon": "ydelse_opstartssamtale_140.json",
        "variant": "Medicinsk",
    },
    "Opstartssamtale §140 Neurologisk §140": {
        "skabelon": "ydelse_opstartssamtale_140.json",
        "variant": "Neurologisk",
    },
    "Opstartssamtale §140 Psykiatrisk §140": {
        "skabelon": "ydelse_opstartssamtale_140.json",
        "variant": "Psykiatrisk",
    },
    "Opstartssamtale §140 Kræft §140": {
        "skabelon": "ydelse_opstartssamtale_140.json",
        "variant": "Kræft",
    },
}


def _required_text(value: Any, field_name: str) -> str:
    if value is None or not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} skal være en ikke-tom tekst.")
    return value.strip()


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst eller None.")
    return value.strip() or None


def _iso(value: Any, field_name: str, optional: bool = False) -> str | None:
    value = _optional_text(value, field_name) if optional else _required_text(value, field_name)
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} skal være et gyldigt ISO-tidspunkt.") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} skal indeholde tidszone.")
    return value


def _extensions(resource: dict) -> list:
    value = resource.get("extension")
    if not isinstance(value, list):
        value = []
        resource["extension"] = value
    return value


def _find(resource: dict, url: str) -> dict | None:
    return next((e for e in _extensions(resource) if isinstance(e, dict) and e.get("url") == url), None)


def _require(resource: dict, url: str) -> dict:
    extension = _find(resource, url)
    if extension is None:
        raise ValueError(f"Skabelonen mangler extension: {url}")
    return extension


def _remove(resource: dict, url: str) -> None:
    resource["extension"] = [e for e in _extensions(resource) if not (isinstance(e, dict) and e.get("url") == url)]


def _set_optional_datetime(resource: dict, url: str, value: str | None) -> None:
    if value is None:
        _remove(resource, url)
        return
    extension = _find(resource, url)
    if extension is None:
        extension = {"url": url}
        _extensions(resource).append(extension)
    extension["valueDateTime"] = value


def _set_optional_reference(resource: dict, url: str, reference: str | None) -> None:
    if reference is None:
        _remove(resource, url)
        return
    extension = _find(resource, url)
    if extension is None:
        extension = {"url": url}
        _extensions(resource).append(extension)
    extension["valueReference"] = {"reference": reference}


def _normalise_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _resolve_organization(value: str | None, value_type: str, field_name: str) -> dict:
    value = _optional_text(value, field_name)
    if value is None:
        return {"id": None, "name": None}
    value_type = _required_text(value_type, f"{field_name}_type").lower()
    if value_type == "id":
        org_id = value.split("/", 1)[1] if value.startswith("Organization/") else value
        return {"id": _required_text(org_id, field_name), "name": None}
    if value_type != "navn":
        raise ValueError(f"{field_name}_type skal være 'id' eller 'navn'.")
    result = get_organizations(search_name=value, raw=False, include_inactive=False)
    organizations = result.get("organizationer", []) if isinstance(result, dict) else []
    matches = [o for o in organizations if isinstance(o, dict) and _normalise_name(str(o.get("name") or "")) == _normalise_name(value)]
    if len(matches) != 1:
        raise ValueError(f"Forventede ét aktivt præcist match for {field_name}={value!r}, men fandt {len(matches)}.")
    return {"id": _required_text(str(matches[0].get("organization_id") or ""), field_name), "name": str(matches[0].get("name") or "")}


def hent_tilgængelige_ydelsesnavne() -> list[str]:
    return list(YDELSESOVERSAETTER)


def _load_template(file_name: str) -> dict:
    path = SKABELON_MAPPE / file_name
    if not path.is_file():
        raise FileNotFoundError(f"Ydelsesskabelonen findes ikke: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("resourceType") != "ProcedureRequest":
        raise ValueError("Ydelsesskabelonen er ikke en ProcedureRequest.")
    return deepcopy(data)


def build_ydelse(
    ydelsesnavn: str,
    borger_id: str,
    forloeb_id: str,
    start_datetime: str,
    ordered_on_datetime: str,
    leverandoer: str,
    *,
    leverandoer_type: str = "id",
    opfoelgningsdato: str | None = None,
    opfoelgningsorganisation: str | None = None,
    opfoelgningsorganisation_type: str = "id",
) -> tuple[dict, dict]:
    ydelsesnavn = _required_text(ydelsesnavn, "ydelsesnavn")
    translation = YDELSESOVERSAETTER.get(ydelsesnavn)
    if translation is None:
        raise ValueError(f"Ukendt ydelsesnavn: {ydelsesnavn!r}. Tilladte værdier: {hent_tilgængelige_ydelsesnavne()}")
    supplier = _resolve_organization(leverandoer, leverandoer_type, "leverandoer")
    follow_up_date = _iso(opfoelgningsdato, "opfoelgningsdato", optional=True)
    follow_up_org = _resolve_organization(opfoelgningsorganisation, opfoelgningsorganisation_type, "opfoelgningsorganisation")
    if bool(follow_up_date) != bool(follow_up_org["id"]):
        raise ValueError("Opfølgning kræver både opfoelgningsdato og opfoelgningsorganisation.")
    body = _load_template(translation["skabelon"])
    body["subject"] = {"reference": f"Patient/{_required_text(borger_id, 'borger_id')}"}
    body["performer"] = {"reference": f"Organization/{supplier['id']}"}
    body["status"] = "requested"
    body["orderedOn"] = _iso(ordered_on_datetime, "ordered_on_datetime")
    _require(body, EXT_SERVICE_VARIANT)["valueCodeableConcept"] = {"text": translation["variant"]}
    _require(body, EXT_PERIOD)["valuePeriod"] = {"start": _iso(start_datetime, "start_datetime")}
    _require(body, EXT_PATHWAY)["valueReference"] = {"reference": f"CarePlan/{_required_text(forloeb_id, 'forloeb_id')}"}
    _set_optional_datetime(body, EXT_FOLLOW_UP_DATE, follow_up_date)
    _set_optional_reference(body, EXT_FOLLOW_UP_ORG, f"Organization/{follow_up_org['id']}" if follow_up_org["id"] else None)
    body.pop("id", None)
    meta = body.get("meta")
    if isinstance(meta, dict):
        for key in ("versionId", "lastUpdated", "extension"):
            meta.pop(key, None)
    # previousOrderedVersions må aldrig sendes.
    _remove(body, "http://curafhir.dk/x/CuraGrantedProcedureRequest/previousOrderedVersions")
    context = {"variant": translation["variant"], "leverandoer": supplier, "opfoelgningsorganisation": follow_up_org}
    return body, context


def _id_from_post(response: dict) -> tuple[str, str]:
    location = str(response.get("location") or response.get("content_location") or "").strip()
    clean = location.split("?", 1)[0].rstrip("/")
    resource_id = clean.split("/")[-3] if "/_history/" in clean else (clean.split("/")[-1] if clean else "")
    if not resource_id and isinstance(response.get("data"), dict):
        resource_id = str(response["data"].get("id") or "")
    return resource_id, location


def opret_ydelse(
    ydelsesnavn: str,
    borger_id: str,
    forloeb_id: str,
    start_datetime: str,
    ordered_on_datetime: str,
    leverandoer: str,
    *,
    leverandoer_type: str = "id",
    opfoelgningsdato: str | None = None,
    opfoelgningsorganisation: str | None = None,
    opfoelgningsorganisation_type: str = "id",
    raw: bool = False,
) -> dict:
    body, context = build_ydelse(
        ydelsesnavn, borger_id, forloeb_id, start_datetime, ordered_on_datetime, leverandoer,
        leverandoer_type=leverandoer_type,
        opfoelgningsdato=opfoelgningsdato,
        opfoelgningsorganisation=opfoelgningsorganisation,
        opfoelgningsorganisation_type=opfoelgningsorganisation_type,
    )
    response = post("ProcedureRequest", body, raw=True)
    ydelse_id, location = _id_from_post(response)
    if not ydelse_id:
        raise RuntimeError("Ydelsen blev muligvis oprettet, men POST-svaret indeholdt ikke et id. Kør ikke oprettelsen igen før GET-kontrol.")
    verified = get(f"ProcedureRequest/{ydelse_id}", raw=True)
    if not isinstance(verified, dict) or verified.get("resourceType") != "ProcedureRequest":
        raise RuntimeError("Kontrol-GET returnerede ikke en ProcedureRequest.")
    expected = {
        "subject": f"Patient/{borger_id}",
        "performer": f"Organization/{context['leverandoer']['id']}",
        "pathway": f"CarePlan/{forloeb_id}",
    }
    actual_subject = str((verified.get("subject") or {}).get("reference") or "")
    actual_performer = str((verified.get("performer") or {}).get("reference") or "")
    actual_pathway = str((_require(verified, EXT_PATHWAY).get("valueReference") or {}).get("reference") or "")
    if actual_subject != expected["subject"] or actual_performer != expected["performer"] or actual_pathway != expected["pathway"] or verified.get("status") != "requested":
        raise RuntimeError("Den oprettede ydelse bestod ikke kontrol af borger, leverandør, forløb og status.")
    result = {
        "success": True,
        "verified": True,
        "ydelsesnavn": ydelsesnavn,
        "variant": context["variant"],
        "ydelse_id": ydelse_id,
        "ydelse_reference": f"ProcedureRequest/{ydelse_id}",
        "forloeb_id": forloeb_id,
        "forloeb_reference": actual_pathway,
        "status": verified.get("status"),
        "leverandoer_id": context["leverandoer"]["id"],
        "leverandoer_navn": context["leverandoer"]["name"],
        "leverandoer_reference": actual_performer,
        "location": location,
        "raw_resource": verified,
    }
    if raw:
        result["request_body"] = body
        result["post_response"] = response
    return result

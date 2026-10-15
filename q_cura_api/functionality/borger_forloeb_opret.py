"""
OPRET FORLØB I CURA
===================

FORMÅL
------
Dette modul opretter et CarePlan-forløb i CURA ud fra en JSON-skabelon.
Den primære offentlige funktion er:

    opret_forloeb(...)

Funktionen understøtter to forskellige handlinger. Handlingen bestemmer den
status, som sendes i det ENE POST-kald til CURA:

1. handling="opret"
   - Bruges, når forløbet kun skal gemmes, men ikke bestilles/startes.
   - CarePlan sendes med status="proposed".
   - Dette svarer til et forløb, som endnu ikke er kørt gennem
     "Gem og bestil" i CURA.

2. handling="opret_og_bestil"
   - Bruges, når forløbet både skal oprettes og bestilles/startes med det samme.
   - CarePlan sendes med status="draft".
   - Hele sluttilstanden bygges før POST-kaldet.
   - Der foretages IKKE først POST og derefter PUT.

SKRIVENDE API-KALD
------------------
Hver kørsel af opret_forloeb() foretager præcis ét skrivende kald:

    POST CarePlan

Efter POST foretages ét læsende GET-kald til CarePlan/<id> for at kontrollere,
at CURA har gemt den forventede borger, status og leverandør. Kontrol-GET ændrer
ikke data i CURA.

FORLØBSTYPE OG SKABELON
-----------------------
Argumentet forloebstype vælger en registreret JSON-skabelon fra:

    q_cura_api/skabeloner/

Aktuelt eksempel:

    forloebstype="genoptraeningsforloeb_140"

Nye forløbstyper tilføjes ved at:

1. lægge en ny JSON-skabelon i q_cura_api/skabeloner,
2. registrere typen i FORLOEBS_SKABELONER,
3. teste typen særskilt i CURA-testmiljøet.

LEVERANDØR
----------
Leverandøren er valgfri og angives med argumenterne leverandoer og
leverandoer_type.

Ingen leverandør:

    leverandoer=None

Leverandør som teknisk Organization-id:

    leverandoer="564d6e04-0d56-41c4-b379-be7f67e4809f"
    leverandoer_type="id"

Hele referencen Organization/<id> accepteres også ved leverandoer_type="id".

Leverandør som præcist organisationsnavn:

    leverandoer="Det præcise navn i CURA"
    leverandoer_type="navn"

Ved leverandoer_type="navn" kaldes get_organizations() fra organisation_hent.py.
Kun aktive organisationer indgår. Funktionen kræver præcis ét eksakt navnematch.
Hvis ingen eller flere organisationer matcher, stoppes oprettelsen. Dette er en
sikkerhed mod at vælge en forkert leverandør.

OPFØLGNING
----------
Opfølgning er valgfri.

Uden opfølgning:

    opfoelgningsdato=None
    opfoelgningsorganisation_id=None

Med opfølgning skal begge værdier udfyldes. Det er ikke tilladt kun at angive
den ene værdi:

    opfoelgningsdato="2026-10-20T00:00:00+02:00"
    opfoelgningsorganisation_id="<Organization-id>"

DATOER
------
start_datetime, slut_datetime og opfoelgningsdato skal angives som ISO-dato/tid
med tidszone, eksempelvis:

    2026-10-15T00:00:00+02:00

EKSEMPEL: OPRET UDEN BESTILLING
------------------------------

    resultat = opret_forloeb(
        forloebstype="genoptraeningsforloeb_140",
        handling="opret",
        borger_id=borger_id,
        start_datetime="2026-10-15T00:00:00+02:00",
        henvist_fra="Henvisning fra sygehus",
        bemaerkning="Oprettet via API",
        leverandoer=None,
        opfoelgningsdato=None,
        opfoelgningsorganisation_id=None,
    )

Forventet gemt status:

    proposed

EKSEMPEL: OPRET OG BESTIL MED LEVERANDØRNAVN
--------------------------------------------

    resultat = opret_forloeb(
        forloebstype="genoptraeningsforloeb_140",
        handling="opret_og_bestil",
        borger_id=borger_id,
        start_datetime="2026-10-15T00:00:00+02:00",
        henvist_fra="Henvisning fra sygehus",
        bemaerkning="Oprettet og bestilt via API",
        leverandoer="Det præcise navn i CURA",
        leverandoer_type="navn",
        opfoelgningsdato=None,
        opfoelgningsorganisation_id=None,
    )

Forventet gemt status:

    draft

VIGTIGT FOR KALDENDE KODE OG AI
-------------------------------
- Brug ikke status som frit input. Vælg i stedet handling="opret" eller
  handling="opret_og_bestil".
- "opret" betyder status="proposed".
- "opret_og_bestil" betyder status="draft".
- Forsøg ikke at gennemføre "opret_og_bestil" med et ekstra PUT. Sluttilstanden
  skal sendes i det ene POST-kald.
- Brug leverandoer=None, når forløbet ikke skal have en leverandør.
- Brug leverandoer_type="navn" kun med det præcise navn fra CURA.
- Brug leverandoer_type="id", hvis navnet ikke er entydigt.
- Genkør ikke blindt oprettelsen efter en fejl efter POST. Et forløb kan være
  oprettet, selv om efterfølgende kontrol fejler. Undersøg først CURA med GET.
- Vælg CURA-miljø med set_cura_credential() før funktionen kaldes.

RETURNERET RESULTAT
-------------------
Ved succes returnerer opret_forloeb() en dictionary med blandt andet:

    success
    verified
    handling
    forloeb_id
    forloeb_reference
    borger_id
    borger_reference
    status
    leverandoer_organisation_id
    leverandoer_navn
    leverandoer_reference
    period
    post_status_code
    raw_resource

Hvis raw=True, medtages også request_body og post_response.
"""



from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from q_cura_api.api_client import get, post
from q_cura_api.functionality.organisation_hent import get_organizations


# ------------------------------------------------------------
# FASTE CURA-VÆRDIER
# ------------------------------------------------------------

CARE_PLAN_PROFILE = "http://curafhir.dk/p/CuraCarePlan"

EXTENSION_NAME = "http://curafhir.dk/x/CuraCarePlan/name"
EXTENSION_PARAGRAPH = "http://curafhir.dk/x/CuraCarePlan/paragraph"
EXTENSION_REFERRED_FROM = "http://curafhir.dk/x/CuraCarePlan/referredFrom"
EXTENSION_SUPPLIER = "http://curafhir.dk/x/CuraCarePlan/supplier"
EXTENSION_REMARK = "http://curafhir.dk/x/CuraCarePlan/remark"
EXTENSION_FOLLOW_UP_DATE = "http://curafhir.dk/x/CuraCarePlan/followUpDate"
EXTENSION_RESPONSIBLE_FOLLOWUP_ORGANIZATION = (
    "http://curafhir.dk/x/CuraCarePlan/responsibleFollowupOrganization"
)

STATUS_OPRET = "proposed"
STATUS_OPRET_OG_BESTIL = "draft"

HANDLING_OPRET = "opret"
HANDLING_OPRET_OG_BESTIL = "opret_og_bestil"

TILLADTE_HANDLINGER = {
    HANDLING_OPRET,
    HANDLING_OPRET_OG_BESTIL,
}

LEVERANDOER_TYPE_ID = "id"
LEVERANDOER_TYPE_NAVN = "navn"
TILLADTE_LEVERANDOER_TYPER = {
    LEVERANDOER_TYPE_ID,
    LEVERANDOER_TYPE_NAVN,
}

SKABELON_MAPPE = Path(__file__).resolve().parent.parent / "skabeloner"

# Nøglen er det input, som processen bruger.
# Filnavnet er JSON-skabelonen under q_cura_api/skabeloner.
FORLOEBS_SKABELONER = {
    "genoptraeningsforloeb_140": "genoptraeningsforloeb_140.json",
}


# ------------------------------------------------------------
# VALIDERING
# ------------------------------------------------------------


def _required_text(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} skal angives.")

    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst.")

    result = value.strip()

    if not result:
        raise ValueError(f"{field_name} må ikke være tom.")

    return result


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst eller None.")

    result = value.strip()
    return result or None


def _validate_iso_datetime(value: Any, field_name: str) -> str:
    validated = _required_text(value, field_name)

    try:
        parsed = datetime.fromisoformat(
            validated.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ValueError(
            f"{field_name} skal være et gyldigt ISO-tidspunkt."
        ) from error

    if parsed.tzinfo is None:
        raise ValueError(
            f"{field_name} skal indeholde tidszone, fx +01:00 eller +02:00."
        )

    return validated


def _validate_optional_iso_datetime(
    value: Any,
    field_name: str,
) -> str | None:
    optional_value = _optional_text(value, field_name)

    if optional_value is None:
        return None

    return _validate_iso_datetime(optional_value, field_name)


def _validate_handling(handling: Any) -> str:
    validated = _required_text(handling, "handling").lower()

    if validated not in TILLADTE_HANDLINGER:
        raise ValueError(
            "handling skal være 'opret' eller 'opret_og_bestil'."
        )

    return validated


def _normaliser_navn(value: str) -> str:
    """Gør et organisationsnavn sammenligneligt."""
    return " ".join(value.split()).casefold()


def _resolve_leverandoer(
    leverandoer: Any,
    leverandoer_type: Any,
) -> dict:
    """
    Finder leverandørens Organization-id.

    leverandoer=None eller tom tekst:
        Ingen leverandør. Der foretages intet organisationsopslag.

    leverandoer_type="id":
        leverandoer bruges direkte som teknisk Organization-id.

    leverandoer_type="navn":
        organisation_hent.get_organizations() bruges til opslag.
        Efter opslaget kræves præcis ét aktivt, eksakt navnematch.
    """
    validated_supplier = _optional_text(leverandoer, "leverandoer")

    if validated_supplier is None:
        return {
            "organization_id": None,
            "organization_name": None,
            "input_type": None,
            "input_value": None,
        }

    validated_type = _required_text(
        leverandoer_type,
        "leverandoer_type",
    ).lower()

    if validated_type not in TILLADTE_LEVERANDOER_TYPER:
        raise ValueError(
            "leverandoer_type skal være 'id' eller 'navn'."
        )

    if validated_type == LEVERANDOER_TYPE_ID:
        organization_id = validated_supplier

        if organization_id.startswith("Organization/"):
            organization_id = organization_id.split("/", 1)[1].strip()

        if not organization_id:
            raise ValueError("leverandoer indeholder ikke et Organization-id.")

        return {
            "organization_id": organization_id,
            "organization_name": None,
            "input_type": validated_type,
            "input_value": validated_supplier,
        }

    search_result = get_organizations(
        search_name=validated_supplier,
        raw=False,
        include_inactive=False,
    )

    if not isinstance(search_result, dict):
        raise RuntimeError(
            "Organisationsopslaget returnerede ikke en dictionary."
        )

    organizations = search_result.get("organizationer")

    if not isinstance(organizations, list):
        raise RuntimeError(
            "Organisationsopslaget mangler listen organizationer."
        )

    expected_name = _normaliser_navn(validated_supplier)
    exact_matches = []

    for organization in organizations:
        if not isinstance(organization, dict):
            continue

        organization_name = str(organization.get("name") or "").strip()
        organization_id = str(
            organization.get("organization_id") or ""
        ).strip()

        if not organization_name or not organization_id:
            continue

        if _normaliser_navn(organization_name) == expected_name:
            exact_matches.append(
                {
                    "organization_id": organization_id,
                    "organization_name": organization_name,
                }
            )

    if not exact_matches:
        raise ValueError(
            "Ingen aktiv organisation blev fundet med det præcise navn: "
            f"{validated_supplier!r}."
        )

    if len(exact_matches) > 1:
        matching_ids = [
            match["organization_id"]
            for match in exact_matches
        ]
        raise ValueError(
            "Flere aktive organisationer har det præcise navn "
            f"{validated_supplier!r}. Fundne id'er: {matching_ids}. "
            "Brug leverandoer_type='id' for at vælge entydigt."
        )

    match = exact_matches[0]

    return {
        "organization_id": match["organization_id"],
        "organization_name": match["organization_name"],
        "input_type": validated_type,
        "input_value": validated_supplier,
    }


# ------------------------------------------------------------
# EXTENSION-HJÆLPERE
# ------------------------------------------------------------


def _get_extensions(resource: dict) -> list:
    extensions = resource.get("extension")

    if not isinstance(extensions, list):
        extensions = []
        resource["extension"] = extensions

    return extensions


def _find_extension(resource: dict, extension_url: str) -> dict | None:
    for extension in _get_extensions(resource):
        if (
            isinstance(extension, dict)
            and extension.get("url") == extension_url
        ):
            return extension

    return None


def _require_extension(resource: dict, extension_url: str) -> dict:
    extension = _find_extension(resource, extension_url)

    if extension is None:
        raise ValueError(
            "Forløbsskabelonen mangler extension: "
            f"{extension_url}"
        )

    return extension


def _remove_extension(resource: dict, extension_url: str) -> None:
    resource["extension"] = [
        extension
        for extension in _get_extensions(resource)
        if not (
            isinstance(extension, dict)
            and extension.get("url") == extension_url
        )
    ]


def _set_optional_string_extension(
    resource: dict,
    extension_url: str,
    value: str | None,
) -> None:
    if value is None:
        _remove_extension(resource, extension_url)
        return

    extension = _find_extension(resource, extension_url)

    if extension is None:
        extension = {"url": extension_url}
        _get_extensions(resource).append(extension)

    extension["valueString"] = value


def _set_optional_datetime_extension(
    resource: dict,
    extension_url: str,
    value: str | None,
) -> None:
    if value is None:
        _remove_extension(resource, extension_url)
        return

    extension = _find_extension(resource, extension_url)

    if extension is None:
        extension = {"url": extension_url}
        _get_extensions(resource).append(extension)

    extension["valueDateTime"] = value


def _set_optional_reference_extension(
    resource: dict,
    extension_url: str,
    reference: str | None,
) -> None:
    if reference is None:
        _remove_extension(resource, extension_url)
        return

    extension = _find_extension(resource, extension_url)

    if extension is None:
        extension = {"url": extension_url}
        _get_extensions(resource).append(extension)

    extension["valueReference"] = {
        "reference": reference,
    }


def _get_extension_reference(resource: dict, extension_url: str) -> str:
    extension = _find_extension(resource, extension_url)

    if extension is None:
        return ""

    value_reference = extension.get("valueReference")

    if not isinstance(value_reference, dict):
        return ""

    return str(value_reference.get("reference") or "").strip()


# ------------------------------------------------------------
# SKABELONER
# ------------------------------------------------------------


def hent_tilgængelige_forloebstyper() -> list[str]:
    return sorted(FORLOEBS_SKABELONER)


def _validate_template(template: dict) -> None:
    if template.get("resourceType") != "CarePlan":
        raise ValueError("Forløbsskabelonen er ikke en CarePlan.")

    meta = template.get("meta")
    profiles = meta.get("profile") if isinstance(meta, dict) else []

    if not isinstance(profiles, list) or CARE_PLAN_PROFILE not in profiles:
        raise ValueError(
            "Forløbsskabelonen mangler CuraCarePlan-profilen."
        )

    _require_extension(template, EXTENSION_NAME)
    _require_extension(template, EXTENSION_PARAGRAPH)
    _require_extension(template, EXTENSION_REFERRED_FROM)
    _require_extension(template, EXTENSION_REMARK)


def hent_forloebsskabelon(forloebstype: str) -> dict:
    validated_type = _required_text(forloebstype, "forloebstype")
    filnavn = FORLOEBS_SKABELONER.get(validated_type)

    if filnavn is None:
        tilgængelige = ", ".join(hent_tilgængelige_forloebstyper())
        raise ValueError(
            f"Ukendt forløbstype: {validated_type}. "
            f"Tilgængelige typer: {tilgængelige}"
        )

    skabelonsti = SKABELON_MAPPE / filnavn

    if not skabelonsti.is_file():
        raise FileNotFoundError(
            f"Forløbsskabelonen findes ikke: {skabelonsti}"
        )

    json_text = skabelonsti.read_text(encoding="utf-8")

    if not json_text.strip():
        raise ValueError(f"Forløbsskabelonen er tom: {skabelonsti}")

    try:
        template = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Forløbsskabelonen indeholder ugyldig JSON. "
            f"Fil: {skabelonsti}. "
            f"Linje: {error.lineno}. "
            f"Kolonne: {error.colno}. "
            f"Fejl: {error.msg}"
        ) from error

    if not isinstance(template, dict):
        raise TypeError(
            "Forløbsskabelonen skal indeholde et JSON-objekt."
        )

    _validate_template(template)
    return deepcopy(template)


# ------------------------------------------------------------
# SERVERSTYREDE FELTER OG POST-SVAR
# ------------------------------------------------------------


def _clean_server_fields(resource: dict) -> None:
    resource.pop("id", None)
    resource.pop("identifier", None)
    resource.pop("implicitRules", None)

    meta = resource.get("meta")

    if not isinstance(meta, dict):
        return

    meta.pop("versionId", None)
    meta.pop("lastUpdated", None)
    meta.pop("extension", None)


def _extract_resource_id_from_location(location: str) -> str:
    clean_location = str(location or "").split("?", 1)[0].rstrip("/")

    if not clean_location:
        return ""

    location_parts = clean_location.split("/")

    if (
        len(location_parts) >= 3
        and location_parts[-2] == "_history"
    ):
        return location_parts[-3]

    return location_parts[-1]


def _extract_created_id(post_response: dict) -> tuple[str, str]:
    location = str(
        post_response.get("location")
        or post_response.get("content_location")
        or ""
    ).strip()

    resource_id = _extract_resource_id_from_location(location)

    if resource_id:
        return resource_id, location

    data = post_response.get("data")

    if isinstance(data, dict):
        resource_id = str(data.get("id") or "").strip()

    return resource_id, location


# ------------------------------------------------------------
# BYG FORLØB
# ------------------------------------------------------------


def build_forloeb(
    forloebstype: str,
    handling: str,
    borger_id: str,
    start_datetime: str,
    henvist_fra: str,
    bemaerkning: str,
    *,
    leverandoer: str | None = None,
    leverandoer_type: str = LEVERANDOER_TYPE_ID,
    opfoelgningsdato: str | None = None,
    opfoelgningsorganisation_id: str | None = None,
    slut_datetime: str | None = None,
) -> dict:
    """
    Bygger ét komplet CarePlan til ét POST-kald.

    handling="opret":
        status bliver proposed.

    handling="opret_og_bestil":
        status bliver draft.

    Leverandør og opfølgning er valgfrie. Leverandøren kan angives som id eller navn.
    """
    validated_handling = _validate_handling(handling)
    body = hent_forloebsskabelon(forloebstype)

    validated_borger_id = _required_text(borger_id, "borger_id")
    validated_start = _validate_iso_datetime(
        start_datetime,
        "start_datetime",
    )
    validated_henvist_fra = _required_text(
        henvist_fra,
        "henvist_fra",
    )
    validated_bemaerkning = _required_text(
        bemaerkning,
        "bemaerkning",
    )
    leverandoer_data = _resolve_leverandoer(
        leverandoer,
        leverandoer_type,
    )
    validated_supplier_id = leverandoer_data["organization_id"]
    validated_follow_up_date = _validate_optional_iso_datetime(
        opfoelgningsdato,
        "opfoelgningsdato",
    )
    validated_follow_up_org_id = _optional_text(
        opfoelgningsorganisation_id,
        "opfoelgningsorganisation_id",
    )
    validated_end = _validate_optional_iso_datetime(
        slut_datetime,
        "slut_datetime",
    )

    if bool(validated_follow_up_date) != bool(validated_follow_up_org_id):
        raise ValueError(
            "Opfølgning skal enten have både opfoelgningsdato og "
            "opfoelgningsorganisation_id eller ingen af delene."
        )

    body["subject"] = {
        "reference": f"Patient/{validated_borger_id}",
    }

    body["status"] = (
        STATUS_OPRET_OG_BESTIL
        if validated_handling == HANDLING_OPRET_OG_BESTIL
        else STATUS_OPRET
    )

    period = body.get("period")

    if not isinstance(period, dict):
        period = {}
        body["period"] = period

    period["start"] = validated_start

    if validated_end is None:
        period.pop("end", None)
    else:
        period["end"] = validated_end

    _require_extension(
        body,
        EXTENSION_REFERRED_FROM,
    )["valueString"] = validated_henvist_fra

    _require_extension(
        body,
        EXTENSION_REMARK,
    )["valueString"] = validated_bemaerkning

    supplier_reference = (
        f"Organization/{validated_supplier_id}"
        if validated_supplier_id
        else None
    )
    _set_optional_reference_extension(
        body,
        EXTENSION_SUPPLIER,
        supplier_reference,
    )

    _set_optional_datetime_extension(
        body,
        EXTENSION_FOLLOW_UP_DATE,
        validated_follow_up_date,
    )

    follow_up_org_reference = (
        f"Organization/{validated_follow_up_org_id}"
        if validated_follow_up_org_id
        else None
    )
    _set_optional_reference_extension(
        body,
        EXTENSION_RESPONSIBLE_FOLLOWUP_ORGANIZATION,
        follow_up_org_reference,
    )

    _clean_server_fields(body)
    return body


# ------------------------------------------------------------
# OPRET FORLØB MED PRÆCIS ÉT POST-KALD
# ------------------------------------------------------------


def opret_forloeb(
    forloebstype: str,
    handling: str,
    borger_id: str,
    start_datetime: str,
    henvist_fra: str,
    bemaerkning: str,
    *,
    leverandoer: str | None = None,
    leverandoer_type: str = LEVERANDOER_TYPE_ID,
    opfoelgningsdato: str | None = None,
    opfoelgningsorganisation_id: str | None = None,
    slut_datetime: str | None = None,
    raw: bool = False,
) -> dict:
    """
    Opretter et CarePlan med præcis ét POST-kald.

    handling="opret":
        POST-body sendes med status proposed.

    handling="opret_og_bestil":
        POST-body sendes med status draft.

    Leverandøren kan angives som id eller navn. Ved navn foretages et læsende organisationsopslag før POST.

    Der sendes aldrig et efterfølgende PUT.
    Efter POST udføres kun ét læsende GET for at verificere resultatet.
    """
    validated_handling = _validate_handling(handling)
    validated_borger_id = _required_text(borger_id, "borger_id")
    leverandoer_data = _resolve_leverandoer(
        leverandoer,
        leverandoer_type,
    )
    validated_supplier_id = leverandoer_data["organization_id"]

    body = build_forloeb(
        forloebstype=forloebstype,
        handling=validated_handling,
        borger_id=validated_borger_id,
        start_datetime=start_datetime,
        henvist_fra=henvist_fra,
        bemaerkning=bemaerkning,
        leverandoer=validated_supplier_id,
        leverandoer_type=LEVERANDOER_TYPE_ID,
        opfoelgningsdato=opfoelgningsdato,
        opfoelgningsorganisation_id=opfoelgningsorganisation_id,
        slut_datetime=slut_datetime,
    )

    post_response = post(
        "CarePlan",
        body,
        raw=True,
    )

    if not isinstance(post_response, dict):
        raise RuntimeError(
            "CURA returnerede ikke et forståeligt POST-resultat."
        )

    forloeb_id, location = _extract_created_id(post_response)

    if not forloeb_id:
        raise RuntimeError(
            "Forløbet blev muligvis oprettet, men CURA returnerede "
            "ikke et id i Location-headeren eller response body. "
            f"Statuskode: {post_response.get('status_code')}. "
            "Kør ikke oprettelsen igen, før forløbet er fundet med GET."
        )

    verified = get(
        f"CarePlan/{forloeb_id}",
        raw=True,
    )

    if not isinstance(verified, dict):
        raise RuntimeError(
            "CarePlan blev oprettet, men kontrol-GET returnerede "
            "ikke en dictionary."
        )

    if verified.get("resourceType") != "CarePlan":
        raise RuntimeError(
            "Kontrol-GET returnerede ikke en CarePlan."
        )

    if str(verified.get("id") or "").strip() != forloeb_id:
        raise RuntimeError(
            "Det hentede CarePlan-id matcher ikke id'et fra POST-kaldet."
        )

    expected_subject = f"Patient/{validated_borger_id}"
    subject = verified.get("subject")
    stored_subject = (
        str(subject.get("reference") or "").strip()
        if isinstance(subject, dict)
        else ""
    )

    if stored_subject != expected_subject:
        raise RuntimeError(
            "Det oprettede forløb peger ikke på den forventede borger. "
            f"Forventet: {expected_subject}. Fundet: {stored_subject}."
        )

    expected_status = (
        STATUS_OPRET_OG_BESTIL
        if validated_handling == HANDLING_OPRET_OG_BESTIL
        else STATUS_OPRET
    )
    stored_status = str(verified.get("status") or "").strip()

    if stored_status != expected_status:
        raise RuntimeError(
            "Det oprettede forløb har ikke den forventede status. "
            f"Forventet: {expected_status}. Fundet: {stored_status}."
        )

    expected_supplier_reference = (
        f"Organization/{validated_supplier_id}"
        if validated_supplier_id
        else ""
    )
    stored_supplier_reference = _get_extension_reference(
        verified,
        EXTENSION_SUPPLIER,
    )

    if stored_supplier_reference != expected_supplier_reference:
        raise RuntimeError(
            "Det oprettede forløbs leverandør matcher ikke input. "
            f"Forventet: {expected_supplier_reference or '<ingen>'}. "
            f"Fundet: {stored_supplier_reference or '<ingen>'}."
        )

    result = {
        "success": True,
        "verified": True,
        "forloebstype": forloebstype,
        "handling": validated_handling,
        "forloeb_id": forloeb_id,
        "forloeb_reference": f"CarePlan/{forloeb_id}",
        "borger_id": validated_borger_id,
        "borger_reference": stored_subject,
        "status": stored_status,
        "leverandoer_input": leverandoer_data["input_value"],
        "leverandoer_input_type": leverandoer_data["input_type"],
        "leverandoer_organisation_id": validated_supplier_id,
        "leverandoer_navn": leverandoer_data["organization_name"],
        "leverandoer_reference": stored_supplier_reference,
        "period": verified.get("period") or {},
        "post_status_code": post_response.get("status_code"),
        "location": location,
        "raw_resource": verified,
    }

    if raw:
        result["post_response"] = post_response
        result["request_body"] = body

    return result

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from urllib.parse import urlencode

from q_cura_api.api_client import get, put


# ------------------------------------------------------------
# KENDTE COMMUNICATION-PROFILER
# ------------------------------------------------------------
# message_type er et kort navn til processerne.
# profile kan altid bruges med en fuld CURA-profil-URL, så
# biblioteket ikke låses til de profiler, vi kender i dag.
MESSAGE_PROFILES = {
    "rehabilitation_plan": "http://curafhir.dk/p/CuraRehabilitationPlan",
    "care_communication": "http://curafhir.dk/p/MedcomCareCommunication",
    "digital_post_inbound": "http://curafhir.dk/p/DigitalPostInboundCommunication",
}

REHABILITATION_PLAN_PROFILE = (
    "http://curafhir.dk/p/CuraRehabilitationPlan"
)
REHABILITATION_TYPE_URL = (
    "http://curafhir.dk/x/CuraRehabilitationPlan/type"
)
REHABILITATION_SUBTYPE_URL = (
    "http://curafhir.dk/x/CuraRehabilitationPlan/subType"
)
REHABILITATION_DIAGNOSIS_URL = (
    "http://curafhir.dk/x/CuraRehabilitationPlan/diagnosis"
)

# UI-navne verificeret ud fra CURA-brugerfladen og faktiske resources:
# BASIC    = "Basalt niveau"
# ADVANCED = "Avanceret niveau"
REHABILITATION_SUBTYPE_UI_NAMES = {
    "BASIC": "Basalt niveau",
    "ADVANCED": "Avanceret niveau",
}


# ------------------------------------------------------------
# VALIDERING
# ------------------------------------------------------------
def _required_text(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} skal angives.")
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst.")
    validated = value.strip()
    if not validated:
        raise ValueError(f"{field_name} må ikke være tom.")
    return validated


def _validate_iso_datetime(value, field_name: str) -> str:
    validated = _required_text(value, field_name)
    parse_value = validated[:-1] + "+00:00" if validated.endswith(("Z", "z")) else validated
    try:
        datetime.fromisoformat(parse_value)
    except ValueError as error:
        raise ValueError(
            f"{field_name} skal være en ISO-dato eller ISO-dato/tid."
        ) from error
    return validated


def _resolve_profile(
    message_type: str | None,
    profile: str | None,
) -> str:
    if profile is not None:
        return _required_text(profile, "profile")

    validated_type = _required_text(message_type, "message_type")
    resolved = MESSAGE_PROFILES.get(validated_type)
    if not resolved:
        raise ValueError(
            f"Ukendt message_type: {validated_type!r}. "
            f"Tilladte værdier: {sorted(MESSAGE_PROFILES)}. "
            "Brug alternativt profile med en fuld profil-URL."
        )
    return resolved


# ------------------------------------------------------------
# GENERELLE FHIR-HJÆLPERE
# ------------------------------------------------------------
def _get_profiles(resource: dict) -> list:
    meta = resource.get("meta", {})
    if not isinstance(meta, dict):
        return []
    profiles = meta.get("profile", [])
    return profiles if isinstance(profiles, list) else []


def _get_reference(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("reference") or "").strip()
    if isinstance(value, list):
        for item in value:
            reference = _get_reference(item)
            if reference:
                return reference
    return ""


def _get_reference_id(value) -> str:
    reference = _get_reference(value)
    return reference.rstrip("/").split("/")[-1] if reference else ""


def _find_extension(resource: dict, extension_url: str) -> dict:
    extensions = resource.get("extension", [])
    if not isinstance(extensions, list):
        return {}
    for extension in extensions:
        if isinstance(extension, dict) and extension.get("url") == extension_url:
            return extension
    return {}


def _get_extension_value(resource: dict, extension_url: str):
    extension = _find_extension(resource, extension_url)
    if not extension:
        return ""
    for key, value in extension.items():
        if key.startswith("value"):
            return value
    nested = extension.get("extension")
    return nested if isinstance(nested, list) else ""


def _find_nested_values(value, url_ending: str) -> list:
    found = []
    if isinstance(value, dict):
        if str(value.get("url") or "").endswith(url_ending):
            for key, child in value.items():
                if key.startswith("value"):
                    found.append(child)
        for child in value.values():
            found.extend(_find_nested_values(child, url_ending))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_nested_values(child, url_ending))
    return found


def _get_diagnoses(resource: dict) -> list:
    diagnosis = _find_extension(resource, REHABILITATION_DIAGNOSIS_URL)
    if not diagnosis:
        return []

    codes = _find_nested_values(diagnosis, "/diagnosisCode")
    types = _find_nested_values(diagnosis, "/typeCode")
    texts = _find_nested_values(diagnosis, "/text")
    count = max(len(codes), len(types), len(texts), 0)

    return [
        {
            "code": codes[index] if index < len(codes) else "",
            "code_type": types[index] if index < len(types) else "",
            "text": texts[index] if index < len(texts) else "",
        }
        for index in range(count)
    ]


def _get_content_strings(resource: dict) -> list[str]:
    """Henter payload.contentString uden at ændre HTML-indholdet."""
    payload = resource.get("payload", [])
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    return [
        str(item.get("contentString"))
        for item in payload
        if isinstance(item, dict) and item.get("contentString") is not None
    ]


def _get_identifiers(resource: dict) -> list[dict]:
    identifiers = resource.get("identifier", [])
    if not isinstance(identifiers, list):
        return []
    return [
        {
            "system": str(item.get("system") or ""),
            "value": str(item.get("value") or ""),
        }
        for item in identifiers
        if isinstance(item, dict)
    ]


def _normalise_communication(
    resource: dict,
) -> dict:
    """
    Omdanner én Communication-resource til et fælles resultat.

    Funktionen fjerner ikke indhold fra CURA-responsen.

    Outputtet indeholder:
        - fælles felter, som findes på tværs af profiler
        - profilbestemte felter for CuraRehabilitationPlan
        - content_strings fra payload.contentString
        - hele den oprindelige ressource i raw_resource

    UI-sammenhæng for CuraRehabilitationPlan:

        rehabilitation_type:
            Extension:
                CuraRehabilitationPlan/type

            Eksempel:
                GENERALIZED

            Feltet beskriver genoptræningsplanens overordnede
            tekniske type.

        rehabilitation_subtype:
            Extension:
                CuraRehabilitationPlan/subType

            API-værdier:
                BASIC
                    Vises som "Basalt niveau" i CURA UI.

                ADVANCED
                    Vises som "Avanceret niveau" i CURA UI.

            UI-navnet returneres ikke som et særskilt felt.
            Funktionen returnerer kun API-værdien.

        diagnoses:
            Extension:
                CuraRehabilitationPlan/diagnosis

            Eksempel:
                {
                    "code": "DM531",
                    "code_type": "ICD10kode",
                    "text": "Cervikobrakialt syndrom",
                }

            Dette svarer i UI til:
                Cervikobrakialt syndrom (DM531)
    """
    if not isinstance(resource, dict):
        raise TypeError(
            "resource skal være en dictionary."
        )

    profiles = _get_profiles(
        resource
    )

    result = {
        "communication_id": str(
            resource.get("id")
            or ""
        ),
        "resource_type": str(
            resource.get("resourceType")
            or ""
        ),
        "profile": (
            profiles[0]
            if profiles
            else ""
        ),
        "profiles": profiles,
        "received": str(
            resource.get("received")
            or ""
        ),
        "sent": str(
            resource.get("sent")
            or ""
        ),
        "borger_reference": (
            _get_reference(
                resource.get("subject")
            )
        ),
        "borger_id": (
            _get_reference_id(
                resource.get("subject")
            )
        ),
        "sender_reference": (
            _get_reference(
                resource.get("sender")
            )
        ),
        "sender_id": (
            _get_reference_id(
                resource.get("sender")
            )
        ),
        "recipient": resource.get(
            "recipient",
            [],
        ),
        "identifiers": _get_identifiers(
            resource
        ),
        # Bevarer alle payload.contentString-værdier.
        # Indholdet kan være langt HTML.
        "content_strings": (
            _get_content_strings(
                resource
            )
        ),
        # Hele ressourcen bevares uændret.
        "raw_resource": resource,
    }

    if (
        REHABILITATION_PLAN_PROFILE
        in profiles
    ):
        subtype_code = str(
            _get_extension_value(
                resource,
                REHABILITATION_SUBTYPE_URL,
            )
            or ""
        ).strip().upper()

        result.update(
            {
                "rehabilitation_type": (
                    _get_extension_value(
                        resource,
                        REHABILITATION_TYPE_URL,
                    )
                ),
                # Kun API-koden returneres.
                #
                # BASIC:
                #     Basalt niveau i CURA UI.
                #
                # ADVANCED:
                #     Avanceret niveau i CURA UI.
                "rehabilitation_subtype": (
                    subtype_code
                ),
                "diagnoses": (
                    _get_diagnoses(
                        resource
                    )
                ),
            }
        )

    return result


# ------------------------------------------------------------
# 1. HENT COMMUNICATIONS I EN PERIODE
# ------------------------------------------------------------
def get_communications_in_period(
    received_from: str,
    received_to: str,
    *,
    message_type: str | None = None,
    profile: str | None = None,
    count: int = 1000,
    raw: bool = False,
) -> dict:
    """Henter én side Communications med oplysninger om næste side.

    raw=True returnerer CURA-svaret uændret.
    raw=False bevarer eksisterende felter og tilføjer:
      bundle_entry_count: Antal entries i dette svar.
      link_relations: Linktyper uden URL'er.
      has_next: Om svaret annoncerer en næste side.

    bundle_total er CURAs værdi, ikke et verificeret antal.
    has_next=False er ikke i sig selv en garanti for fuldstændighed.
    Funktionen henter ikke efterfølgende sider.
    """
    start = _validate_iso_datetime(received_from, "received_from")
    end = _validate_iso_datetime(received_to, "received_to")
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count skal være et helt tal.")
    if not 1 <= count <= 1000:
        raise ValueError("count skal være mellem 1 og 1000.")

    resolved_profile = _resolve_profile(message_type, profile)
    endpoint = "Communication?" + urlencode(
        [
            ("_profile", resolved_profile),
            ("received", f"ge{start}"),
            ("received", f"le{end}"),
            ("_count", str(count)),
        ],
        doseq=True,
    )
    bundle = get(endpoint, raw=True)
    if raw:
        return bundle
    if not isinstance(bundle, dict):
        raise RuntimeError("CURA returnerede ikke en dictionary.")

    entries = bundle.get("entry", [])
    links = bundle.get("link", [])
    if not isinstance(entries, list):
        raise RuntimeError("CURA Bundle.entry er ikke en liste.")
    if not isinstance(links, list):
        raise RuntimeError("CURA Bundle.link er ikke en liste.")

    # Ukendt linkformat må ikke skjule en mulig næste side.
    link_relations = []
    for link in links:
        if not isinstance(link, dict):
            raise RuntimeError("Uventet linkformat i CURA-svaret.")
        relation = link.get("relation")
        if not isinstance(relation, str) or not relation.strip():
            raise RuntimeError("CURA-link mangler relation.")
        link_relations.append(relation.strip())

    communications = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Uventet entry-format i CURA-svaret.")
        resource = entry.get("resource", {})
        if not isinstance(resource, dict):
            raise RuntimeError("Uventet resource-format i CURA-svaret.")
        if resource.get("resourceType") == "Communication":
            communications.append(_normalise_communication(resource))

    communications.sort(
        key=lambda item: str(item.get("received") or item.get("sent") or ""),
        reverse=True,
    )
    return {
        "found": bool(communications),
        "count": len(communications),
        "bundle_total": bundle.get("total"),
        "bundle_entry_count": len(entries),
        "link_relations": link_relations,
        "has_next": "next" in link_relations,
        "profile": resolved_profile,
        "received_from": start,
        "received_to": end,
        "communications": communications,
    }


# ------------------------------------------------------------
# 2. HENT ÉN COMMUNICATION VIA ID
# ------------------------------------------------------------
def get_communication_by_id(
    communication_id: str,
    *,
    raw: bool = False,
) -> dict:
    """
    Henter hele Communication-ressourcen via id.

    raw=True returnerer ressourcen helt uændret, inklusive contentString.
    raw=False returnerer fælles felter, content_strings og raw_resource.
    """
    validated_id = _required_text(communication_id, "communication_id")
    resource = get(f"Communication/{validated_id}", raw=True)
    if not isinstance(resource, dict):
        raise RuntimeError("CURA returnerede ikke en dictionary.")
    if resource.get("resourceType") != "Communication":
        raise RuntimeError("Ressourcen er ikke en Communication.")
    return resource if raw else _normalise_communication(resource)


# ------------------------------------------------------------
# 3. OPDATÉR UNDERTYPE PÅ GENOPTRÆNINGSPLAN
# ------------------------------------------------------------
def update_rehabilitation_plan_subtype(
    communication_id: str,
    subtype_code: str,
    *,
    expected_current_subtype: str | None = None,
    dry_run: bool = True,
    raw: bool = False,
) -> dict:
    """
    Ændrer undertypen på en CuraRehabilitationPlan.

    Ressourcen opdateres efter dette mønster:

        1. GET Communication/{id}
        2. Kontrollér resourceType og profil.
        3. Find den eksisterende subType-extension.
        4. Ændr kun valueCode.
        5. PUT hele Communication-ressourcen.
        6. GET Communication/{id} igen.
        7. Kontrollér den gemte valueCode.

    UI-sammenhæng:

        BASIC:
            Vises som "Basalt niveau" i CURA UI.

        ADVANCED:
            Vises som "Avanceret niveau" i CURA UI.

    Funktionen returnerer kun API-koderne BASIC og ADVANCED.
    UI-navnene returneres ikke.

    Parametre:
        communication_id:
            Det tekniske id på Communication-ressourcen.

        subtype_code:
            Den nye undertype.

            Tilladte værdier:
                BASIC
                ADVANCED

        expected_current_subtype:
            Valgfri sikkerhedskontrol.

            Hvis værdien eksempelvis er BASIC, stopper funktionen,
            hvis CURAs aktuelle værdi ikke længere er BASIC.

            Dette beskytter mod at overskrive en ændring, som en
            anden bruger eller proces har foretaget.

        dry_run:
            True:
                Der laves ingen PUT.

                Funktionen henter ressourcen, laver ændringen i en
                kopi og returnerer den foreslåede ændring.

            False:
                Den ændrede ressource sendes til CURA med PUT.

                Ressourcen hentes derefter igen, så ændringen kan
                verificeres.

        raw:
            Ved dry_run=True:
                Medtager original_resource, hvis raw=True.

            Ved dry_run=False:
                Medtager put_response og verified_resource,
                hvis raw=True.

    Output ved dry run:
        {
            "success": True,
            "changed": False,
            "verified": False,
            "dry_run": True,
            "communication_id": "...",
            "old_subtype": "BASIC",
            "new_subtype": "ADVANCED",
            "message": "Dry run. Ingen PUT blev sendt til CURA.",
            "updated_resource": {...},
        }

    Output efter en verificeret PUT:
        {
            "success": True,
            "changed": True,
            "verified": True,
            "dry_run": False,
            "communication_id": "...",
            "old_subtype": "BASIC",
            "new_subtype": "ADVANCED",
            "stored_subtype": "ADVANCED",
            "message": "Undertypen blev opdateret og verificeret.",
        }
    """
    validated_id = _required_text(
        communication_id,
        "communication_id",
    )

    validated_subtype = (
        _required_text(
            subtype_code,
            "subtype_code",
        )
        .upper()
    )

    allowed_subtypes = {
        "BASIC",
        "ADVANCED",
    }

    if (
        validated_subtype
        not in allowed_subtypes
    ):
        raise ValueError(
            "subtype_code skal være "
            "'BASIC' eller 'ADVANCED'."
        )

    if not isinstance(dry_run, bool):
        raise TypeError(
            "dry_run skal være True eller False."
        )

    validated_expected_subtype = None

    if (
        expected_current_subtype
        is not None
    ):
        validated_expected_subtype = (
            _required_text(
                expected_current_subtype,
                "expected_current_subtype",
            )
            .upper()
        )

        if (
            validated_expected_subtype
            not in allowed_subtypes
        ):
            raise ValueError(
                "expected_current_subtype skal være "
                "'BASIC' eller 'ADVANCED'."
            )

    # --------------------------------------------------------
    # 1. HENT DEN AKTUELLE RESOURCE FRA CURA
    # --------------------------------------------------------
    original_resource = get(
        f"Communication/{validated_id}",
        raw=True,
    )

    if not isinstance(
        original_resource,
        dict,
    ):
        raise RuntimeError(
            "CURA returnerede ikke en dictionary."
        )

    if (
        original_resource.get(
            "resourceType"
        )
        != "Communication"
    ):
        raise RuntimeError(
            "Ressourcen er ikke en Communication."
        )

    profiles = _get_profiles(
        original_resource
    )

    if (
        REHABILITATION_PLAN_PROFILE
        not in profiles
    ):
        raise ValueError(
            "Communication-ressourcen har ikke "
            "profilen CuraRehabilitationPlan. "
            f"Fundne profiler: {profiles}"
        )

    # --------------------------------------------------------
    # 2. LAV EN KOPI
    # --------------------------------------------------------
    updated_resource = deepcopy(
        original_resource
    )

    # --------------------------------------------------------
    # 3. FIND UNDERTYPE-EXTENSIONEN
    # --------------------------------------------------------
    subtype_extension = (
        _find_extension(
            updated_resource,
            REHABILITATION_SUBTYPE_URL,
        )
    )

    if not subtype_extension:
        raise ValueError(
            "Ressourcen mangler den forventede "
            "CuraRehabilitationPlan/subType-extension."
        )

    current_subtype = str(
        subtype_extension.get(
            "valueCode"
        )
        or ""
    ).strip().upper()

    # --------------------------------------------------------
    # 4. SIKKERHEDSKONTROL
    # --------------------------------------------------------
    if (
        validated_expected_subtype
        is not None
        and current_subtype
        != validated_expected_subtype
    ):
        raise RuntimeError(
            "Undertypen blev ikke ændret, fordi "
            "den aktuelle værdi ikke matcher den "
            "forventede værdi. "
            f"Forventet: "
            f"{validated_expected_subtype}. "
            f"Aktuel: {current_subtype}."
        )

    # --------------------------------------------------------
    # 5. RETURNÉR HVIS VÆRDIEN ALLEREDE ER KORREKT
    # --------------------------------------------------------
    if (
        current_subtype
        == validated_subtype
    ):
        return {
            "success": True,
            "changed": False,
            "verified": True,
            "dry_run": dry_run,
            "communication_id": validated_id,
            "old_subtype": current_subtype,
            "new_subtype": validated_subtype,
            "stored_subtype": current_subtype,
            "message": (
                "Ressourcen har allerede "
                "den ønskede undertype."
            ),
        }

    # --------------------------------------------------------
    # 6. ÆNDR KUN VALUECODE
    # --------------------------------------------------------
    subtype_extension[
        "valueCode"
    ] = validated_subtype

    # --------------------------------------------------------
    # 7. DRY RUN
    # --------------------------------------------------------
    if dry_run:
        result = {
            "success": True,
            "changed": False,
            "verified": False,
            "dry_run": True,
            "communication_id": validated_id,
            "old_subtype": current_subtype,
            "new_subtype": validated_subtype,
            "message": (
                "Dry run. Ingen PUT blev "
                "sendt til CURA."
            ),
            "updated_resource": (
                updated_resource
            ),
        }

        if raw:
            result[
                "original_resource"
            ] = original_resource

        return result

    # --------------------------------------------------------
    # 8. SEND HELE RESSOURCEN MED PUT
    # --------------------------------------------------------
    put_response = put(
        f"Communication/{validated_id}",
        updated_resource,
        raw=True,
    )

    # --------------------------------------------------------
    # 9. HENT RESSOURCEN IGEN
    # --------------------------------------------------------
    verified_resource = get(
        f"Communication/{validated_id}",
        raw=True,
    )

    if not isinstance(
        verified_resource,
        dict,
    ):
        raise RuntimeError(
            "PUT blev sendt, men CURA returnerede "
            "ikke en læsbar resource ved kontrol-GET."
        )

    # --------------------------------------------------------
    # 10. FIND DEN GEMTE VÆRDI
    # --------------------------------------------------------
    verified_extension = (
        _find_extension(
            verified_resource,
            REHABILITATION_SUBTYPE_URL,
        )
    )

    if not verified_extension:
        raise RuntimeError(
            "PUT blev sendt, men den efterfølgende "
            "resource mangler subType-extensionen."
        )

    stored_subtype = str(
        verified_extension.get(
            "valueCode"
        )
        or ""
    ).strip().upper()

    verified = (
        stored_subtype
        == validated_subtype
    )

    if not verified:
        raise RuntimeError(
            "CURA accepterede PUT-kaldet, men den "
            "efterfølgende kontrol fandt ikke den "
            "forventede værdi. "
            f"Forventet gemt værdi: "
            f"{validated_subtype}. "
            f"Faktisk gemt værdi: "
            f"{stored_subtype}."
        )

    # --------------------------------------------------------
    # 11. VERIFICERET RESULTAT
    # --------------------------------------------------------
    result = {
        "success": True,
        "changed": True,
        "verified": True,
        "dry_run": False,
        "communication_id": validated_id,
        "old_subtype": current_subtype,
        "new_subtype": validated_subtype,
        "stored_subtype": stored_subtype,
        "message": (
            "Undertypen blev opdateret "
            "og verificeret."
        ),
    }

    if raw:
        result[
            "put_response"
        ] = put_response

        result[
            "verified_resource"
        ] = verified_resource

    return result

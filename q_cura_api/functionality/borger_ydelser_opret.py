from __future__ import annotations

from copy import deepcopy
from typing import Any

from q_cura_api.api_client import get, post

YDELSE_PROFILE = (
    "http://curafhir.dk/p/"
    "CuraGrantedProcedureRequest"
)

EXTENSION_PATHWAY = (
    "http://curafhir.dk/x/"
    "CuraGrantedProcedureRequest/pathway"
)

EXTENSION_PERIOD = (
    "http://curafhir.dk/x/"
    "CuraGrantedProcedureRequest/period"
)


def _required_text(
    value: Any,
    field_name: str,
) -> str:
    result = str(
        value
        or ""
    ).strip()

    if not result:
        raise ValueError(
            f"{field_name} skal være udfyldt"
        )

    return result


def _clean_meta(
    resource: dict,
) -> None:
    meta = resource.get("meta")

    if not isinstance(meta, dict):
        return

    meta.pop("versionId", None)
    meta.pop("lastUpdated", None)
    meta.pop("extension", None)


def _find_extension(
    resource: dict,
    extension_url: str,
) -> dict | None:
    extensions = resource.get("extension")

    if not isinstance(extensions, list):
        return None

    for extension in extensions:
        if (
            isinstance(extension, dict)
            and extension.get("url")
            == extension_url
        ):
            return extension

    return None


def lav_ydelse_skabelon_fra_resource(
    resource: dict,
) -> dict:
    """
    Laver en genbrugelig ProcedureRequest-skabelon
    fra en eksisterende ydelse.

    Serverstyrede felter fjernes. Lokale
    CURA-extensions og koder bevares.

    Borger, leverandør, forløb og datoer erstattes
    med pladsholdere.
    """
    if not isinstance(resource, dict):
        raise TypeError(
            "resource skal være en dictionary"
        )

    if (
        resource.get("resourceType")
        != "ProcedureRequest"
    ):
        raise ValueError(
            "Ressourcen er ikke en ProcedureRequest"
        )

    template = deepcopy(resource)

    template.pop("id", None)
    template.pop("identifier", None)
    template.pop("implicitRules", None)

    _clean_meta(template)

    template["subject"] = {
        "reference": "Patient/INDSAET_BORGER_ID"
    }

    if isinstance(
        template.get("performer"),
        dict,
    ):
        template["performer"] = {
            "reference": (
                "Organization/"
                "INDSAET_LEVERANDOER_ORGANISATION_ID"
            )
        }

    pathway = _find_extension(
        template,
        EXTENSION_PATHWAY,
    )

    if pathway is None:
        raise ValueError(
            "Ydelsen mangler pathway-extensionen"
        )

    pathway["valueReference"] = {
        "reference": (
            "CarePlan/INDSAET_FORLOEB_ID"
        )
    }

    period_extension = _find_extension(
        template,
        EXTENSION_PERIOD,
    )

    if period_extension is not None:
        value_period = period_extension.get(
            "valuePeriod"
        )

        if isinstance(value_period, dict):
            if "start" in value_period:
                value_period["start"] = (
                    "INDSAET_START_DATETIME"
                )

            if "end" in value_period:
                value_period["end"] = (
                    "INDSAET_SLUT_DATETIME_ELLER_FJERN"
                )

    if "orderedOn" in template:
        template["orderedOn"] = (
            "INDSAET_ORDERED_ON_DATETIME"
        )

    return template


def build_ydelse_fra_skabelon(
    template: dict,
    borger_id: str,
    forloeb_id: str,
    leverandoer_organisation_id: str,
    *,
    start_datetime: str | None = None,
    ordered_on_datetime: str | None = None,
    slut_datetime: str | None = None,
) -> dict:
    """
    Bygger POST-body til en ny
    CuraGrantedProcedureRequest.
    """
    if not isinstance(template, dict):
        raise TypeError(
            "template skal være en dictionary"
        )

    if (
        template.get("resourceType")
        != "ProcedureRequest"
    ):
        raise ValueError(
            "Skabelonen er ikke en ProcedureRequest"
        )

    body = deepcopy(template)

    body["subject"] = {
        "reference": (
            "Patient/"
            f"{_required_text(borger_id, 'borger_id')}"
        )
    }

    body["performer"] = {
        "reference": (
            "Organization/"
            f"{_required_text(
                leverandoer_organisation_id,
                'leverandoer_organisation_id',
            )}"
        )
    }

    pathway = _find_extension(
        body,
        EXTENSION_PATHWAY,
    )

    if pathway is None:
        raise ValueError(
            "Skabelonen mangler pathway-extensionen"
        )

    pathway["valueReference"] = {
        "reference": (
            "CarePlan/"
            f"{_required_text(forloeb_id, 'forloeb_id')}"
        )
    }

    period_extension = _find_extension(
        body,
        EXTENSION_PERIOD,
    )

    if period_extension is not None:
        value_period = period_extension.setdefault(
            "valuePeriod",
            {},
        )

        if start_datetime is not None:
            value_period["start"] = _required_text(
                start_datetime,
                "start_datetime",
            )
        elif value_period.get("start") == (
            "INDSAET_START_DATETIME"
        ):
            raise ValueError(
                "start_datetime skal udfyldes"
            )

        if slut_datetime is not None:
            value_period["end"] = _required_text(
                slut_datetime,
                "slut_datetime",
            )
        elif value_period.get("end") == (
            "INDSAET_SLUT_DATETIME_ELLER_FJERN"
        ):
            value_period.pop("end", None)

    if ordered_on_datetime is not None:
        body["orderedOn"] = _required_text(
            ordered_on_datetime,
            "ordered_on_datetime",
        )
    elif body.get("orderedOn") == (
        "INDSAET_ORDERED_ON_DATETIME"
    ):
        raise ValueError(
            "ordered_on_datetime skal udfyldes"
        )

    body.pop("id", None)

    _clean_meta(body)

    return body


def opret_ydelse_fra_skabelon(
    template: dict,
    borger_id: str,
    forloeb_id: str,
    leverandoer_organisation_id: str,
    *,
    start_datetime: str | None = None,
    ordered_on_datetime: str | None = None,
    slut_datetime: str | None = None,
    raw: bool = False,
):
    """
    Opretter en ydelse, henter den igen og
    kontrollerer pathway.
    """
    body = build_ydelse_fra_skabelon(
        template,
        borger_id,
        forloeb_id,
        leverandoer_organisation_id,
        start_datetime=start_datetime,
        ordered_on_datetime=(
            ordered_on_datetime
        ),
        slut_datetime=slut_datetime,
    )

    created = post(
        "ProcedureRequest",
        body,
        raw=False,
    )

    if not isinstance(created, dict):
        raise RuntimeError(
            "CURA returnerede ikke en "
            "ProcedureRequest-resource ved oprettelse"
        )

    ydelse_id = str(
        created.get("id")
        or ""
    ).strip()

    if not ydelse_id:
        raise RuntimeError(
            "CURA-svaret indeholdt ikke id på den "
            "nye ydelse"
        )

    verified = get(
        f"ProcedureRequest/{ydelse_id}",
        raw=True,
    )

    pathway = (
        _find_extension(
            verified,
            EXTENSION_PATHWAY,
        )
        or {}
    )

    pathway_reference = str(
        (
            pathway.get("valueReference")
            or {}
        ).get("reference")
        or ""
    )

    expected_pathway = (
        f"CarePlan/{forloeb_id}"
    )

    if pathway_reference != expected_pathway:
        raise RuntimeError(
            "Den oprettede ydelse peger ikke på "
            "det forventede forløb. "
            f"Forventet: {expected_pathway}. "
            f"Fundet: {pathway_reference}."
        )

    if raw:
        return verified

    subject = (
        verified.get("subject")
        or {}
    )

    subject_reference = str(
        subject.get("reference")
        or ""
    )

    return {
        "ydelse_id": ydelse_id,
        "ydelse_reference": (
            f"ProcedureRequest/{ydelse_id}"
        ),
        "borger_reference": subject_reference,
        "borger_id": (
            subject_reference.split("/", 1)[-1]
        ),
        "forloeb_reference": pathway_reference,
        "forloeb_id": (
            pathway_reference.split("/", 1)[-1]
        ),
        "status": verified.get("status"),
        "raw_resource": verified,
    }
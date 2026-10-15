import os
from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import get, set_cura_credential

# ------------------------------------------------------------
# KONFIGURATION TIL DENNE LOKALE, LÆSENDE TEST
# ------------------------------------------------------------
CURA_CREDENTIAL = "API_CURA"
BORGER_ID = "39dde427-b1fc-42b3-9e85-fccf727ee3bf"

GRANTED_PROFILE = "http://curafhir.dk/p/CuraGrantedProcedureRequest"
CARE_PLAN_PROFILE = "http://curafhir.dk/p/CuraCarePlan"
PATHWAY_URL = "http://curafhir.dk/x/CuraGrantedProcedureRequest/pathway"


def get_entries(bundle: dict, context: str) -> list[dict]:
    """Validerer et råt FHIR Bundle og returnerer dets entries."""
    if not isinstance(bundle, dict):
        raise RuntimeError(f"{context}: CURA returnerede ikke en dictionary.")

    if bundle.get("resourceType") != "Bundle":
        raise RuntimeError(
            f"{context}: Forventede resourceType='Bundle'."
        )

    links = bundle.get("link", [])

    if not isinstance(links, list):
        raise RuntimeError(
            f"{context}: Bundle.link er ikke en liste."
        )

    if any(
        isinstance(link, dict)
        and link.get("relation") == "next"
        for link in links
    ):
        raise RuntimeError(
            f"{context}: CURA returnerede flere sider. Testen stopper, "
            "så resultatet ikke fejlagtigt opfattes som komplet."
        )

    entries = bundle.get("entry", [])

    if not isinstance(entries, list):
        raise RuntimeError(
            f"{context}: Bundle.entry er ikke en liste."
        )

    return entries


def get_resources(
    bundle: dict,
    resource_type: str,
    context: str,
) -> list[dict]:
    """Henter ressourcer af én bestemt type fra et valideret Bundle."""
    resources = []

    for entry in get_entries(bundle, context):
        if not isinstance(entry, dict):
            raise RuntimeError(
                f"{context}: Uventet format i Bundle.entry."
            )

        resource = entry.get("resource", {})

        if not isinstance(resource, dict):
            raise RuntimeError(
                f"{context}: Uventet format i entry.resource."
            )

        if resource.get("resourceType") == resource_type:
            resources.append(resource)

    return resources


def find_pathway_extensions(resource: dict) -> list[dict]:
    """Finder alle pathway-extensions uden at antage værditypen."""
    extensions = resource.get("extension", [])

    if not isinstance(extensions, list):
        raise RuntimeError(
            "ProcedureRequest.extension er ikke en liste."
        )

    return [
        extension
        for extension in extensions
        if isinstance(extension, dict)
        and extension.get("url") == PATHWAY_URL
    ]


def find_reference_values(value) -> list[str]:
    """Finder reference-værdier rekursivt i en ukendt struktur."""
    references = []

    if isinstance(value, dict):
        reference = value.get("reference")

        if isinstance(reference, str) and reference.strip():
            references.append(reference.strip())

        for child in value.values():
            references.extend(
                find_reference_values(child)
            )

    elif isinstance(value, list):
        for child in value:
            references.extend(
                find_reference_values(child)
            )

    return references


def get_first_display(resource: dict) -> str:
    """Henter første display fra ProcedureRequest.code.coding."""
    code = resource.get("code", {})

    if not isinstance(code, dict):
        return ""

    coding = code.get("coding", [])

    if not isinstance(coding, list):
        return ""

    for item in coding:
        if isinstance(item, dict) and item.get("display"):
            return str(item["display"])

    return ""


def get_extension_value(
    resource: dict,
    extension_url: str,
):
    """Henter første value[x] uden at kende typen på forhånd."""
    extensions = resource.get("extension", [])

    if not isinstance(extensions, list):
        return ""

    for extension in extensions:
        if not isinstance(extension, dict):
            continue

        if extension.get("url") != extension_url:
            continue

        for key, value in extension.items():
            if key.startswith("value"):
                return value

        return extension.get("extension", "")

    return ""


def summarize_care_plan(resource: dict) -> dict:
    """Returnerer kun relevante tekniske felter fra et forløb."""
    period = resource.get("period", {})

    if not isinstance(period, dict):
        period = {}

    return {
        "care_plan_id": resource.get("id", ""),
        "status": resource.get("status", ""),
        "name": get_extension_value(
            resource,
            "http://curafhir.dk/x/CuraCarePlan/name",
        ),
        "description": resource.get(
            "description",
            "",
        ),
        "period_start": period.get(
            "start",
            "",
        ),
        "period_end": period.get(
            "end",
            "",
        ),
    }


def main() -> None:
    """Undersøger koblingen mellem ydelser og CuraCarePlan."""
    borger_id = os.getenv(
        "BORGER_ID",
        BORGER_ID,
    ).strip()

    if (
        not borger_id
        or borger_id == "SKRIV_BORGER_ID_HER"
    ):
        raise ValueError(
            "Skriv borgerens Cura-ID i BORGER_ID "
            "eller angiv BORGER_ID i .env."
        )

    set_cura_credential(
        CURA_CREDENTIAL
    )

    # --------------------------------------------------------
    # TRIN 1: HENT BORGERENS YDELSER
    # --------------------------------------------------------
    procedure_endpoint = (
        "ProcedureRequest?"
        + urlencode({
            "subject": borger_id,
            "_profile": GRANTED_PROFILE,
            "_count": "1000",
        })
    )

    procedure_bundle = get(
        procedure_endpoint,
        raw=True,
    )

    procedures = get_resources(
        procedure_bundle,
        "ProcedureRequest",
        "Ydelsessøgning",
    )

    # --------------------------------------------------------
    # TRIN 2: FIND PATHWAY PÅ HVER YDELSE
    # --------------------------------------------------------
    pathway_results = []
    referenced_care_plan_ids = set()

    for procedure in procedures:
        pathway_extensions = (
            find_pathway_extensions(
                procedure
            )
        )

        references = []

        for extension in pathway_extensions:
            references.extend(
                find_reference_values(
                    extension
                )
            )

        references = sorted(
            set(references)
        )

        for reference in references:
            if reference.startswith("CarePlan/"):
                care_plan_id = (
                    reference
                    .rstrip("/")
                    .split("/")[-1]
                )

                referenced_care_plan_ids.add(
                    care_plan_id
                )

        pathway_results.append({
            "procedure_request_id": (
                procedure.get("id", "")
            ),
            "ydelsesnavn": (
                get_first_display(
                    procedure
                )
            ),
            "status": procedure.get(
                "status",
                "",
            ),
            "pathway_fundet": bool(
                pathway_extensions
            ),
            "pathway_antal": len(
                pathway_extensions
            ),
            "fundne_referencer": references,

            # Hele pathway-extensionen vises, fordi formålet
            # med testen er at lære den faktiske struktur.
            "pathway_extensions": (
                pathway_extensions
            ),
        })

    print("\n" + "=" * 100)
    print(
        "TRIN 1 OG 2: "
        "YDELSER OG PATHWAY-EXTENSIONS"
    )
    print("=" * 100)

    print(
        f"Antal ydelser: {len(procedures)}"
    )

    print(
        "Antal ydelser med pathway: "
        f"{sum(
            item['pathway_fundet']
            for item in pathway_results
        )}"
    )

    pprint(
        pathway_results,
        width=160,
        sort_dicts=False,
    )

    # --------------------------------------------------------
    # TRIN 3: HENT BORGERENS FORLØB SOM CURACAREPLAN
    # --------------------------------------------------------
    care_plan_endpoint = (
        "CarePlan?"
        + urlencode({
            "subject": borger_id,
            "_profile": CARE_PLAN_PROFILE,
            "_count": "1000",
        })
    )

    care_plan_bundle = get(
        care_plan_endpoint,
        raw=True,
    )

    care_plans = get_resources(
        care_plan_bundle,
        "CarePlan",
        "Forløbssøgning",
    )

    care_plans_by_id = {
        str(care_plan.get("id") or ""): (
            care_plan
        )
        for care_plan in care_plans
        if care_plan.get("id")
    }

    print("\n" + "=" * 100)
    print(
        "TRIN 3: "
        "BORGERENS CURACAREPLAN-FORLØB"
    )
    print("=" * 100)

    pprint(
        [
            summarize_care_plan(
                care_plan
            )
            for care_plan in care_plans
        ],
        width=160,
        sort_dicts=False,
    )

    # --------------------------------------------------------
    # TRIN 4: SAMMENLIGN PATHWAY-ID MED CAREPLAN-ID
    # --------------------------------------------------------
    comparison = []

    for care_plan_id in sorted(
        referenced_care_plan_ids
    ):
        care_plan = care_plans_by_id.get(
            care_plan_id
        )

        comparison.append({
            "pathway_care_plan_id": (
                care_plan_id
            ),
            "fundet_blandt_borgerens_care_plans": (
                care_plan is not None
            ),
            "care_plan": (
                summarize_care_plan(
                    care_plan
                )
                if care_plan is not None
                else None
            ),
        })

    print("\n" + "=" * 100)
    print(
        "TRIN 4: MATCH MELLEM YDELSENS "
        "PATHWAY OG BORGERENS CAREPLAN"
    )
    print("=" * 100)

    pprint(
        comparison,
        width=160,
        sort_dicts=False,
    )

    print(
        "\nTesten er kun læsende. "
        "Der udføres ingen POST eller PUT."
    )


if __name__ == "__main__":
    main()
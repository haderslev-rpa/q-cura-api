from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.organisation_hent import get_organizations

# Opsætning til denne selvstændige test.
CURA_CREDENTIAL_NAME = "API_CURA"
TEST_NAVN = "Social og Sundhed"  # Hele navnet, uden *.
INCLUDE_INACTIVE = True


def hent_organisationer() -> list[dict]:
    """Henter rå organisationer og stopper ved ufuldstændig sidevisning."""
    bundle = get_organizations(
        search_name=None,
        raw=True,
        include_inactive=True,
    )
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise RuntimeError("Forventede et FHIR Bundle fra CURA.")

    # Undgå at præsentere en delvis liste som et komplet resultat.
    if any(link.get("relation") == "next" for link in bundle.get("link", [])):
        raise RuntimeError(
            "CURA returnerede flere sider. Testen stopper, så navnematch "
            "og listen ikke bygger på et ufuldstændigt resultat. "
            "Der skal tilføjes sidehentning til organisationopslaget."
        )

    organisationer = {}
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Organization":
            continue
        org_id = resource.get("id")
        if not org_id:
            raise RuntimeError("En organisation mangler id.")
        organisationer[org_id] = resource

    return list(organisationer.values())


def main():
    """Finder en organisation på navn og derefter dens direkte børn."""
    navn = TEST_NAVN.strip()
    if not navn or "*" in navn or "?" in navn:
        raise ValueError("TEST_NAVN skal være det præcise navn uden wildcards.")

    set_cura_credential(CURA_CREDENTIAL_NAME)
    organisationer = hent_organisationer()

    # Trin 1: Præcist navnematch, også med samme store/små bogstaver.
    print("\nTRIN 1: FIND OVERORGANISATION PÅ PRÆCIST NAVN")
    matches = [org for org in organisationer if org.get("name") == navn]
    if len(matches) != 1:
        pprint([
            {"name": org.get("name"), "organization_id": org["id"]}
            for org in matches
        ], sort_dicts=False)
        raise RuntimeError(
            f"Forventede ét præcist navnematch på {navn!r}, "
            f"men fandt {len(matches)}. Ingen organisation blev valgt."
        )

    overorganisation = matches[0]
    overordnet_id = overorganisation["id"]
    print(f"Navn: {overorganisation['name']}")
    print(f"Id: {overordnet_id}")
    print(f"Aktiv: {overorganisation.get('active')}")

    # Trin 2: Søg i de hentede ressourcers partOf.reference.
    # Der bruges den fundne organisations eget id, ikke dens partOf-id.
    print("\nTRIN 2: FIND DIREKTE UNDERORGANISATIONER")
    reference = f"Organization/{overordnet_id}"
    underorganisationer = []
    for org in organisationer:
        part_of = org.get("partOf") or {}
        if part_of.get("reference") != reference:
            continue
        if not INCLUDE_INACTIVE and org.get("active") is not True:
            continue
        underorganisationer.append({
            "organization_id": org["id"],
            "name": org.get("name"),
            "active": org.get("active"),
            "part_of_reference": part_of["reference"],
        })

    underorganisationer.sort(key=lambda org: (org["name"] or "").casefold())
    pprint({
        "overordnet_id": overordnet_id,
        "overordnet_navn": overorganisation["name"],
        "count": len(underorganisationer),
        "organisationer": underorganisationer,
    }, width=120, sort_dicts=False)


if __name__ == "__main__":
    main()
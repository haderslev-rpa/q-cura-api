from fnmatch import fnmatch
from urllib.parse import quote

from q_cura_api.api_client import get


# ------------------------------------------------------------
# HENT ORGANISATIONER MED VALGFRI SØGNING
# ------------------------------------------------------------
def get_organizations(
    search_name: str = None,
    raw: bool = False,
    include_inactive: bool = True,
):
    """
    Henter organisationer fra Cura.

    Input:
        search_name:
            None eller tom tekst:
                Henter alle organisationer.

            Almindelig tekst:
                Søger efter organisationer, hvor navnet indeholder teksten.

                Eksempel:
                    search_name="Senior"

            Wildcard med *:
                * betyder nul eller flere vilkårlige tegn.

                Eksempler:
                    "*Senior*" finder navne, der indeholder "Senior".
                    "Forebyggende*" finder navne, der starter med
                    "Forebyggende".
                    "*Seniorer" finder navne, der slutter med "Seniorer".

            Wildcard med ?:
                ? betyder præcis ét vilkårligt tegn.

                Eksempel:
                    "Team ?" kan finde "Team A" og "Team 1".

        raw:
            Hvis raw=True, returneres det rå Cura-svar uden
            Python-filtrering.

        include_inactive:
            False er standard og returnerer kun aktive organisationer.
            True returnerer både aktive og inaktive organisationer.

    Output ved raw=False:
        {
            "found": True,
            "count": 2,
            "organizationer": [
                {
                    "organization_id": "...",
                    "name": "...",
                },
                {
                    "organization_id": "...",
                    "name": "...",
                },
            ],
        }

    Outputformatet er holdt simpelt og bagudkompatibelt:
    Hver organisation indeholder kun organization_id og name.
    """

    search_name = str(
        search_name or ""
    ).strip()

    has_wildcard = (
        "*" in search_name
        or "?" in search_name
    )

    # --------------------------------------------------------
    # BYG ENDPOINT
    # --------------------------------------------------------

    # Ved wildcard henter vi alle organisationer og filtrerer
    # bagefter i Python.
    if not search_name or has_wildcard:
        endpoint = (
            "Organization"
            "?_profile=http://curafhir.dk/p/CuraOrganization"
        )

    else:
        search_encoded = quote(
            search_name
        )

        endpoint = (
            "Organization"
            f"?name={search_encoded}"
            "&_profile=http://curafhir.dk/p/CuraOrganization"
        )

    data = get(
        endpoint,
        raw=raw,
    )

    # Ved raw=True returneres Cura-svaret uændret.
    # Der filtreres derfor ikke på active eller navn.
    if raw:
        return data

    # --------------------------------------------------------
    # STANDARDFORMAT
    # --------------------------------------------------------
    result = {
        "found": False,
        "count": 0,
        "organizationer": [],
    }

    if not isinstance(data, list):
        return result

    for item in data:
        if not isinstance(item, dict):
            continue

        resource = item.get(
            "resource",
            {},
        )

        if not isinstance(resource, dict):
            continue

        organization_id = resource.get("id")
        name = resource.get("name")
        active = resource.get("active")

        # ----------------------------------------------------
        # FILTRER INAKTIVE ORGANISATIONER
        # ----------------------------------------------------

        # Som standard medtages kun organisationer,
        # hvor active udtrykkeligt er True.
        if not include_inactive and active is not True:
            continue

        # En organisation uden ID eller navn er ikke brugbar
        # i det almindelige output.
        if not organization_id or not name:
            continue

        # ----------------------------------------------------
        # FILTRER PÅ NAVN
        # ----------------------------------------------------
        if search_name:
            normalized_name = str(name).lower()
            normalized_search = search_name.lower()

            if has_wildcard:
                # Wildcard-søgning.
                if not fnmatch(
                    normalized_name,
                    normalized_search,
                ):
                    continue

            else:
                # Almindelig case-insensitive contains-søgning.
                if normalized_search not in normalized_name:
                    continue

        # ----------------------------------------------------
        # BEVAR DET GAMLE, SIMPLE OUTPUT
        # ----------------------------------------------------
        result["organizationer"].append(
            {
                "organization_id": organization_id,
                "name": name,
            }
        )

    # Sortér organisationerne alfabetisk efter navn.
    result["organizationer"].sort(
        key=lambda organization: str(
            organization.get("name") or ""
        ).lower()
    )

    result["count"] = len(
        result["organizationer"]
    )

    result["found"] = (
        result["count"] > 0
    )

    return result

def get_organizations_by_parent_name(
    parent_name: str,
    include_inactive: bool = True,
) -> dict:
    """Find direkte underorganisationer ud fra overorganisationens navn.

    Sådan søger du på organisationspart (partOf):
        result = get_organizations_by_parent_name(
            parent_name="(Hjælpemidler) Frit valg",
            include_inactive=True,
        )
        organisationer = result["organizationer"]

    Navnet skal være præcist, inklusive store/små bogstaver.
    Wildcards er ikke tilladt. Du skal ikke selv angive et id.

    Trin 1: Find overorganisationen ved præcist navnematch.
    Trin 2: Find organisationer, hvis partOf.reference peger på dens id.

    include_inactive gælder kun underorganisationerne.
    Overorganisationen kan findes, selvom den er inaktiv.
    Kun direkte børn medtages, ikke børnebørn eller overorganisationen.

    Output:
        parent_organization: Den fundne overorganisation.
        found: True, hvis mindst én underorganisation blev fundet.
        count: Antal underorganisationer efter filtrering.
        organizationer: Liste med id, navn, active og part_of_reference.

    Rejser en fejl ved nul/flere navnematch eller ufuldstændigt svar.
    Funktionen printer intet og ændrer ingen data i CURA.
    Miljøet vælges af den kaldende proces med set_cura_credential().
    """
    if not isinstance(parent_name, str) or not parent_name.strip():
        raise ValueError("parent_name skal være en ikke-tom tekst.")

    parent_name = parent_name.strip()

    if "*" in parent_name or "?" in parent_name:
        raise ValueError(
            "parent_name skal være et præcist navn uden wildcards."
        )

    if not isinstance(include_inactive, bool):
        raise TypeError("include_inactive skal være True eller False.")

    # Hent alle rå organisationer én gang. Det simple output fra
    # get_organizations(raw=False) indeholder ikke partOf.
    bundle = get_organizations(search_name=None, raw=True)

    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise RuntimeError("Forventede et FHIR Bundle fra CURA.")

    links = bundle.get("link", [])
    entries = bundle.get("entry", [])

    if not isinstance(links, list) or not isinstance(entries, list):
        raise RuntimeError("Bundle.link og Bundle.entry skal være lister.")

    # Stop frem for at returnere en ufuldstændig liste.
    if any(
        isinstance(link, dict) and link.get("relation") == "next"
        for link in links
    ):
        raise RuntimeError(
            "CURA returnerede flere sider. Sidehentning skal implementeres "
            "før dette opslag kan returnere et komplet resultat."
        )

    # Saml organisationerne og fjern dubletter med samme id.
    organisations_by_id = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Uventet format i Bundle.entry.")

        resource = entry.get("resource", {})

        if not isinstance(resource, dict):
            raise RuntimeError("Uventet format i entry.resource.")

        if resource.get("resourceType") != "Organization":
            continue

        if not resource.get("id"):
            raise RuntimeError("En organisation mangler id.")

        organisations_by_id[resource["id"]] = resource

    # Trin 1: Brug navnet til at finde præcis én overorganisation.
    organisations = list(organisations_by_id.values())

    matches = [
        org
        for org in organisations
        if org.get("name") == parent_name
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Forventede ét præcist navnematch på {parent_name!r}, "
            f"men fandt {len(matches)}. Ingen organisation blev valgt."
        )

    parent = matches[0]
    parent_reference = f"Organization/{parent['id']}"

    # Trin 2: Sammenlign børnenes partOf med overorganisationens eget id.
    # Brug IKKE overorganisationens partOf: det ville finde dens søskende.
    children = []

    for org in organisations:
        part_of = org.get("partOf") or {}

        if not isinstance(part_of, dict):
            raise RuntimeError(
                "Organisationens partOf har et uventet format."
            )

        if org["id"] == parent["id"]:
            continue

        if part_of.get("reference") != parent_reference:
            continue

        # Filtreringen udføres her, fordi raw=True ikke filtrerer active.
        if not include_inactive and org.get("active") is not True:
            continue

        children.append({
            "organization_id": org["id"],
            "name": org.get("name"),
            "active": org.get("active"),
            "part_of_reference": parent_reference,
        })

    children.sort(
        key=lambda org: str(org["name"] or "").casefold()
    )

    return {
        "parent_organization": {
            "organization_id": parent["id"],
            "name": parent["name"],
            "active": parent.get("active"),
        },
        "found": bool(children),
        "count": len(children),
        "organizationer": children,
    }

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
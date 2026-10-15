from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_forloeb_opret import (
    EXTENSION_SUPPLIER,
    build_forloeb,
    opret_forloeb,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

# Testen må kun køres mod CURA-testmiljøet.
CURA_CREDENTIAL = "API_CURA_TEST"

FORLOEBSTYPE = "genoptraeningsforloeb_140"
HANDLING = "opret_og_bestil"

# Teknisk Patient-id uden "Patient/".
BORGER_ID = "0f5403d0-1575-4e9c-842e-d399ff55198a"

# Navnet skal være det præcise aktive organisationsnavn i CURA.
LEVERANDOER_NAVN = "Myndighed - Træning"

START_DATETIME = "2026-10-15T00:00:00+02:00"
HENVIST_FRA = "API-test i CURA testmiljø"
BEMAERKNING = "Oprettet og bestilt via q-cura-api test"

# Denne test opretter et rigtigt forløb, når værdien er True.
UDFOER_OPRETTELSE = True

# Ingen opfølgning i denne test.
OPFOELGNINGSDATO = None
OPFOELGNINGSORGANISATION_ID = None


# ------------------------------------------------------------
# HJÆLPEFUNKTIONER
# ------------------------------------------------------------


def find_extension(
    resource: dict,
    extension_url: str,
) -> dict | None:
    """Finder en extension ud fra dens fulde URL."""
    extensions = resource.get("extension")

    if not isinstance(extensions, list):
        return None

    for extension in extensions:
        if not isinstance(extension, dict):
            continue

        if extension.get("url") == extension_url:
            return extension

    return None


def get_reference(value) -> str:
    """Henter reference fra en FHIR valueReference."""
    if not isinstance(value, dict):
        return ""

    return str(value.get("reference") or "").strip()


def valider_testdata() -> None:
    """Stopper testen, hvis testdata ikke er klar."""
    if CURA_CREDENTIAL != "API_CURA_TEST":
        raise ValueError(
            "Testen må kun køres med CURA_CREDENTIAL='API_CURA_TEST'."
        )

    if HANDLING != "opret_og_bestil":
        raise ValueError(
            "Denne test skal bruge HANDLING='opret_og_bestil'."
        )

    if not BORGER_ID or BORGER_ID.startswith("INDSAET_"):
        raise ValueError(
            "Udfyld BORGER_ID med testborgerens tekniske Patient-id."
        )

    if (
        not LEVERANDOER_NAVN
        or LEVERANDOER_NAVN.startswith("INDSAET_")
    ):
        raise ValueError(
            "Udfyld LEVERANDOER_NAVN med det præcise aktive "
            "organisationsnavn fra CURA."
        )

    if not isinstance(UDFOER_OPRETTELSE, bool):
        raise TypeError("UDFOER_OPRETTELSE skal være True eller False.")


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def main() -> None:
    """
    Tester opret og bestil med leverandør angivet som navn.

    Flow:
    1. Vælg API_CURA_TEST.
    2. Slå leverandørnavnet op via organisation_hent.py.
    3. Byg POST-body og kontrollér status og supplier.
    4. Udfør ét POST CarePlan, hvis UDFOER_OPRETTELSE=True.
    5. Kontrollér det returnerede og genhentede CarePlan.
    """
    valider_testdata()

    set_cura_credential(CURA_CREDENTIAL)

    print()
    print("=" * 100)
    print("1. BYGGER OPRET-OG-BESTIL BODY FRA LEVERANDØRNAVN")
    print("=" * 100)
    print(f"Credential:      {CURA_CREDENTIAL}")
    print(f"Forløbstype:     {FORLOEBSTYPE}")
    print(f"Handling:        {HANDLING}")
    print(f"Borger-id:       {BORGER_ID}")
    print(f"Leverandørnavn:  {LEVERANDOER_NAVN}")

    body = build_forloeb(
        forloebstype=FORLOEBSTYPE,
        handling=HANDLING,
        borger_id=BORGER_ID,
        start_datetime=START_DATETIME,
        henvist_fra=HENVIST_FRA,
        bemaerkning=BEMAERKNING,
        leverandoer=LEVERANDOER_NAVN,
        leverandoer_type="navn",
        opfoelgningsdato=OPFOELGNINGSDATO,
        opfoelgningsorganisation_id=(
            OPFOELGNINGSORGANISATION_ID
        ),
    )

    if body.get("status") != "draft":
        raise AssertionError(
            "POST-body skal have status 'draft' ved opret_og_bestil. "
            f"Fundet: {body.get('status')}."
        )

    supplier_extension = find_extension(
        body,
        EXTENSION_SUPPLIER,
    )

    if supplier_extension is None:
        raise AssertionError(
            "POST-body mangler CuraCarePlan/supplier."
        )

    supplier_reference = get_reference(
        supplier_extension.get("valueReference")
    )

    if not supplier_reference.startswith("Organization/"):
        raise AssertionError(
            "Leverandøroplaget gav ikke en gyldig Organization-reference. "
            f"Fundet: {supplier_reference!r}."
        )

    print()
    print("Leverandør blev fundet:")
    print(f"  {supplier_reference}")
    print()
    print("POST-body:")
    pprint(body, width=180, sort_dicts=False)

    if not UDFOER_OPRETTELSE:
        print()
        print("DRY RUN BESTÅET")
        print("UDFOER_OPRETTELSE=False, så der blev ikke sendt POST.")
        return

    print()
    print("=" * 100)
    print("2. OPRETTER OG BESTILLER MED ÉT POST-KALD")
    print("=" * 100)

    resultat = opret_forloeb(
        forloebstype=FORLOEBSTYPE,
        handling=HANDLING,
        borger_id=BORGER_ID,
        start_datetime=START_DATETIME,
        henvist_fra=HENVIST_FRA,
        bemaerkning=BEMAERKNING,
        leverandoer=LEVERANDOER_NAVN,
        leverandoer_type="navn",
        opfoelgningsdato=OPFOELGNINGSDATO,
        opfoelgningsorganisation_id=(
            OPFOELGNINGSORGANISATION_ID
        ),
        raw=False,
    )

    print()
    print("Resultat fra CURA:")
    pprint(resultat, width=180, sort_dicts=False)

    print()
    print("=" * 100)
    print("3. KONTROLLERER RESULTATET")
    print("=" * 100)

    if resultat.get("success") is not True:
        raise AssertionError("Resultatet har ikke success=True.")

    if resultat.get("verified") is not True:
        raise AssertionError("Resultatet har ikke verified=True.")

    if resultat.get("handling") != "opret_og_bestil":
        raise AssertionError(
            "Resultatet har ikke handling='opret_og_bestil'."
        )

    if resultat.get("status") != "draft":
        raise AssertionError(
            "Det gemte forløb har ikke status 'draft'. "
            f"Fundet: {resultat.get('status')}."
        )

    if resultat.get("leverandoer_input_type") != "navn":
        raise AssertionError(
            "Resultatet viser ikke, at leverandøren blev angivet som navn."
        )

    if resultat.get("leverandoer_input") != LEVERANDOER_NAVN:
        raise AssertionError(
            "Resultatets leverandoer_input matcher ikke testens navn."
        )

    result_supplier_reference = str(
        resultat.get("leverandoer_reference") or ""
    ).strip()

    if result_supplier_reference != supplier_reference:
        raise AssertionError(
            "Den gemte leverandørreference matcher ikke opslaget. "
            f"Forventet: {supplier_reference}. "
            f"Fundet: {result_supplier_reference}."
        )

    forloeb_id = str(resultat.get("forloeb_id") or "").strip()

    if not forloeb_id:
        raise AssertionError("Resultatet mangler forloeb_id.")

    print("TEST BESTÅET")
    print(f"Nyt forløbs-id:  {forloeb_id}")
    print(f"Ny reference:    CarePlan/{forloeb_id}")
    print("Status:          draft")
    print(f"Leverandørnavn:  {resultat.get('leverandoer_navn')}")
    print(f"Leverandørref.:  {result_supplier_reference}")


if __name__ == "__main__":
    main()

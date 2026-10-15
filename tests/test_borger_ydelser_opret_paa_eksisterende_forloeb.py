from pprint import pprint
from datetime import datetime
from zoneinfo import ZoneInfo

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_ydelser_opret import (
    EXT_PATHWAY,
    EXT_SERVICE_VARIANT,
    build_ydelse,
    opret_ydelse,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

# Testen må kun køres mod CURA-testmiljøet.
CURA_CREDENTIAL = "API_CURA_TEST"

# Teknisk Patient-id uden "Patient/".
BORGER_ID = (
    "0f5403d0-1575-4e9c-842e-d399ff55198a"
)

# Teknisk CarePlan-id uden "CarePlan/".
# Indsæt id'et på det eksisterende, bestilte forløb.
FORLOEB_ID = (
    "32c60a31-f496-44c7-9524-27720116afe7"
)

# Det præcise UI-navn på ydelsen.
#
# Tilladte værdier fremgår af YDELSESOVERSAETTER i:
#
# q_cura_api/functionality/borger_ydelser_opret.py
YDELSESNAVN = (
    "Opstartssamtale §140 Ortopædisk §140"
)

# Navnet skal matche præcist én aktiv
# organisation i CURA.
LEVERANDOER_NAVN = (
    "Myndighed - Træning"
)

# Ydelsens startdato med tidszone.
START_DATETIME = (
    "2026-10-16T00:00:00+02:00"
)

# Ingen opfølgning i denne test.
OPFOELGNINGSDATO = None
OPFOELGNINGSORGANISATION = None

# True:
#     Udfører et rigtigt POST-kald og opretter ydelsen.
#
# False:
#     Bygger og kontrollerer kun POST-bodyen.
UDFOER_OPRETTELSE = True


# ------------------------------------------------------------
# HJÆLPEFUNKTIONER
# ------------------------------------------------------------


def find_extension(
    resource: dict,
    extension_url: str,
) -> dict | None:
    """
    Finder en extension ud fra dens fulde URL.
    """
    extensions = resource.get("extension")

    if not isinstance(extensions, list):
        return None

    for extension in extensions:
        if not isinstance(extension, dict):
            continue

        if extension.get("url") == extension_url:
            return extension

    return None


def get_reference(
    value,
) -> str:
    """
    Henter reference fra en FHIR valueReference.
    """
    if not isinstance(value, dict):
        return ""

    return str(
        value.get("reference")
        or ""
    ).strip()


def get_variant(
    resource: dict,
) -> str:
    """
    Henter varianten fra ServiceVariant-extensionen.
    """
    extension = find_extension(
        resource,
        EXT_SERVICE_VARIANT,
    )

    if extension is None:
        return ""

    codeable_concept = extension.get(
        "valueCodeableConcept"
    )

    if not isinstance(
        codeable_concept,
        dict,
    ):
        return ""

    return str(
        codeable_concept.get("text")
        or ""
    ).strip()


def get_pathway_reference(
    resource: dict,
) -> str:
    """
    Henter CarePlan-referencen fra
    pathway-extensionen.
    """
    extension = find_extension(
        resource,
        EXT_PATHWAY,
    )

    if extension is None:
        return ""

    return get_reference(
        extension.get("valueReference")
    )


def current_copenhagen_datetime() -> str:
    """
    Returnerer aktuelt tidspunkt med dansk tidszone.

    Værdien bruges som orderedOn.
    """
    return datetime.now(
        ZoneInfo("Europe/Copenhagen")
    ).isoformat(
        timespec="seconds"
    )


def valider_testdata() -> None:
    """
    Stopper testen, hvis testdata ikke er klar.
    """
    if CURA_CREDENTIAL != "API_CURA_TEST":
        raise ValueError(
            "Testen må kun køres med "
            "CURA_CREDENTIAL='API_CURA_TEST'."
        )

    if (
        not BORGER_ID
        or BORGER_ID.startswith("INDSAET_")
    ):
        raise ValueError(
            "Udfyld BORGER_ID med testborgerens "
            "tekniske Patient-id."
        )

    if (
        not FORLOEB_ID
        or FORLOEB_ID.startswith("INDSAET_")
    ):
        raise ValueError(
            "Udfyld FORLOEB_ID med id'et på det "
            "eksisterende, bestilte CarePlan-forløb."
        )

    if FORLOEB_ID.startswith("CarePlan/"):
        raise ValueError(
            "FORLOEB_ID skal angives uden "
            "'CarePlan/'."
        )

    if not LEVERANDOER_NAVN:
        raise ValueError(
            "LEVERANDOER_NAVN skal være udfyldt."
        )

    if not isinstance(
        UDFOER_OPRETTELSE,
        bool,
    ):
        raise TypeError(
            "UDFOER_OPRETTELSE skal være "
            "True eller False."
        )


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def main() -> None:
    """
    Opretter én bestilt §140-ydelse på et
    eksisterende forløb.

    Testen:

    1. Vælger API_CURA_TEST.
    2. Slår leverandørnavnet op.
    3. Bygger og kontrollerer POST-bodyen.
    4. Opretter ydelsen med ét POST-kald.
    5. Kontrollerer den genhentede ProcedureRequest.
    """
    valider_testdata()

    set_cura_credential(
        CURA_CREDENTIAL
    )

    ordered_on_datetime = (
        current_copenhagen_datetime()
    )

    print()
    print("=" * 100)
    print(
        "1. BYGGER OG KONTROLLERER YDELSEN"
    )
    print("=" * 100)
    print(
        f"Credential:       {CURA_CREDENTIAL}"
    )
    print(
        f"Borger-id:        {BORGER_ID}"
    )
    print(
        f"Forløbs-id:       {FORLOEB_ID}"
    )
    print(
        f"Ydelsesnavn:      {YDELSESNAVN}"
    )
    print(
        f"Leverandørnavn:   {LEVERANDOER_NAVN}"
    )
    print(
        f"Start:            {START_DATETIME}"
    )
    print(
        "Bestillingstid:   "
        f"{ordered_on_datetime}"
    )

    body, context = build_ydelse(
        ydelsesnavn=YDELSESNAVN,
        borger_id=BORGER_ID,
        forloeb_id=FORLOEB_ID,
        start_datetime=START_DATETIME,
        ordered_on_datetime=(
            ordered_on_datetime
        ),
        leverandoer=LEVERANDOER_NAVN,
        leverandoer_type="navn",
        opfoelgningsdato=(
            OPFOELGNINGSDATO
        ),
        opfoelgningsorganisation=(
            OPFOELGNINGSORGANISATION
        ),
        opfoelgningsorganisation_type=(
            "navn"
        ),
    )

    expected_subject = (
        f"Patient/{BORGER_ID}"
    )

    expected_pathway = (
        f"CarePlan/{FORLOEB_ID}"
    )

    expected_supplier = (
        "Organization/"
        f"{context['leverandoer']['id']}"
    )

    actual_subject = get_reference(
        body.get("subject")
    )

    actual_performer = get_reference(
        body.get("performer")
    )

    actual_pathway = get_pathway_reference(
        body
    )

    actual_variant = get_variant(
        body
    )

    if (
        body.get("resourceType")
        != "ProcedureRequest"
    ):
        raise AssertionError(
            "POST-body er ikke en "
            "ProcedureRequest."
        )

    if body.get("status") != "requested":
        raise AssertionError(
            "POST-body skal have status "
            "'requested'. "
            f"Fundet: {body.get('status')}."
        )

    if actual_subject != expected_subject:
        raise AssertionError(
            "POST-body har forkert "
            "borgerreference. "
            f"Forventet: {expected_subject}. "
            f"Fundet: {actual_subject}."
        )

    if actual_pathway != expected_pathway:
        raise AssertionError(
            "POST-body har forkert "
            "CarePlan-reference. "
            f"Forventet: {expected_pathway}. "
            f"Fundet: {actual_pathway}."
        )

    if actual_performer != expected_supplier:
        raise AssertionError(
            "POST-body har forkert "
            "leverandørreference. "
            f"Forventet: {expected_supplier}. "
            f"Fundet: {actual_performer}."
        )

    if not actual_variant:
        raise AssertionError(
            "POST-body mangler ServiceVariant."
        )

    if "id" in body:
        raise AssertionError(
            "POST-body må ikke indeholde "
            "et resource-id."
        )

    if any(
        isinstance(extension, dict)
        and str(
            extension.get("url")
            or ""
        ).endswith(
            "/previousOrderedVersions"
        )
        for extension
        in body.get("extension", [])
    ):
        raise AssertionError(
            "POST-body må ikke indeholde "
            "previousOrderedVersions."
        )

    print()
    print("Leverandør fundet:")
    print(
        "  Navn: "
        f"{context['leverandoer']['name']}"
    )
    print(
        "  ID:   "
        f"{context['leverandoer']['id']}"
    )
    print(
        f"  Ref.: {expected_supplier}"
    )
    print(
        f"Variant: {actual_variant}"
    )

    print()
    print("POST-body:")

    pprint(
        body,
        width=180,
        sort_dicts=False,
    )

    if not UDFOER_OPRETTELSE:
        print()
        print("DRY RUN BESTÅET")
        print(
            "UDFOER_OPRETTELSE=False, "
            "så der blev ikke sendt POST "
            "til CURA."
        )

        return

    print()
    print("=" * 100)
    print(
        "2. OPRETTER YDELSEN "
        "MED ÉT POST-KALD"
    )
    print("=" * 100)

    resultat = opret_ydelse(
        ydelsesnavn=YDELSESNAVN,
        borger_id=BORGER_ID,
        forloeb_id=FORLOEB_ID,
        start_datetime=START_DATETIME,
        ordered_on_datetime=(
            ordered_on_datetime
        ),
        leverandoer=LEVERANDOER_NAVN,
        leverandoer_type="navn",
        opfoelgningsdato=(
            OPFOELGNINGSDATO
        ),
        opfoelgningsorganisation=(
            OPFOELGNINGSORGANISATION
        ),
        opfoelgningsorganisation_type=(
            "navn"
        ),
        raw=False,
    )

    print()
    print("Resultat fra CURA:")

    pprint(
        resultat,
        width=180,
        sort_dicts=False,
    )

    print()
    print("=" * 100)
    print(
        "3. KONTROLLERER RESULTATET"
    )
    print("=" * 100)

    if resultat.get("success") is not True:
        raise AssertionError(
            "Resultatet har ikke success=True."
        )

    if resultat.get("verified") is not True:
        raise AssertionError(
            "Resultatet har ikke verified=True."
        )

    if resultat.get("status") != "requested":
        raise AssertionError(
            "Den gemte ydelse har ikke "
            "status 'requested'. "
            f"Fundet: {resultat.get('status')}."
        )

    if (
        resultat.get("forloeb_reference")
        != expected_pathway
    ):
        raise AssertionError(
            "Den gemte ydelse peger ikke på "
            "det forventede forløb."
        )

    if (
        resultat.get("leverandoer_reference")
        != expected_supplier
    ):
        raise AssertionError(
            "Den gemte leverandørreference "
            "matcher ikke opslaget."
        )

    ydelse_id = str(
        resultat.get("ydelse_id")
        or ""
    ).strip()

    if not ydelse_id:
        raise AssertionError(
            "Resultatet mangler ydelse_id."
        )

    print("TEST BESTÅET")
    print(
        f"Nyt ydelses-id:  {ydelse_id}"
    )
    print(
        "Ny reference:    "
        f"ProcedureRequest/{ydelse_id}"
    )
    print(
        f"Forløbsref.:     {expected_pathway}"
    )
    print(
        "Status:          requested"
    )
    print(
        "Variant:         "
        f"{resultat.get('variant')}"
    )
    print(
        "Leverandørnavn:  "
        f"{resultat.get('leverandoer_navn')}"
    )
    print(
        "Leverandørref.:  "
        f"{resultat.get('leverandoer_reference')}"
    )


if __name__ == "__main__":
    main()
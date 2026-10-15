from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.borger_forloeb_opret import (
    build_forloeb,
    hent_tilgængelige_forloebstyper,
    opret_forloeb,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA_TEST"
FORLOEBSTYPE = "genoptraeningsforloeb_140"

# Teknisk Patient-id uden "Patient/".
BORGER_ID = (
    "0f5403d0-1575-4e9c-842e-d399ff55198a"
)

# Brug ISO-tidspunkt med tidszone.
START_DATETIME = (
    "2026-10-15T00:00:00+02:00"
)

HENVIST_FRA = (
    "API-test i CURA testmiljø"
)

BEMAERKNING = (
    "Oprettet via q-cura-api test"
)

# Begge værdier skal enten være udfyldt
# eller være None.
#
# Her tester vi oprettelse UDEN opfølgning.
OPFOELGNINGSDATO = None
OPFOELGNINGSORGANISATION_ID = None


# ------------------------------------------------------------
# FASTE EXTENSION-URL'ER TIL TESTEN
# ------------------------------------------------------------

EXTENSION_FOLLOW_UP_DATE = (
    "http://curafhir.dk/x/"
    "CuraCarePlan/followUpDate"
)

EXTENSION_RESPONSIBLE_FOLLOWUP_ORGANIZATION = (
    "http://curafhir.dk/x/"
    "CuraCarePlan/"
    "responsibleFollowupOrganization"
)


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


def valider_testdata() -> None:
    """
    Kontrollerer testens obligatoriske værdier.

    Opfølgningsdato og opfølgningsorganisation
    er valgfrie.

    Begge skal dog enten være udfyldt eller
    være None.
    """
    if (
        not isinstance(BORGER_ID, str)
        or not BORGER_ID.strip()
    ):
        raise ValueError(
            "BORGER_ID skal være udfyldt."
        )

    if BORGER_ID.startswith("INDSAET_"):
        raise ValueError(
            "Udfyld BORGER_ID med testborgerens "
            "tekniske Patient-id."
        )

    if (
        not isinstance(FORLOEBSTYPE, str)
        or not FORLOEBSTYPE.strip()
    ):
        raise ValueError(
            "FORLOEBSTYPE skal være udfyldt."
        )

    if (
        not isinstance(START_DATETIME, str)
        or not START_DATETIME.strip()
    ):
        raise ValueError(
            "START_DATETIME skal være udfyldt."
        )

    if (
        not isinstance(HENVIST_FRA, str)
        or not HENVIST_FRA.strip()
    ):
        raise ValueError(
            "HENVIST_FRA skal være udfyldt."
        )

    if (
        not isinstance(BEMAERKNING, str)
        or not BEMAERKNING.strip()
    ):
        raise ValueError(
            "BEMAERKNING skal være udfyldt."
        )

    if (
        OPFOELGNINGSDATO is not None
        and not isinstance(
            OPFOELGNINGSDATO,
            str,
        )
    ):
        raise TypeError(
            "OPFOELGNINGSDATO skal være "
            "tekst eller None."
        )

    if (
        OPFOELGNINGSORGANISATION_ID is not None
        and not isinstance(
            OPFOELGNINGSORGANISATION_ID,
            str,
        )
    ):
        raise TypeError(
            "OPFOELGNINGSORGANISATION_ID "
            "skal være tekst eller None."
        )

    har_opfoelgningsdato = bool(
        OPFOELGNINGSDATO
        and OPFOELGNINGSDATO.strip()
    )

    har_opfoelgningsorganisation = bool(
        OPFOELGNINGSORGANISATION_ID
        and OPFOELGNINGSORGANISATION_ID.strip()
    )

    if (
        har_opfoelgningsdato
        != har_opfoelgningsorganisation
    ):
        raise ValueError(
            "Opfølgning skal enten have både "
            "OPFOELGNINGSDATO og "
            "OPFOELGNINGSORGANISATION_ID "
            "eller ingen af delene."
        )

    if (
        har_opfoelgningsorganisation
        and OPFOELGNINGSORGANISATION_ID.startswith(
            "INDSAET_"
        )
    ):
        raise ValueError(
            "Udfyld "
            "OPFOELGNINGSORGANISATION_ID "
            "eller brug None."
        )


def kontroller_post_body(
    body: dict,
) -> None:
    """
    Kontrollerer POST-bodyen, før testen
    skriver til CURA.
    """
    if body.get("resourceType") != "CarePlan":
        raise AssertionError(
            "POST-body er ikke en CarePlan."
        )

    expected_subject = (
        f"Patient/{BORGER_ID}"
    )

    subject = body.get("subject")

    actual_subject = (
        subject.get("reference")
        if isinstance(subject, dict)
        else None
    )

    if actual_subject != expected_subject:
        raise AssertionError(
            "POST-body peger ikke på den "
            "forventede borger. "
            f"Forventet: {expected_subject}. "
            f"Fundet: {actual_subject}."
        )

    period = body.get("period")

    actual_start = (
        period.get("start")
        if isinstance(period, dict)
        else None
    )

    if actual_start != START_DATETIME:
        raise AssertionError(
            "POST-body har forkert startdato. "
            f"Forventet: {START_DATETIME}. "
            f"Fundet: {actual_start}."
        )

    if "id" in body:
        raise AssertionError(
            "POST-body må ikke indeholde id."
        )

    meta = body.get("meta")

    if not isinstance(meta, dict):
        meta = {}

    for server_field in (
        "versionId",
        "lastUpdated",
        "extension",
    ):
        if server_field in meta:
            raise AssertionError(
                "POST-body må ikke indeholde "
                f"meta.{server_field}."
            )

    follow_up_date = find_extension(
        body,
        EXTENSION_FOLLOW_UP_DATE,
    )

    follow_up_organization = find_extension(
        body,
        EXTENSION_RESPONSIBLE_FOLLOWUP_ORGANIZATION,
    )

    if (
        OPFOELGNINGSDATO is None
        and follow_up_date is not None
    ):
        raise AssertionError(
            "followUpDate skulle være fjernet "
            "fra POST-bodyen."
        )

    if (
        OPFOELGNINGSORGANISATION_ID is None
        and follow_up_organization is not None
    ):
        raise AssertionError(
            "responsibleFollowupOrganization "
            "skulle være fjernet fra POST-bodyen."
        )


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def main() -> None:
    """
    Opretter Genoptræningsforløb §140
    i CURA-testmiljøet.

    Testen foretager et rigtigt POST-kald
    og opretter ét forløb.
    """
    valider_testdata()

    tilgaengelige_forloebstyper = (
        hent_tilgængelige_forloebstyper()
    )

    if (
        FORLOEBSTYPE
        not in tilgaengelige_forloebstyper
    ):
        raise AssertionError(
            f"Forløbstypen {FORLOEBSTYPE!r} "
            "er ikke registreret. "
            "Tilgængelige typer: "
            f"{tilgaengelige_forloebstyper}"
        )

    print()
    print("=" * 100)
    print(
        "1. BYGGER OG KONTROLLERER POST-BODY"
    )
    print("=" * 100)
    print(f"Credential:   {CURA_CREDENTIAL}")
    print(f"Forløbstype:  {FORLOEBSTYPE}")
    print(f"Borger-id:    {BORGER_ID}")
    print(f"Start:        {START_DATETIME}")
    print("Opfølgning:   Nej")

    body = build_forloeb(
        forloebstype=FORLOEBSTYPE,
        borger_id=BORGER_ID,
        start_datetime=START_DATETIME,
        henvist_fra=HENVIST_FRA,
        bemaerkning=BEMAERKNING,
        opfoelgningsdato=(
            OPFOELGNINGSDATO
        ),
        opfoelgningsorganisation_id=(
            OPFOELGNINGSORGANISATION_ID
        ),
    )

    kontroller_post_body(
        body
    )

    pprint(
        body,
        width=180,
        sort_dicts=False,
    )

    print()
    print(
        "POST-body er kontrolleret og "
        "indeholder ingen opfølgning."
    )

    print()
    print("=" * 100)
    print(
        "2. OPRETTER FORLØBET I CURA TEST"
    )
    print("=" * 100)

    set_cura_credential(
        CURA_CREDENTIAL
    )

    resultat = opret_forloeb(
        forloebstype=FORLOEBSTYPE,
        borger_id=BORGER_ID,
        start_datetime=START_DATETIME,
        henvist_fra=HENVIST_FRA,
        bemaerkning=BEMAERKNING,
        opfoelgningsdato=(
            OPFOELGNINGSDATO
        ),
        opfoelgningsorganisation_id=(
            OPFOELGNINGSORGANISATION_ID
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
        "3. KONTROLLERER DET OPRETTEDE FORLØB"
    )
    print("=" * 100)

    if not isinstance(resultat, dict):
        raise AssertionError(
            "Resultatet fra opret_forloeb "
            "er ikke en dictionary."
        )

    forloeb_id = str(
        resultat.get("forloeb_id")
        or ""
    ).strip()

    if not forloeb_id:
        raise AssertionError(
            "Resultatet mangler forloeb_id."
        )

    expected_borger_reference = (
        f"Patient/{BORGER_ID}"
    )

    if (
        resultat.get("borger_reference")
        != expected_borger_reference
    ):
        raise AssertionError(
            "Forløbet peger ikke på den "
            "forventede testborger. "
            f"Forventet: {expected_borger_reference}. "
            "Fundet: "
            f"{resultat.get('borger_reference')}."
        )

    if resultat.get("status") != "proposed":
        raise AssertionError(
            "Forløbet har ikke status 'proposed'. "
            f"Fundet: {resultat.get('status')}."
        )

    period = resultat.get("period")

    if not isinstance(period, dict):
        raise AssertionError(
            "Resultatet mangler en gyldig "
            "period-dictionary."
        )

    if period.get("start") != START_DATETIME:
        raise AssertionError(
            "Forløbets startdato matcher ikke input. "
            f"Forventet: {START_DATETIME}. "
            f"Fundet: {period.get('start')}."
        )

    raw_resource = resultat.get(
        "raw_resource"
    )

    if not isinstance(raw_resource, dict):
        raise AssertionError(
            "Resultatet mangler raw_resource."
        )

    if (
        find_extension(
            raw_resource,
            EXTENSION_FOLLOW_UP_DATE,
        )
        is not None
    ):
        raise AssertionError(
            "Det oprettede forløb indeholder "
            "uventet followUpDate."
        )

    if (
        find_extension(
            raw_resource,
            EXTENSION_RESPONSIBLE_FOLLOWUP_ORGANIZATION,
        )
        is not None
    ):
        raise AssertionError(
            "Det oprettede forløb indeholder "
            "uventet "
            "responsibleFollowupOrganization."
        )

    print("TEST BESTÅET")
    print(
        f"Nyt forløbs-id: {forloeb_id}"
    )
    print(
        "Ny reference:   "
        f"CarePlan/{forloeb_id}"
    )
    print(
        "Opfølgning:     Ikke angivet"
    )

    print()
    print(
        "Gem forløbs-id'et. Det skal bruges i "
        "næste test, når ydelsen skal oprettes "
        "på dette forløb."
    )


if __name__ == "__main__":
    main()
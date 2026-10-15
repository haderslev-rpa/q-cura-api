import json
from pathlib import Path
from pprint import pprint

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# KONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA_TEST"

FORLOEB_ID = (
    "07ca5b1e-0814-4259-89e0-59093fd029bb"
)

OUTPUT_FOLDER = Path(
    "tests/testdata"
)

OUTPUT_FILE = (
    OUTPUT_FOLDER
    / "careplan_raw_reference.json"
)


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------


def main():
    """
    Henter hele CarePlan-ressourcen fra CURA.

    Testen udfører kun ét GET-kald.
    Ressourcen ændres ikke.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    endpoint = (
        f"CarePlan/{FORLOEB_ID}"
    )

    print()
    print("=" * 100)
    print("HENT RAW CAREPLAN")
    print("=" * 100)
    print(f"Credential: {CURA_CREDENTIAL}")
    print(f"Endpoint:   {endpoint}")

    raw_forloeb = get(
        endpoint,
        raw=True,
    )

    if not isinstance(raw_forloeb, dict):
        raise TypeError(
            "CURA returnerede ikke en dictionary."
        )

    if (
        raw_forloeb.get("resourceType")
        != "CarePlan"
    ):
        raise ValueError(
            "Den hentede resource er ikke "
            "en CarePlan."
        )

    faktisk_id = str(
        raw_forloeb.get("id")
        or ""
    )

    if faktisk_id != FORLOEB_ID:
        raise AssertionError(
            "Det returnerede CarePlan-id matcher "
            "ikke det forventede id. "
            f"Forventet: {FORLOEB_ID}. "
            f"Fundet: {faktisk_id}."
        )

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            raw_forloeb,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("-" * 100)
    print("RAW CAREPLAN")
    print("-" * 100)

    pprint(
        raw_forloeb,
        width=180,
        sort_dicts=False,
    )

    print()
    print("=" * 100)
    print("RAW CAREPLAN GEMT")
    print("=" * 100)
    print(OUTPUT_FILE)
    print()
    print(
        "Der blev kun udført ét GET-kald. "
        "Intet blev ændret i CURA."
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from pprint import pprint
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# KONFIGURATION
# ------------------------------------------------------------
PROFILE = (
    "http://curafhir.dk/p/"
    "MedcomCareCommunication"
)

CURA_CREDENTIAL = "API_CURA"

DAYS_BACK = 3

COPENHAGEN_TIMEZONE = ZoneInfo(
    "Europe/Copenhagen"
)


# ------------------------------------------------------------
# TIDSPERIODE
# ------------------------------------------------------------
def get_received_period() -> tuple[datetime, datetime]:
    """
    Beregner perioden fra nu og tre døgn tilbage.

    Output:
        Tuple med:
        - periodens inkluderede starttidspunkt
        - periodens inkluderede sluttidspunkt

    Begge tidspunkter har dansk tidszone.
    """
    received_to = datetime.now(
        COPENHAGEN_TIMEZONE
    )

    received_from = (
        received_to
        - timedelta(days=DAYS_BACK)
    )

    return (
        received_from,
        received_to,
    )


def format_cura_datetime(
    value: datetime,
) -> str:
    """
    Formaterer et datetime-objekt til ISO-format til CURA.

    Eksempel:
        2026-10-03T15:30:00+02:00

    Mikrosekunder fjernes for at holde URL'en læsevenlig.
    """
    return value.replace(
        microsecond=0
    ).isoformat()


# ------------------------------------------------------------
# ENDPOINT
# ------------------------------------------------------------
def build_endpoint(
    received_from: datetime,
    received_to: datetime,
) -> str:
    """
    Bygger CURA-endpointet.

    Der søges:
        - på MedcomCareCommunication-profilen
        - fra tre døgn tilbage
        - til det aktuelle tidspunkt
        - uden borgerfilter

    De to received-parametre betyder:
        received >= received_from
        received <= received_to
    """
    query_parameters = [
        (
            "_profile",
            PROFILE,
        ),
        (
            "received",
            (
                "ge"
                + format_cura_datetime(
                    received_from
                )
            ),
        ),
        (
            "received",
            (
                "le"
                + format_cura_datetime(
                    received_to
                )
            ),
        ),
        (
            "_count",
            "1000",
        ),
    ]

    return (
        "Communication?"
        + urlencode(
            query_parameters,
            doseq=True,
        )
    )


# ------------------------------------------------------------
# BUNDLE-HJÆLPERE
# ------------------------------------------------------------
def get_bundle_entries(
    bundle: dict,
) -> list:
    """
    Henter Bundle.entry som en sikker liste.

    Output:
        Liste med entries.

        Returnerer en tom liste, hvis Bundle.entry mangler
        eller ikke er en liste.
    """
    if not isinstance(bundle, dict):
        return []

    entries = bundle.get(
        "entry",
        [],
    )

    if not isinstance(entries, list):
        return []

    return entries


# ------------------------------------------------------------
# FJERN LANGT BESKEDINDHOLD
# ------------------------------------------------------------
def remove_content_strings(
    value,
):
    """
    Returnerer en kopi uden felter med navnet contentString.

    Funktionen gennemgår rekursivt:
        - dictionaries
        - lister

    Andre felter bevares uændret.

    Det oprindelige API-svar bliver ikke ændret.
    """
    if isinstance(value, dict):
        cleaned_dictionary = {}

        for key, child_value in value.items():
            if key == "contentString":
                continue

            cleaned_dictionary[key] = (
                remove_content_strings(
                    child_value
                )
            )

        return cleaned_dictionary

    if isinstance(value, list):
        return [
            remove_content_strings(item)
            for item in value
        ]

    return value


def get_payload_without_content(
    resource: dict,
) -> list:
    """
    Henter payload-metadata uden contentString.

    Eksempel på output:
        [
            {
                "id": "payload-id"
            }
        ]

    Hvis payload kun indeholder contentString, bliver der
    returneret en tom dictionary for det pågældende element.
    """
    payload = resource.get(
        "payload",
        [],
    )

    if not isinstance(payload, list):
        return []

    cleaned_payload = (
        remove_content_strings(
            payload
        )
    )

    return [
        payload_item
        for payload_item in cleaned_payload
        if isinstance(payload_item, dict)
        and payload_item
    ]


# ------------------------------------------------------------
# EXTENSIONS
# ------------------------------------------------------------
def get_extension_name(
    extension: dict,
) -> str:
    """
    Henter det sidste navn fra extensionens URL.

    Eksempel:
        http://.../careCommunicationType

    bliver til:
        careCommunicationType
    """
    extension_url = str(
        extension.get("url")
        or ""
    ).strip()

    if not extension_url:
        return ""

    return extension_url.rstrip(
        "/"
    ).split("/")[-1]


def get_extension_value(
    extension: dict,
):
    """
    Henter den første value-værdi fra en FHIR-extension.

    Funktionen understøtter blandt andet:
        - valueString
        - valueCode
        - valueBoolean
        - valueDateTime
        - valueReference
        - valueCodeableConcept

    Output:
        Den fundne værdi.

        Returnerer tom tekst, hvis ingen value-værdi findes.
    """
    if not isinstance(extension, dict):
        return ""

    for key, value in extension.items():
        if key.startswith("value"):
            return value

    nested_extensions = extension.get(
        "extension"
    )

    if isinstance(nested_extensions, list):
        return remove_content_strings(
            nested_extensions
        )

    return ""


def get_extensions_summary(
    resource: dict,
) -> dict:
    """
    Laver en overskuelig dictionary over alle extensions.

    Outputeksempel:
        {
            "careCommunicationSubject": {
                "url": "...",
                "value": "Indlagt korrespondance"
            },
            "careCommunicationStatus": {
                "url": "...",
                "value": "new"
            }
        }

    contentString fjernes, hvis det mod forventning findes
    inde i en extension.
    """
    extensions = resource.get(
        "extension",
        [],
    )

    if not isinstance(extensions, list):
        return {}

    result = {}

    for extension_number, extension in enumerate(
        extensions,
        start=1,
    ):
        if not isinstance(extension, dict):
            continue

        extension_name = get_extension_name(
            extension
        )

        if not extension_name:
            extension_name = (
                f"ukendt_extension_"
                f"{extension_number}"
            )

        # Bevar begge, hvis samme extensionnavn forekommer
        # flere gange.
        unique_name = extension_name

        duplicate_number = 2

        while unique_name in result:
            unique_name = (
                f"{extension_name}_"
                f"{duplicate_number}"
            )

            duplicate_number += 1

        result[unique_name] = {
            "url": extension.get(
                "url",
                "",
            ),
            "value": remove_content_strings(
                get_extension_value(
                    extension
                )
            ),
        }

    return result


# ------------------------------------------------------------
# CATEGORY
# ------------------------------------------------------------
def get_category_summary(
    resource: dict,
) -> list:
    """
    Henter category i et enkelt og læsevenligt format.

    Outputeksempel:
        [
            {
                "system": "...categoryCodes",
                "code": "other",
                "display": "Andet"
            }
        ]
    """
    category = resource.get(
        "category"
    )

    if isinstance(category, dict):
        categories = [
            category
        ]

    elif isinstance(category, list):
        categories = category

    else:
        return []

    result = []

    for category_item in categories:
        if not isinstance(
            category_item,
            dict,
        ):
            continue

        coding_list = category_item.get(
            "coding",
            [],
        )

        if not isinstance(coding_list, list):
            coding_list = []

        if not coding_list:
            result.append(
                {
                    "text": category_item.get(
                        "text",
                        "",
                    ),
                }
            )

            continue

        for coding in coding_list:
            if not isinstance(coding, dict):
                continue

            result.append(
                {
                    "system": coding.get(
                        "system",
                        "",
                    ),
                    "code": coding.get(
                        "code",
                        "",
                    ),
                    "display": coding.get(
                        "display",
                        "",
                    ),
                    "text": category_item.get(
                        "text",
                        "",
                    ),
                }
            )

    return result


# ------------------------------------------------------------
# RESTERENDE FELTER
# ------------------------------------------------------------
def get_other_resource_fields(
    resource: dict,
) -> dict:
    """
    Henter alle øvrige felter på Communication-resource.

    Felter, som allerede vises særskilt, udelades.

    payload.contentString fjernes altid.
    """
    excluded_fields = {
        "resourceType",
        "id",
        "meta",
        "received",
        "sent",
        "category",
        "subject",
        "sender",
        "recipient",
        "extension",
        "payload",
    }

    other_fields = {}

    for key, value in resource.items():
        if key in excluded_fields:
            continue

        other_fields[key] = (
            remove_content_strings(
                deepcopy(value)
            )
        )

    return other_fields


# ------------------------------------------------------------
# UDSKRIFT AF ÉN BESKED
# ------------------------------------------------------------
def print_message_summary(
    resource: dict,
    message_number: int,
    total_messages: int,
) -> None:
    """
    Udskriver én Communication-resource uden contentString.

    Der vises:
        - ID
        - profil
        - modtaget og sendt
        - category
        - subject
        - sender
        - recipient
        - alle extensions
        - eventuel payload-metadata
        - øvrige resource-felter

    Selve beskedens lange HTML-indhold vises ikke.
    """
    meta = resource.get(
        "meta",
        {},
    )

    if not isinstance(meta, dict):
        meta = {}

    print("")
    print("-" * 100)
    print(
        f"BESKED {message_number} "
        f"AF {total_messages}"
    )
    print("-" * 100)

    message_summary = {
        "id": resource.get(
            "id",
            "",
        ),
        "profiles": meta.get(
            "profile",
            [],
        ),
        "received": resource.get(
            "received",
            "",
        ),
        "sent": resource.get(
            "sent",
            "",
        ),
        "category": get_category_summary(
            resource
        ),
        "subject": resource.get(
            "subject",
            {},
        ),
        "sender": resource.get(
            "sender",
            {},
        ),
        "recipient": resource.get(
            "recipient",
            [],
        ),
        "extensions": get_extensions_summary(
            resource
        ),
    }

    payload_without_content = (
        get_payload_without_content(
            resource
        )
    )

    if payload_without_content:
        message_summary[
            "payload_uden_contentString"
        ] = payload_without_content

    other_fields = get_other_resource_fields(
        resource
    )

    if other_fields:
        message_summary[
            "øvrige_felter"
        ] = other_fields

    pprint(
        message_summary,
        width=180,
        sort_dicts=False,
    )


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------
def main() -> None:
    """
    Henter indgående MedCom-beskeder fra de seneste tre døgn.

    Der bruges:
        - driftsmiljø
        - intet borgerfilter
        - MedcomCareCommunication-profil
        - received-periode

    contentString bliver ikke udskrevet.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    (
        received_from,
        received_to,
    ) = get_received_period()

    endpoint = build_endpoint(
        received_from=received_from,
        received_to=received_to,
    )

    print("")
    print("=" * 100)
    print("HENTER INDGÅENDE MEDCOM-BESKEDER")
    print("=" * 100)
    print(
        f"Miljø:           {CURA_CREDENTIAL}"
    )
    print(
        f"Antal døgn:      {DAYS_BACK}"
    )
    print(
        "Fra:             "
        + format_cura_datetime(
            received_from
        )
    )
    print(
        "Til:             "
        + format_cura_datetime(
            received_to
        )
    )
    print(
        f"Profil:          {PROFILE}"
    )
    print(
        "Borgerfilter:    Nej"
    )
    print(
        "contentString:   Udskrives ikke"
    )
    print("")
    print(
        f"Endpoint: {endpoint}"
    )

    bundle = get(
        endpoint,
        raw=True,
    )

    entries = get_bundle_entries(
        bundle
    )

    communication_resources = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        resource = entry.get(
            "resource",
            {},
        )

        if not isinstance(resource, dict):
            continue

        if (
            resource.get("resourceType")
            != "Communication"
        ):
            continue

        communication_resources.append(
            resource
        )

    communication_resources.sort(
        key=lambda resource: str(
            resource.get("received")
            or resource.get("sent")
            or ""
        ),
        reverse=True,
    )

    print("")
    print("=" * 100)
    print("RESULTAT")
    print("=" * 100)
    print(
        "Bundle total:    "
        f"{bundle.get('total')}"
    )
    print(
        "Antal entries:   "
        f"{len(entries)}"
    )
    print(
        "Communication:   "
        f"{len(communication_resources)}"
    )

    if not communication_resources:
        print("")
        print(
            "Der blev ikke fundet indgående "
            "MedCom-beskeder i perioden."
        )
        return

    for message_number, resource in enumerate(
        communication_resources,
        start=1,
    ):
        print_message_summary(
            resource=resource,
            message_number=message_number,
            total_messages=len(
                communication_resources
            ),
        )

    print("")
    print("=" * 100)
    print("TESTEN ER FÆRDIG")
    print("=" * 100)
    print(
        "contentString blev ikke udskrevet."
    )


if __name__ == "__main__":
    main()
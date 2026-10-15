from __future__ import annotations

from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


# ------------------------------------------------------------
# TESTKONFIGURATION
# ------------------------------------------------------------

CURA_CREDENTIAL = "API_CURA"

BORGER_ID = (
    "39dde427-b1fc-42b3-9e85-fccf727ee3bf"
)

COUNT = 1000

MESSAGE_PROFILES = {
    "genoptraeningsplan": (
        "http://curafhir.dk/p/"
        "CuraRehabilitationPlan"
    ),
    "plejekommunikation": (
        "http://curafhir.dk/p/"
        "MedcomCareCommunication"
    ),
    "digital_post": (
        "http://curafhir.dk/p/"
        "DigitalPostInboundCommunication"
    ),
}


# ------------------------------------------------------------
# BUNDLE-HJÆLPERE
# ------------------------------------------------------------

def get_bundle_entries(
    bundle: dict,
) -> list:
    """
    Returnerer Bundle.entry som en sikker liste.

    Output:
        En liste med entries.

        Hvis CURA ikke returnerer et Bundle med entries,
        returneres en tom liste.
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


def get_bundle_link_relations(
    bundle: dict,
) -> list:
    """
    Henter relationstyperne fra Bundle.link.

    Eksempler:
        self
        next
        previous

    URL'erne udskrives ikke.
    """
    if not isinstance(bundle, dict):
        return []

    links = bundle.get(
        "link",
        [],
    )

    if not isinstance(links, list):
        return []

    relations = []

    for link in links:
        if not isinstance(link, dict):
            continue

        relation = str(
            link.get("relation")
            or ""
        ).strip()

        if relation:
            relations.append(relation)

    return relations


def get_communication_resources(
    bundle: dict,
) -> list:
    """
    Henter alle Communication-resurser fra Bundle.entry.

    Output:
        Liste med rå Communication-resurser.
    """
    resources = []

    for entry in get_bundle_entries(
        bundle
    ):
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

        resources.append(resource)

    return resources


# ------------------------------------------------------------
# FELTHJÆLPERE
# ------------------------------------------------------------

def get_reference(
    reference_data,
) -> str:
    """
    Henter en FHIR-reference.

    Eksempel:
        {
            "reference": "Patient/123"
        }

    bliver til:

        "Patient/123"
    """
    if isinstance(reference_data, str):
        return reference_data.strip()

    if isinstance(reference_data, dict):
        return str(
            reference_data.get("reference")
            or ""
        ).strip()

    return ""


def get_profiles(
    resource: dict,
) -> list:
    """
    Henter resource.meta.profile som en sikker liste.
    """
    meta = resource.get(
        "meta",
        {},
    )

    if not isinstance(meta, dict):
        return []

    profiles = meta.get(
        "profile",
        [],
    )

    if not isinstance(profiles, list):
        return []

    return profiles


def get_identifiers(
    resource: dict,
) -> list:
    """
    Henter beskedens identifiers uden beskedindhold.

    Output:
        [
            {
                "system": "...",
                "value": "...",
            }
        ]
    """
    identifiers = resource.get(
        "identifier",
        [],
    )

    if not isinstance(identifiers, list):
        return []

    result = []

    for identifier in identifiers:
        if not isinstance(identifier, dict):
            continue

        result.append(
            {
                "system": str(
                    identifier.get("system")
                    or ""
                ),
                "value": str(
                    identifier.get("value")
                    or ""
                ),
            }
        )

    return result


def get_payload_ids(
    resource: dict,
) -> list:
    """
    Henter kun id fra payload-elementerne.

    contentString returneres og udskrives ikke.
    """
    payload = resource.get(
        "payload",
        [],
    )

    if not isinstance(payload, list):
        return []

    payload_ids = []

    for payload_item in payload:
        if not isinstance(
            payload_item,
            dict,
        ):
            continue

        payload_id = str(
            payload_item.get("id")
            or ""
        ).strip()

        if payload_id:
            payload_ids.append(
                payload_id
            )

    return payload_ids


# ------------------------------------------------------------
# NORMALISER KUN TIL TESTUDSKRIFT
# ------------------------------------------------------------

def build_message_summary(
    resource: dict,
    profile_name: str,
) -> dict:
    """
    Bygger en sikker oversigt over én Communication.

    Beskedens payload.contentString medtages ikke.

    Output:
        Dictionary med id, datoer, profiler, afsender,
        borgerreference og identifiers.
    """
    communication_id = str(
        resource.get("id")
        or ""
    ).strip()

    return {
        "communication_id": communication_id,
        "communication_reference": (
            f"Communication/{communication_id}"
            if communication_id
            else ""
        ),
        "profile_name": profile_name,
        "profiles": get_profiles(
            resource
        ),
        "sent": str(
            resource.get("sent")
            or ""
        ),
        "received": str(
            resource.get("received")
            or ""
        ),
        "subject_reference": get_reference(
            resource.get("subject")
        ),
        "sender_reference": get_reference(
            resource.get("sender")
        ),
        "identifiers": get_identifiers(
            resource
        ),
        "payload_ids": get_payload_ids(
            resource
        ),
        "last_updated": str(
            (
                resource.get(
                    "meta",
                    {},
                )
                if isinstance(
                    resource.get("meta"),
                    dict,
                )
                else {}
            ).get(
                "lastUpdated",
                "",
            )
            or ""
        ),
    }


# ------------------------------------------------------------
# BYG ENDPOINT
# ------------------------------------------------------------

def build_endpoint(
    profile: str,
) -> str:
    """
    Bygger et læsende Communication-opslag for:

        én profil
        én borger
        maksimalt COUNT beskeder

    Der anvendes ingen datobegrænsning, så gamle beskeder
    også kan blive returneret.
    """
    return (
        "Communication?"
        + urlencode(
            [
                (
                    "_profile",
                    profile,
                ),
                (
                    "subject",
                    f"Patient/{BORGER_ID}",
                ),
                (
                    "_count",
                    str(COUNT),
                ),
            ],
            doseq=True,
        )
    )


# ------------------------------------------------------------
# HENT ÉN BESKEDPROFIL
# ------------------------------------------------------------

def get_messages_for_profile(
    profile_name: str,
    profile: str,
) -> dict:
    """
    Henter beskeder for én Communication-profil.

    Funktionen udfører kun GET.

    En fejl gemmes i resultatet, så testen kan fortsætte
    med de øvrige profiler.
    """
    endpoint = build_endpoint(
        profile
    )

    print()
    print("=" * 100)
    print(
        "HENTER BESKEDPROFIL: "
        f"{profile_name}"
    )
    print("=" * 100)
    print(f"Profil:   {profile}")
    print(f"Endpoint: {endpoint}")

    try:
        bundle = get(
            endpoint,
            raw=True,
        )

    except Exception as error:
        print()
        print("Opslaget fejlede.")
        print(
            f"Fejltype: "
            f"{type(error).__name__}"
        )
        print(str(error))

        return {
            "profile_name": profile_name,
            "profile": profile,
            "endpoint": endpoint,
            "error": str(error),
            "bundle_total": None,
            "entry_count": 0,
            "link_relations": [],
            "has_next": False,
            "messages": [],
        }

    resources = (
        get_communication_resources(
            bundle
        )
    )

    messages = [
        build_message_summary(
            resource=resource,
            profile_name=profile_name,
        )
        for resource in resources
    ]

    link_relations = (
        get_bundle_link_relations(
            bundle
        )
    )

    print()
    print(
        "Bundle total:  "
        f"{bundle.get('total')}"
    )
    print(
        "Antal entries: "
        f"{len(get_bundle_entries(bundle))}"
    )
    print(
        "Communication: "
        f"{len(messages)}"
    )
    print(
        "Linktyper:     "
        f"{link_relations}"
    )

    if "next" in link_relations:
        print()
        print(
            "ADVARSEL: CURA har angivet et next-link."
        )
        print(
            "Denne test viser derfor kun den aktuelle side."
        )

    return {
        "profile_name": profile_name,
        "profile": profile,
        "endpoint": endpoint,
        "error": "",
        "bundle_total": bundle.get(
            "total"
        ),
        "entry_count": len(
            get_bundle_entries(bundle)
        ),
        "link_relations": link_relations,
        "has_next": (
            "next" in link_relations
        ),
        "messages": messages,
    }


# ------------------------------------------------------------
# TEST
# ------------------------------------------------------------

def main():
    """
    Henter beskeder for én borger fra de kendte
    Communication-profiler.

    Testen:

        - udfører kun GET
        - søger uden datobegrænsning
        - udskriver ikke contentString
        - sorterer beskeder med nyeste først
        - fjerner dubletter med samme Communication.id
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    print()
    print("=" * 100)
    print("BESKEDER FOR BORGER")
    print("=" * 100)
    print(f"Miljø:    {CURA_CREDENTIAL}")
    print(f"Borger:   {BORGER_ID}")
    print(f"Maksimum: {COUNT} pr. profil")
    print(
        "Indhold:   payload.contentString "
        "udskrives ikke"
    )

    messages_by_id = {}
    profile_results = []

    for (
        profile_name,
        profile,
    ) in MESSAGE_PROFILES.items():
        profile_result = (
            get_messages_for_profile(
                profile_name=profile_name,
                profile=profile,
            )
        )

        profile_results.append(
            profile_result
        )

        for message in profile_result.get(
            "messages",
            [],
        ):
            communication_id = str(
                message.get(
                    "communication_id"
                )
                or ""
            )

            if not communication_id:
                continue

            messages_by_id[
                communication_id
            ] = message

    messages = list(
        messages_by_id.values()
    )

    messages.sort(
        key=lambda message: str(
            message.get("received")
            or message.get("sent")
            or message.get("last_updated")
            or ""
        ),
        reverse=True,
    )

    print()
    print("=" * 100)
    print("SAMLET OVERSIGT")
    print("=" * 100)
    print(
        "Antal unikke beskeder: "
        f"{len(messages)}"
    )

    if not messages:
        print()
        print(
            "Der blev ikke fundet beskeder for "
            "borgeren med de afprøvede profiler."
        )

    for number, message in enumerate(
        messages,
        start=1,
    ):
        print()
        print("-" * 100)
        print(
            f"BESKED {number} "
            f"AF {len(messages)}"
        )
        print("-" * 100)

        pprint(
            message,
            width=180,
            sort_dicts=False,
        )

    incomplete_profiles = [
        result.get("profile_name")
        for result in profile_results
        if result.get("has_next")
    ]

    print()
    print("=" * 100)
    print("TESTEN ER FÆRDIG")
    print("=" * 100)
    print(
        "Der blev kun udført GET-kald."
    )
    print(
        "Ingen beskeder eller andre ressourcer "
        "blev ændret."
    )

    if incomplete_profiles:
        print()
        print(
            "Disse profiler havde flere sider:"
        )

        pprint(
            incomplete_profiles,
            width=120,
            sort_dicts=False,
        )


if __name__ == "__main__":
    main()
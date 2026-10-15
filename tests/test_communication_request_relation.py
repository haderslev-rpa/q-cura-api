from pprint import pprint
from urllib.parse import urlencode

from q_cura_api.api_client import (
    get,
    set_cura_credential,
)


CURA_CREDENTIAL = "API_CURA"

BORGER_ID = (
    "b8fd9b01-5d85-4794-"
    "b1a7-5cd3c8e27a03"
)

BESKED_ID = (
    "de4cc915-353e-4011-"
    "995a-5e1c069502c4"
)


def run_search(
    title: str,
    parameter_name: str,
    parameter_value: str,
):
    """
    Udfører ét råt GET-opslag.

    Fejl på ét opslag stopper ikke de næste opslag.
    """
    endpoint = (
        "CommunicationRequest?"
        + urlencode(
            [
                (
                    parameter_name,
                    parameter_value,
                ),
            ]
        )
    )

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(f"Endpoint: {endpoint}")
    print()

    try:
        result = get(
            endpoint,
            raw=True,
        )

    except Exception as error:
        print("OPSLAGET FEJLEDE")
        print(
            f"{type(error).__name__}: {error}"
        )
        return None

    pprint(
        result,
        width=200,
        sort_dicts=False,
    )

    return result


def main():
    """
    Undersøger CommunicationRequest som mulig
    relationsresource.

    Testen udfører kun GET-kald.
    """
    set_cura_credential(
        CURA_CREDENTIAL
    )

    communication_reference = (
        f"Communication/{BESKED_ID}"
    )

    patient_reference = (
        f"Patient/{BORGER_ID}"
    )

    # Mest sandsynlige direkte kobling.
    run_search(
        title=(
            "COMMUNICATIONREQUEST VIA "
            "ORIGINAL COMMUNICATION"
        ),
        parameter_name=(
            "originalCommunication"
        ),
        parameter_value=(
            communication_reference
        ),
    )

    # Mulig årsagsreference.
    run_search(
        title=(
            "COMMUNICATIONREQUEST VIA "
            "REASON REFERENCE"
        ),
        parameter_name=(
            "reasonReference"
        ),
        parameter_value=(
            communication_reference
        ),
    )

    # Mulig detaljerelation.
    run_search(
        title=(
            "COMMUNICATIONREQUEST VIA "
            "REQUEST DETAIL"
        ),
        parameter_name=(
            "requestDetail"
        ),
        parameter_value=(
            communication_reference
        ),
    )

    # Mulig henvisningskilde.
    run_search(
        title=(
            "COMMUNICATIONREQUEST VIA "
            "REFERRAL SOURCE"
        ),
        parameter_name=(
            "referralSource"
        ),
        parameter_value=(
            communication_reference
        ),
    )

    # Alle CommunicationRequests for borgeren.
    run_search(
        title=(
            "COMMUNICATIONREQUEST VIA BORGER"
        ),
        parameter_name="subject",
        parameter_value=patient_reference,
    )

    print()
    print("=" * 100)
    print("TESTEN ER FÆRDIG")
    print("=" * 100)
    print(
        "Der blev kun udført GET-kald."
    )


if __name__ == "__main__":
    main()
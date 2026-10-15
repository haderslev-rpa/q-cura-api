from copy import deepcopy
from pprint import pprint

from q_cura_api.api_client import set_cura_credential
from q_cura_api.functionality.opgaver import get_tasks_for_citizen


BORGER_ID = "b8fd9b01-5d85-4794-b1a7-5cd3c8e27a03"
CONTENT_PREVIEW_LENGTH = 50


def _shorten_content_for_print(value):
    """Forkorter kun content_strings/contentString i testens printkopi."""
    if isinstance(value, dict):
        return {
            key: (
                [str(item)[:CONTENT_PREVIEW_LENGTH] for item in child]
                if key == "content_strings" and isinstance(child, list)
                else str(child)[:CONTENT_PREVIEW_LENGTH]
                if key == "contentString"
                else _shorten_content_for_print(child)
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_shorten_content_for_print(item) for item in value]
    return value


def main():
    set_cura_credential("API_CURA")

    result = get_tasks_for_citizen(
        BORGER_ID,
        raw=False,
    )

    pprint(
        _shorten_content_for_print(deepcopy(result)),
        width=180,
        sort_dicts=False,
    )


if __name__ == "__main__":
    main()

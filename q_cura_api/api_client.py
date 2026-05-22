import time  # modul (tid)
import requests  # modul (HTTP-kald)

from automation_server_client import AutomationServer, Credential  # klasse (AS-klient)

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()
credential = Credential.get_credential("API_CURA")

cfg = credential.data

# -------------------------------------------------
# Konfiguration (matcher Blue Prism)
# -------------------------------------------------
BASE_URL = cfg["base_url"]

ACCESS_TOKEN_URL = cfg["access_token_url"]
AUTH_USERINFO_URL = cfg["auth_userinfo"]
SESSION_TOKEN_URL = cfg["session_token_url"]

ORG_ID = cfg["org_id"]
USER_ROLE = cfg["user_role"]
API_VERSION = cfg["api_version"]

CURA_API_KEY = cfg["cura_api_key"]

USERNAME = credential.username
PASSWORD = credential.password

# -------------------------------------------------
# Token cache
# -------------------------------------------------
_access_token = None
_access_token_expiry = 0

_session_token = None
_session_token_expiry = 0

TOKEN_BUFFER = 600


# -------------------------------------------------
# 1️⃣ Access token
# -------------------------------------------------
def _get_access_token():
    global _access_token, _access_token_expiry

    if _access_token and time.time() < (_access_token_expiry - TOKEN_BUFFER):
        return _access_token

    r1 = requests.get(
        f"{ACCESS_TOKEN_URL}{USERNAME}",
        headers={"Accept": "text/plain"},
        timeout=30,
    )
    r1.raise_for_status()

    authentication_url = r1.text.strip().strip('"')

    r2 = requests.post(
        authentication_url,
        data={
            "grant_type": "password",
            "client_id": "fhir-server",
            "username": USERNAME,
            "password": PASSWORD,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=30,
    )
    r2.raise_for_status()

    data = r2.json()
    _access_token = data["access_token"]
    _access_token_expiry = time.time() + int(data.get("expires_in", 3600))

    return _access_token


# -------------------------------------------------
# 2️⃣ Validate userinfo
# -------------------------------------------------
def _validate_userinfo():
    access_token = _get_access_token()

    r = requests.get(
        AUTH_USERINFO_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "CURA-API-KEY": CURA_API_KEY,
            "Accept": "application/json",
        },
        timeout=30,
    )

    r.raise_for_status()


# -------------------------------------------------
# 3️⃣ Session token
# -------------------------------------------------
def _get_session_token():
    global _session_token, _session_token_expiry

    if _session_token and time.time() < (_session_token_expiry - TOKEN_BUFFER):
        return _session_token

    access_token = _get_access_token()

    r = requests.post(
        SESSION_TOKEN_URL,
        data={
            "organization": ORG_ID,
            "userRole": USER_ROLE,
            "apiVersion": API_VERSION,
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "CURA-API-KEY": CURA_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )

    if r.status_code >= 300:
        raise RuntimeError(f"Session-token fejl {r.status_code}: {r.text}")

    data = r.json()["sessionToken"]
    _session_token = data["tokenString"]
    _session_token_expiry = time.time() + 3600

    return _session_token


# -------------------------------------------------
# Headers
# -------------------------------------------------
def _auth_headers():
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "CURA-API-KEY": CURA_API_KEY,
        "CuraSessionToken": f"Bearer {_get_session_token()}",
    }


# -------------------------------------------------
# ✅ GET
# -------------------------------------------------
def get(endpoint: str, raw: bool = False):
    url = f"{BASE_URL}{endpoint}"

    r = requests.get(url, headers=_auth_headers(), timeout=30)

    print("\n--- GET DEBUG ---")
    print("URL:", url)
    print("Status:", r.status_code)

    r.raise_for_status()

    data = r.json()

    if raw:
        return data

    if isinstance(data, dict) and isinstance(data.get("entry"), list):
        return data["entry"]

    return data


# -------------------------------------------------
# ✅ POST
# -------------------------------------------------
def post(endpoint: str, body: dict, raw: bool = False):
    url = f"{BASE_URL}{endpoint}"

    r = requests.post(
        url,
        headers={
            **_auth_headers(),
            "Content-Type": "application/json"
        },
        json=body,
        timeout=30,
    )

    print("\n--- POST DEBUG ---")
    print("URL:", url)
    print("Status:", r.status_code)
    print("Response:", r.text)

    r.raise_for_status()

    # --------------------------------------------------------
    # ✅ COMMON RESULT (fallback safe)
    # --------------------------------------------------------
    result = {
        "success": True,
        "status_code": r.status_code,
        "location": r.headers.get("Location"),
        "data": None,
        "empty_response": False
    }

    # --------------------------------------------------------
    # ✅ TOM RESPONSE (Cura normal opførsel)
    # --------------------------------------------------------
    if not r.text.strip():
        result["empty_response"] = True
        return result

    # --------------------------------------------------------
    # ✅ PRØV JSON
    # --------------------------------------------------------
    try:
        data = r.json()
        result["data"] = data

        if raw:
            return result

        return data

    except ValueError:
        # 👉 fallback hvis det IKKE er JSON
        result["data"] = r.text
        result["non_json_response"] = True
        return result

# -------------------------------------------------
# ✅ PATCH
# -------------------------------------------------
def put(endpoint: str, body: dict, raw: bool = False):
    url = f"{BASE_URL}{endpoint}"

    r = requests.put(
        url,
        headers={
            **_auth_headers(),
            "Content-Type": "application/json"
        },
        json=body,
        timeout=30,
    )

    print("\n--- PUT DEBUG ---")
    print("URL:", url)
    print("Status:", r.status_code)
    print("Response:", r.text)

    r.raise_for_status()

    if not r.text.strip():
        return {
            "success": True,
            "status_code": r.status_code,
            "empty_response": True
        }

    try:
        data = r.json()
        return {"success": True, "data": data, "status_code": r.status_code}
    except:
        return {"success": True, "data": r.text, "status_code": r.status_code}
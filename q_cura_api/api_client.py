import time
import requests

from automation_server_client import AutomationServer, Credential

# -------------------------------------------------
# Init Automation Server
# -------------------------------------------------
AutomationServer.from_environment()

# -------------------------------------------------
# Aktiv credential (default = PROD)
# -------------------------------------------------
_active_credential_name = "API_CURA"

# -------------------------------------------------
# Globale config variabler
# -------------------------------------------------
credential = None
cfg = None

BASE_URL = None
ACCESS_TOKEN_URL = None
AUTH_USERINFO_URL = None
SESSION_TOKEN_URL = None

ORG_ID = None
USER_ROLE = None
API_VERSION = None

CURA_API_KEY = None

USERNAME = None
PASSWORD = None

# -------------------------------------------------
# Token cache
# -------------------------------------------------
_access_token = None
_access_token_expiry = 0

_session_token = None
_session_token_expiry = 0

TOKEN_BUFFER = 600


# -------------------------------------------------
# ✅ INIT CLIENT (meget vigtig)
# -------------------------------------------------
def _init_client():
    global credential, cfg
    global BASE_URL, ACCESS_TOKEN_URL, AUTH_USERINFO_URL, SESSION_TOKEN_URL
    global ORG_ID, USER_ROLE, API_VERSION
    global CURA_API_KEY, USERNAME, PASSWORD
    global _access_token, _session_token

    # 🔥 hent credential
    credential = Credential.get_credential(_active_credential_name)
    cfg = credential.data

    # 🔥 opsæt config
    BASE_URL = cfg["base_url"]
    ACCESS_TOKEN_URL = cfg["access_token_url"]
    AUTH_USERINFO_URL = cfg["auth_userinfo"]
    SESSION_TOKEN_URL = cfg["session_token_url"]

    ORG_ID = cfg["org_id"]
    USER_ROLE = cfg["user_role"]
    API_VERSION = cfg["api_version"]

    CURA_API_KEY = cfg["cura_api_key"]

    # -------------------------------------------------
    # Login-oplysninger
    # -------------------------------------------------
    if _active_credential_name == "API_CURA":

        # API_CURA indeholder kun JSON-config
        dirxbla_credential = Credential.get_credential("DIRXBLA")

        USERNAME = dirxbla_credential.username
        PASSWORD = dirxbla_credential.password

    else:

        # Gammel adfærd for alle andre credentials
        USERNAME = credential.username
        PASSWORD = credential.password

    # 🔥 reset tokens når vi skifter miljø
    _access_token = None
    _session_token = None

    #print(f"\n⚙️ Cura client initialiseret med credential: {_active_credential_name}")
    #print(f"🌐 Base URL: {BASE_URL}")

# -------------------------------------------------
# ✅ PUBLIC: SKIFT MILJØ
# -------------------------------------------------
def set_cura_credential(credential_name: str):
    global _active_credential_name

    _active_credential_name = credential_name

    # 🔥 geninitialiser hele clienten
    _init_client()


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
# 2️⃣ Session token
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

    #print("\n--- GET DEBUG ---")
    #print("URL:", url)
    #print("Status:", r.status_code)

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
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )

    #print("\n--- POST DEBUG ---")
    #print("Status:", r.status_code)

    r.raise_for_status()

    if not r.text.strip():
        return {"success": True, "status_code": r.status_code}

    try:
        return r.json() if not raw else {"data": r.json()}
    except:
        return {"success": True, "data": r.text, "status_code": r.status_code}


# -------------------------------------------------
# ✅ PUT
# -------------------------------------------------
def put(endpoint: str, body: dict, raw: bool = False):
    url = f"{BASE_URL}{endpoint}"

    r = requests.put(
        url,
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )

    #print("\n--- PUT DEBUG ---")
    #print("Status:", r.status_code)

    r.raise_for_status()

    if not r.text.strip():
        return {"success": True, "status_code": r.status_code}

    try:
        return r.json() if not raw else {"data": r.json()}
    except:
        return {"success": True, "data": r.text, "status_code": r.status_code}


# -------------------------------------------------
# ✅ INIT KØRES AUTOMATISK
# -------------------------------------------------
_init_client()
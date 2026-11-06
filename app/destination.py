import os
import json
import httpx


def _get_dest_service_creds() -> dict:
    """Destination service credentials from VCAP_SERVICES (CF) or flat env vars (local dev)."""
    auth_url = os.getenv("DEST_AUTH_URL")
    if auth_url:
        return {
            "url":          auth_url,
            "uri":          os.getenv("DEST_URI", ""),
            "clientid":     os.getenv("DEST_CLIENT_ID", ""),
            "clientsecret": os.getenv("DEST_CLIENT_SECRET", ""),
        }
    vcap = json.loads(os.getenv("VCAP_SERVICES", "{}"))
    bindings = vcap.get("destination", [])
    if not bindings:
        raise RuntimeError("No Destination service binding found in VCAP_SERVICES.")
    return bindings[0]["credentials"]


def _get_ds_token(creds: dict) -> str:
    resp = httpx.post(
        creds["url"] + "/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(creds["clientid"], creds["clientsecret"]),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_destination_config(name: str) -> dict:
    """Return the raw destinationConfiguration dict for the named destination.

    Use this when you need low-level fields (clientId, clientSecret, tokenServiceURL)
    rather than a ready-to-use auth header — e.g. for ai-core-sdk initialization.
    """
    creds = _get_dest_service_creds()
    ds_token = _get_ds_token(creds)

    resp = httpx.get(
        f"{creds['uri']}/destination-configuration/v1/destinations/{name}",
        headers={"Authorization": f"Bearer {ds_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["destinationConfiguration"]


def resolve_destination(name: str) -> tuple[str, dict]:
    """Return (base_url, auth_headers) for the named BTP destination.

    No X-user-token is sent — suitable for system-user (technical) destinations.
    The Destination service handles OAuth2/SAML token exchange internally and
    returns a ready bearer token in authTokens[0].
    """
    creds = _get_dest_service_creds()
    ds_token = _get_ds_token(creds)

    resp = httpx.get(
        f"{creds['uri']}/destination-configuration/v1/destinations/{name}",
        headers={"Authorization": f"Bearer {ds_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    raw_url = data["destinationConfiguration"]["URL"].rstrip("/")
    # SuccessFactors destinations point to the tenant root; OData v2 lives under /odata/v2
    base_url = raw_url + "/odata/v2" if name == "sfsf-conn-sysuser" else raw_url
    auth_tokens = data.get("authTokens", [])
    if auth_tokens and auth_tokens[0].get("value"):
        token_type = auth_tokens[0].get("type", "Bearer")
        auth_header = f"{token_type} {auth_tokens[0]['value']}"
    else:
        auth_header = ""

    return base_url, {"Authorization": auth_header, "Accept": "application/json"}

import os
import httpx


def _get_aicore_creds() -> dict:
    """Resolve AI Core credentials via the aicore-destination BTP destination."""
    from app.destination import get_destination_config

    cfg = get_destination_config("aicore-destination")
    return {
        "url":         cfg["tokenServiceURL"].replace("/oauth/token", ""),
        "clientid":    cfg["clientId"],
        "clientsecret": cfg["clientSecret"],
        "serviceurls": {"AI_API_URL": cfg["URL"]},
    }


def get_access_token(creds: dict) -> str:
    """Fetch a client-credentials access token from the AI Core OAuth endpoint."""
    resp = httpx.post(
        creds["url"] + "/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(creds["clientid"], creds["clientsecret"]),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_deployment_url(creds: dict, model: str, resource_group: str) -> str:
    """Return the inference URL for the first running deployment matching model."""
    from ai_core_sdk.ai_core_v2_client import AICoreV2Client

    client = AICoreV2Client(
        base_url=creds["serviceurls"]["AI_API_URL"] + "/v2",
        auth_url=creds["url"] + "/oauth/token",
        client_id=creds["clientid"],
        client_secret=creds["clientsecret"],
        resource_group=resource_group,
    )
    deployments = client.deployment.query()
    deployment = next(
        (d for d in deployments.resources
         if d.status.value == "RUNNING"
         and (d.details or {}).get("resources", {}).get("backend_details", {})
             .get("model", {}).get("name") == model),
        None,
    )
    if not deployment:
        raise RuntimeError(
            f"No running deployment for model '{model}' in resource group '{resource_group}'"
        )
    return deployment.deployment_url


def get_llm():
    """Return a ChatOpenAI instance pointed at the AI Core deployment."""
    from langchain_openai import ChatOpenAI

    creds = _get_aicore_creds()
    model = os.getenv("MODEL_NAME", "gpt-4.1")
    resource_group = os.getenv("AICORE_RESOURCE_GROUP", "default")

    deployment_url = get_deployment_url(creds, model, resource_group)
    access_token = get_access_token(creds)

    return ChatOpenAI(
        model=model,
        base_url=f"{deployment_url}/v1",
        api_key=access_token,
        max_tokens=4096,
        default_headers={"AI-Resource-Group": resource_group},
    )

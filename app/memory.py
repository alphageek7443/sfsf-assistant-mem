from sap_cloud_sdk.agent_memory import AgentMemoryClient, AgentMemoryConfig, AccessStrategy, create_client

from app.destination import get_destination_config


def _get_memory_config() -> AgentMemoryConfig:
    """Resolve SAP Agent Memory Service credentials via the sap-agent-memory destination."""
    cfg = get_destination_config("sap-agent-memory")
    return AgentMemoryConfig(
        base_url=cfg["URL"].rstrip("/"),
        token_url=cfg["tokenServiceURL"],
        client_id=cfg["clientId"],
        client_secret=cfg["clientSecret"]
    )


def get_memory_client(tenant: str | None = None) -> AgentMemoryClient:
    """Return an AgentMemoryClient wired to the SAP Agent Memory Service.

    Pass tenant (BTP subaccount identityzone subdomain) for per-tenant isolation.
    Omit for provider-level access (single-tenant / system-user deployments).
    """
    strategy = AccessStrategy.SUBSCRIBER if tenant else AccessStrategy.PROVIDER
    return create_client(
        config=_get_memory_config(),
        access_strategy=strategy,
        tenant=tenant,
    )

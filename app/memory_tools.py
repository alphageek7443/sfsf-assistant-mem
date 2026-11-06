from langchain_core.tools import tool

from app.memory import get_memory_client

AGENT_ID = "sfsf-assistant-mem"

def get_system_user() -> str:
    """Read the SystemUser from the sfsf-conn-sysuser destination."""
    from app.destination import get_destination_config
    cfg = get_destination_config("sfsf-conn-sysuser")
    return cfg.get("SystemUser", "sfadmin")


@tool
def remember(content: str) -> str:
    """Store a long-term fact or preference for the current user across sessions.

    Args:
        content: The fact to remember (e.g. 'User prefers leave balances shown in days')
    """
    invoker_id = get_system_user()
    with get_memory_client() as client:
        client.add_memory(
            agent_id=AGENT_ID,
            invoker_id=invoker_id,
            content=content,
            metadata={"source": "preferences", "confidence": "high"},
        )
    return f"Remembered: {content}"


@tool
def recall(query: str) -> list:
    """Search long-term memory for facts about the current user relevant to the query.

    Args:
        query: Natural language description of what to look for
    """
    invoker_id = get_system_user()
    with get_memory_client() as client:
        results = client.search_memories(
            agent_id=AGENT_ID,
            invoker_id=invoker_id,
            query=query,
            threshold=0.6,
            limit=5,
        )
    return [r.content for r in results]


def get_memory_tools() -> list:
    return [remember, recall]

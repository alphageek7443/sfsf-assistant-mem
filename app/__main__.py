import uvicorn
import os
import json
from app.agent_card import get_agent_card
from app.agent_executor import MyAgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore


def get_app_url() -> str:
    """Get the app URL from CF environment or fall back to localhost."""
    vcap = json.loads(os.getenv("VCAP_APPLICATION", "{}"))
    uris = vcap.get("application_uris", [])
    if uris:
        return f"https://{uris[0]}"
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8080")
    return f"http://{host}:{port}"


def main():
    from dotenv import load_dotenv
    load_dotenv()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))

    app_url = get_app_url()
    agent_card = get_agent_card(app_url)
    agent_executor = MyAgentExecutor()

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()

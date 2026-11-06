from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
from typing import Any, AsyncIterable, Literal

from app.llm import get_llm
from app.tools import get_tools
from app.memory_tools import get_memory_tools


class ResponseFormat(BaseModel):
    """Structured response format for A2A compatibility."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


# Names of memory-only tools (these do NOT count as "data" tool calls)
MEMORY_TOOL_NAMES = {"recall", "remember"}

SYSTEM_INSTRUCTION = """You are an HR assistant integrated with SAP SuccessFactors.
You help users with:
- Looking up employee profile information (name, job title, department, email, location)
- Checking leave balances (annual leave, sick leave, etc.)
- Viewing direct reports and org chart hierarchies
- Searching for employees by name or department
- Querying talent pools for succession planning, candidate recommendations, and high-potential employee identification by department, location, and target roles

Always use the available tools to retrieve live data from SuccessFactors rather than guessing.
If the user's request is ambiguous (e.g. a name that could match multiple employees), use the search_employees tool first to find the right user ID.

When a user asks about succession slates, candidate recommendations, talent pools, or high-potential employees, you MUST call the query_talent_pool tool to fetch live candidate data from SuccessFactors. Use the department, location, and role filters extracted from the user's request AND from any recalled memory context as parameters. Memory recall alone is NEVER a complete answer — it only provides context and preferences to guide your SFSF tool calls.

## Memory rules
- ALWAYS call recall() as your FIRST action on EVERY user request. Use the user's request as the query.
- Memory results are CONTEXT, not answers. After recall(), you MUST ALWAYS call at least one SuccessFactors data tool (get_employee_info, get_leave_balance, get_direct_reports, search_employees, get_org_chart, or query_talent_pool) to fetch live data. NEVER respond with only memory content.
- Merge information from both the user query and recalled memory to build the best possible tool parameters. For example, if memory specifies "restrict to VP and Director roles", use those as target_roles in query_talent_pool. If the user says "Operation FR department in Paris", use those as department_keyword and location_name.
- Apply any recalled preferences to your response format (e.g. table format, language).
- When the user states a preference (e.g. language, display format, shortcuts), call remember() to store it for future sessions.
- When the user asks you to forget something, do not store it and confirm.

## Response status rules
- Set status to "completed" when you have called a SuccessFactors data tool (not just recall/remember) and returned results (even if no data was found).
- Set status to "input_required" ONLY when you genuinely cannot proceed without user input BEFORE calling any tool.
- Do NOT ask for confirmation or additional filters if you already have enough information to call a tool. Always attempt the tool call first with the information available from the user query and recalled memory; you can refine later if needed.
- Set status to "error" if an unrecoverable error occurs.
"""

RESPONSE_FORMAT_INSTRUCTION = """Always respond using the ResponseFormat schema."""

memory = MemorySaver()


class MyAgent:
    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self):
        self.tools = get_tools() + get_memory_tools()

    def _get_graph(self):
        """Build graph with a fresh AI Core token on every call."""
        return create_react_agent(
            get_llm(),
            tools=self.tools,
            checkpointer=memory,
            prompt=SYSTEM_INSTRUCTION,
            response_format=(RESPONSE_FORMAT_INSTRUCTION, ResponseFormat),
        )

    def invoke(self, query: str, session_id: str) -> dict[str, Any]:
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        self._get_graph().invoke({"messages": [("user", query)]}, config)
        return self._get_response(config)

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        inputs = {"messages": [("user", query)]}
        for item in self._get_graph().stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if isinstance(message, AIMessage) and message.tool_calls:
                yield {"is_task_complete": False, "require_user_input": False, "content": "Processing..."}
            elif isinstance(message, ToolMessage):
                yield {"is_task_complete": False, "require_user_input": False, "content": "Analyzing results..."}
        yield self._get_response(config)

    def _get_response(self, config: RunnableConfig) -> dict[str, Any]:
        state = self._get_graph().get_state(config)
        messages = state.values.get("messages", [])

        # Check whether a real SFSF data tool was called (exclude recall/remember)
        sfsf_tool_was_called = any(
            isinstance(m, ToolMessage) and m.name not in MEMORY_TOOL_NAMES
            for m in messages[-10:]
        )

        structured = state.values.get("structured_response")
        if structured and isinstance(structured, ResponseFormat):
            if sfsf_tool_was_called and structured.status == "input_required":
                return {"is_task_complete": True, "require_user_input": False, "content": structured.message}
            return {
                "is_task_complete": structured.status == "completed",
                "require_user_input": structured.status == "input_required",
                "content": structured.message,
            }
        if messages and hasattr(messages[-1], "content"):
            return {"is_task_complete": True, "require_user_input": False, "content": str(messages[-1].content)}
        return {"is_task_complete": False, "require_user_input": True, "content": "Could you rephrase your request?"}

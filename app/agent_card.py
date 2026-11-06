from a2a.types import AgentCard, AgentCapabilities, AgentSkill


def get_agent_card(base_url: str) -> AgentCard:
    capabilities = AgentCapabilities(streaming=True, pushNotifications=False)

    skill_employee = AgentSkill(
        id="employee_info",
        name="Employee Profile Lookup",
        description="Look up employee profile details such as job title, department, email, and location from SAP SuccessFactors.",
        tags=["hr", "employee", "successfactors"],
        examples=["What is John Smith's job title?", "Show me the profile of employee 00001234"],
    )

    skill_leave = AgentSkill(
        id="leave_balance",
        name="Leave Balance Check",
        description="Check current leave balances (annual leave, sick leave, etc.) for an employee in SAP SuccessFactors.",
        tags=["hr", "leave", "absence", "successfactors"],
        examples=["How many vacation days does Jane Doe have left?", "What is my current sick leave balance?"],
    )

    skill_org = AgentSkill(
        id="org_chart",
        name="Org Chart & Direct Reports",
        description="View an employee's direct reports or the org chart hierarchy in SAP SuccessFactors.",
        tags=["hr", "org chart", "team", "successfactors"],
        examples=["Who reports to Maria Garcia?", "Show me the org chart for department Engineering"],
    )

    skill_search = AgentSkill(
        id="employee_search",
        name="Employee Search",
        description="Search for employees by name or department in SAP SuccessFactors.",
        tags=["hr", "search", "successfactors"],
        examples=["Find all employees named Smith", "List employees in the Finance department"],
    )

    skill_talent = AgentSkill(
        id="talent_pool",
        name="Talent Pool & Succession Planning",
        description="Search for high-potential candidates in talent pools for succession planning, filtered by department, location, and target roles. Uses stored memory context for role restrictions and prioritization criteria.",
        tags=["hr", "talent", "succession", "candidates", "successfactors"],
        examples=[
            "Find VP candidates in the Operations department in Paris",
            "Retrieve high-potential recommendations for the Director succession slate",
            "Show me candidate recommendations for the VP of Product succession slate",
        ],
    )

    return AgentCard(
        name="SFSF HR Assistant",
        description=(
            "An HR assistant that queries employee data, leave balances, and org chart "
            "information from SAP SuccessFactors via OData APIs."
        ),
        url=f"{base_url}/",
        version="1.0.0",
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        capabilities=capabilities,
        skills=[skill_employee, skill_leave, skill_org, skill_search, skill_talent],
    )

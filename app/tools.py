from typing import List, Optional

from langchain_core.tools import tool
import httpx

from app.destination import resolve_destination


def _resolve_user_id(identifier: str) -> str:
    """Resolve a username (e.g. 'twalker') to a numeric userId (e.g. '82094').

    SuccessFactors OData key is always the numeric userId. If the identifier
    is already numeric, return it as-is. Otherwise filter by username field.
    """
    if identifier.isdigit():
        return identifier
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    resp = httpx.get(
        f"{base_url}/User",
        params={
            "$filter": f"username eq '{identifier}'",
            "$select": "userId",
            "$format": "json",
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json().get("d", {}).get("results", [])
    if not results:
        raise ValueError(f"No employee found with username '{identifier}'")
    return results[0]["userId"]


@tool
def get_employee_info(user_id: str) -> dict:
    """Retrieve full profile information for a SuccessFactors employee.

    Args:
        user_id: The SuccessFactors userId or username (e.g. "twalker" or "82094")
    """
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    try:
        resolved = _resolve_user_id(user_id)
        resp = httpx.get(
            f"{base_url}/User('{resolved}')",
            params={
                "$select": (
                    "userId,username,empId,firstName,lastName,mi,displayName,salutation,nickname,pronouns,"
                    "email,businessPhone,cellPhone,homePhone,"
                    "addressLine1,city,state,zipCode,country,"
                    "title,jobTitle,jobCode,jobLevel,jobFamily,jobRole,"
                    "department,division,location,"
                    "hireDate,origHireDate,dateOfCurrentPosition,gender,"
                    "status,employeeClass,defaultLocale,timeZone,"
                    "teamMembersSize,totalTeamSize,keyPosition,"
                    "manager/userId,manager/username,manager/firstName,manager/lastName,"
                    "manager/email,manager/title,manager/department,manager/jobTitle"
                ),
                "$expand": "manager",
                "$format": "json",
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("d", {})
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"Failed to fetch employee info: {str(e)}"}


@tool
def get_leave_balance(user_id: str) -> list:
    """Retrieve current leave balances for a SuccessFactors employee.

    Args:
        user_id: The SuccessFactors userId or username (e.g. "twalker" or "82094")
    """
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    try:
        resolved = _resolve_user_id(user_id)
        resp = httpx.get(
            f"{base_url}/TimeAccount",
            params={
                "$filter": f"userId eq '{resolved}'",
                "$select": "externalCode,accountType,startDate,endDate,accountClosed",
                "$expand": "timeAccountSummary",
                "$format": "json",
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("d", {}).get("results", [])
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"Failed to fetch leave balances: {str(e)}"}


@tool
def get_direct_reports(manager_user_id: str) -> list:
    """Retrieve the list of direct reports for a manager in SAP SuccessFactors.

    Args:
        manager_user_id: The SuccessFactors userId or username of the manager
    """
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    try:
        resolved = _resolve_user_id(manager_user_id)
        resp = httpx.get(
            f"{base_url}/User",
            params={
                "$filter": f"manager/userId eq '{resolved}'",
                "$select": "userId,username,firstName,lastName,jobTitle,department,email",
                "$format": "json",
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("d", {}).get("results", [])
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"Failed to fetch direct reports: {str(e)}"}


@tool
def search_employees(name: str, department: str = "") -> list:
    """Search for employees by name or department in SAP SuccessFactors.

    Args:
        name: Full or partial name to search for (first or last name)
        department: Optional department filter
    """
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    try:
        parts = name.strip().split()
        if len(parts) >= 2:
            filters = [f"(startswith(firstName,'{parts[0]}') and startswith(lastName,'{parts[-1]}'))"]
        else:
            filters = [f"(startswith(firstName,'{name}') or startswith(lastName,'{name}'))"]
        if department:
            filters.append(f"department eq '{department}'")
        filter_str = " and ".join(filters)

        resp = httpx.get(
            f"{base_url}/User",
            params={
                "$filter": filter_str,
                "$select": (
                    "userId,username,empId,firstName,lastName,mi,displayName,salutation,nickname,pronouns,"
                    "email,businessPhone,cellPhone,homePhone,"
                    "addressLine1,city,state,zipCode,country,"
                    "title,jobTitle,jobCode,jobLevel,jobFamily,jobRole,"
                    "department,division,location,"
                    "hireDate,origHireDate,dateOfCurrentPosition,gender,"
                    "status,employeeClass,defaultLocale,timeZone,"
                    "teamMembersSize,totalTeamSize,keyPosition,"
                    "manager/userId,manager/username,manager/firstName,manager/lastName,"
                    "manager/email,manager/title,manager/department,manager/jobTitle"
                ),
                "$expand": "manager",
                "$top": 20,
                "$format": "json",
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("d", {}).get("results", [])
    except httpx.HTTPError as e:
        return {"error": f"Employee search failed: {str(e)}"}


@tool
def get_org_chart(user_id: str, levels: int = 2) -> dict:
    """Retrieve the org chart hierarchy starting from a given employee.

    Args:
        user_id: The SuccessFactors userId or username to start the org chart from
        levels: Number of levels to retrieve downward (1-3, default 2)
    """
    levels = max(1, min(levels, 3))
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    try:
        resolved = _resolve_user_id(user_id)
        result = {"user_id": resolved, "direct_reports": []}
        resp = httpx.get(
            f"{base_url}/User('{resolved}')",
            params={"$select": "userId,username,firstName,lastName,jobTitle", "$format": "json"},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result.update(resp.json().get("d", {}))

        if levels > 1:
            reports_resp = httpx.get(
                f"{base_url}/User",
                params={
                    "$filter": f"manager/userId eq '{resolved}'",
                    "$select": "userId,username,firstName,lastName,jobTitle",
                    "$format": "json",
                },
                headers=headers,
                timeout=30,
            )
            reports_resp.raise_for_status()
            result["direct_reports"] = reports_resp.json().get("d", {}).get("results", [])

        return result
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"Failed to fetch org chart: {str(e)}"}


@tool
def query_talent_pool(department_keyword: str, location_name: str = "", target_roles: Optional[List[str]] = None) -> list:
    """Search for employees in a talent pool by department keyword, location, and target role titles.

    Args:
        department_keyword: Partial department name to search for (e.g. "Human Resources")
        location_name: Optional location name to filter by (e.g. "San Francisco")
        target_roles: Optional list of job title keywords to include (e.g., ["VP", "Director"])
    """
    base_url, headers = resolve_destination("sfsf-conn-sysuser")
    try:
        filter_str = f"substringof('{department_keyword}', departmentNav/name) eq true"
        if location_name:
            filter_str += f" and locationNav/name eq '{location_name}'"

        # substringof() must be in the URL directly — params dict causes httpx to
        # URL-encode it, which breaks OData v2 function syntax
        url = (
            f"{base_url}/EmpJob"
            f"?$filter={filter_str}"
            f"&$expand=locationNav,departmentNav,userNav"
            f"&$select=userId,jobTitle,department,locationNav/name,departmentNav/name,"
            f"userNav/firstName,userNav/lastName"
            f"&$format=json"
        )
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("d", {}).get("results", [])
        records = []
        for r in results:
            title = r.get("jobTitle") or ""
            
            # Post-filter by target roles if specified
            if target_roles:
                if not any(role.lower() in title.lower() for role in target_roles):
                    continue

            records.append({
                "userId": r.get("userId"),
                "jobTitle": title,
                "department": (r.get("departmentNav") or {}).get("name"),
                "location": (r.get("locationNav") or {}).get("name"),
                "firstName": (r.get("userNav") or {}).get("firstName"),
                "lastName": (r.get("userNav") or {}).get("lastName"),
            })

        return records
    except httpx.HTTPError as e:
        return {"error": f"Talent pool query failed: {str(e)}"}
    except ValueError as e:
        return {"error": f"Talent pool query failed: {str(e)}"}


def get_tools() -> list:
    """Return all SFSF OData tools available to the agent."""
    return [get_employee_info, get_leave_balance, get_direct_reports, search_employees, get_org_chart, query_talent_pool]

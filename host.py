import asyncio
import json
from fastmcp import Client
from groq import Groq
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime, UTC
import time

# ==============================
# RATE LIMITER (ASYNC SAFE)
# ==============================

LAST_CALL_TIME = 0
MIN_INTERVAL = 1

async def rate_limit():
    global LAST_CALL_TIME
    now = time.time()
    if now - LAST_CALL_TIME < MIN_INTERVAL:
        await asyncio.sleep(MIN_INTERVAL - (now - LAST_CALL_TIME))
    LAST_CALL_TIME = time.time()


# ==============================
# ENV
# ==============================

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ==============================
# RBAC
# ==============================

ROLE_PERMISSIONS = {
    "junior": {
        "validate_transaction_policies",
        "flag_high_value_transactions",
        "get_vendor_risk_profile"
    },
    "senior": {
        "validate_transaction_policies",
        "flag_high_value_transactions",
        "get_vendor_risk_profile",
        "enrich_transaction_context"
    },
    "partner": {
        "validate_transaction_policies",
        "flag_high_value_transactions",
        "get_vendor_risk_profile",
        "enrich_transaction_context",
        "generate_audit_markdown_report"
    },
    "admin": {"*"}
}

def authorize(user_role: str, tool_name: str):
    if user_role not in ROLE_PERMISSIONS:
        raise PermissionError(f"Invalid role: {user_role}")

    allowed = ROLE_PERMISSIONS[user_role]

    if "*" in allowed:
        return

    if tool_name not in allowed:
        raise PermissionError(
            f"Role '{user_role}' is not authorized to call '{tool_name}'"
        )


# ==============================
# LOGGING
# ==============================

def log_tool_call(flow_id, tool_name, args):
    log_entry = {
        "flow_id": flow_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "tool": tool_name,
        "args": args
    }

    with open("audit_trace.log", "a") as f:
        f.write(json.dumps(log_entry) + "\n")


# ==============================
# SAFE TOOL CALL WRAPPER
# ==============================

async def safe_call_tool(session, tool_name, args, timeout=10):
    try:
        result = await asyncio.wait_for(
            session.call_tool(tool_name, args),
            timeout=timeout
        )

        text = result.content[0].text

        # Try parsing JSON
        try:
            data = json.loads(text)

            # If structured error returned
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(data.get("message"))

            return data

        except json.JSONDecodeError:
            # Not JSON → return raw text (e.g., Markdown)
            return text

    except Exception as e:
        raise RuntimeError(f"{tool_name} failed: {str(e)}")

async def wait_for_mcp():
    for i in range(15):
        try:
            async with Client("http://mcp:8000/mcp") as test:
                print("MCP ready.")
                return
        except Exception:
            print(f"Waiting for MCP... ({i+1})")
            await asyncio.sleep(2)

    raise RuntimeError("MCP service not reachable after retries.")
# ==============================
# MAIN
# ==============================

async def run_audit():
    await wait_for_mcp()
    flow_id = f"AUDIT_{uuid.uuid4().hex[:8]}"
    user_id = "auditor_01"
    user_role = "partner"

    async with Client("http://mcp:8000/mcp") as mcp_session:

        # ------------------------------------
        # CAPABILITY DISCOVERY (LOGGED)
        # ------------------------------------
        tools = await mcp_session.list_tools()
        log_tool_call(flow_id, "CAPABILITY_DISCOVERY",
                      [t.name for t in tools])

        groq_tools = [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "No description provided.",
                "parameters": t.inputSchema
            }
        } for t in tools]

        # ------------------------------------
        # GROQ TOOL SELECTION
        # ------------------------------------
        await rate_limit()

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": "Run full policy validation audit."
            }],
            tools=groq_tools,
            tool_choice="auto",
            temperature=0
        )

        message = response.choices[0].message

        if not message.tool_calls:
            print("No tool selected.")
            return

        tool_call = message.tool_calls[0]

        # Defensive argument parsing
        try:
            args = json.loads(tool_call.function.arguments or "{}")
        except Exception:
            print("Invalid tool arguments format.")
            return

        # ------------------------------------
        # POLICY ENGINE
        # ------------------------------------
        try:
            authorize(user_role, tool_call.function.name)
        except PermissionError as e:
            log_tool_call(flow_id, "RBAC_BLOCK", {
                "role": user_role,
                "attempted_tool": tool_call.function.name
            })
            print(f"Access Denied: {e}")
            return

        findings = await safe_call_tool(
            mcp_session,
            tool_call.function.name,
            args
        )

        log_tool_call(flow_id, tool_call.function.name, args)

        enriched_findings = []

        # ------------------------------------
        # ENRICHMENT
        # ------------------------------------
        try:
            authorize(user_role, "enrich_transaction_context")
        except PermissionError as e:
            log_tool_call(flow_id, "RBAC_BLOCK", {
                "role": user_role,
                "attempted_tool": "enrich_transaction_context"
            })
            print(f"Access Denied: {e}")
            return

        for item in findings:

            if item.get("severity") == "HIGH":

                await rate_limit()

                enrichment = await safe_call_tool(
                    mcp_session,
                    "enrich_transaction_context",
                    {"vendor_name": item["vendor"]}
                )

                log_tool_call(
                    flow_id,
                    "enrich_transaction_context",
                    {"vendor_name": item["vendor"]}
                )

                item["external_risk"] = enrichment

            enriched_findings.append(item)

        # ------------------------------------
        # PAYLOAD SIZE DEFENSE
        # ------------------------------------
        payload = json.dumps(enriched_findings)
        if len(payload) > 10000:
            print("Payload too large. Aborting.")
            return

        # ------------------------------------
        # PROMPT PRIMITIVE (FROM SERVER)
        # ------------------------------------
        prompt_response = await asyncio.wait_for(
        mcp_session.get_prompt("compliance_audit_prompt"),
        timeout=5
        )

        log_tool_call(flow_id, "PROMPT_RETRIEVAL", {})

        prompt_text = ""
        for msg in prompt_response.messages:
          if msg.role == "system":
           prompt_text += msg.content + "\n"

        reasoning_messages = [
        {"role": "system", "content": prompt_text},
         {"role": "user", "content": f"""
           Below are structured compliance findings in JSON format:

           {payload}

            Generate a formal compliance audit summary.

            Requirements:
            - Group by severity.
            - For HIGH items, include recommended actions.
            - Maintain structured professional tone.
            """}
         ]

        await rate_limit()

        final_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=reasoning_messages,
            temperature=0
        )

        print("\n--- Enriched Audit Report ---\n")

        # ------------------------------------
        # REPORT GENERATION
        # ------------------------------------
        try:
            authorize(user_role, "generate_audit_markdown_report")
        except PermissionError as e:
            log_tool_call(flow_id, "RBAC_BLOCK", {
                "role": user_role,
                "attempted_tool": "generate_audit_markdown_report"
            })
            print(f"Access Denied: {e}")
            return

        await rate_limit()

        report_data = await safe_call_tool(
            mcp_session,
            "generate_audit_markdown_report",
            {"findings_json": json.dumps(enriched_findings),
             "flow_id":flow_id,
             "user_id":user_id,
             "role":user_role}
        )

        log_tool_call(flow_id,
                      "generate_audit_markdown_report",
                      {})

        print("\n--- Final Audit Markdown Report ---\n")
        print(report_data)
        print(final_response.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(run_audit())
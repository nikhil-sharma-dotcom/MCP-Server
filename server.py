import os
from fastmcp import FastMCP
from resources import database_schema_resource
from prompts import compliance_audit_prompt
from tools import ALL_TOOLS
from dotenv import load_dotenv
load_dotenv()
mcp = FastMCP("Enterprise_Audit_Framework", version="2024-11-05")
TOOL_DESCRIPTIONS = {
    "validate_transaction_policies": """
Analyze financial transactions and detect compliance violations.

Checks include:
- blacklisted vendor detection
- category spending limits
- excessive pending exposure across vendors

Returns structured findings with severity levels (HIGH, MEDIUM, LOW).
""",

    "flag_high_value_transactions": """
Identify transactions exceeding a configurable monetary threshold.

Used for detecting high-value financial activity that may require
additional approval or fraud investigation.
""",

    "get_vendor_risk_profile": """
Retrieve historical transaction statistics for a vendor.

Provides:
- total transaction count
- average spending value

Helps assess vendor financial behavior and potential risk exposure.
""",

    "enrich_transaction_context": """
Enrich vendor data using an internal risk intelligence database.

Returns contextual risk indicators including:
- past compliance issues
- conflict-of-interest flags
- regulatory alerts
- vendor risk score.
""",

    "generate_audit_markdown_report": """
Generate an enterprise financial compliance report.

Capabilities include:
- severity breakdown of findings
- vendor exposure analysis
- anomaly detection
- automated chart generation
- downloadable PDF report

Provides executive-level compliance insights.
"""
}
for tool in ALL_TOOLS:
    mcp.tool(
        name=tool.__name__,
        description=TOOL_DESCRIPTIONS.get(tool.__name__,"No description provided")
    )(tool)
mcp.resource("db://schema")(database_schema_resource)
mcp.prompt()(compliance_audit_prompt)
if __name__=="__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
            )
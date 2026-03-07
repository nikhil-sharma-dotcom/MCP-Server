import json
from utils import  raise_tool_error
from models.schemas import VendorRequest
from db import get_read_only_connection

async def get_vendor_risk_profile(vendor_name: str) -> str:
    """
    Retrieves historical transaction statistics for vendor.
    """

    try:
        
        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT amount FROM transactions WHERE LOWER(vendor) LIKE LOWER(?)",
            (f"%{vendor_name}%",)
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            raise_tool_error("get_vendor_risk_profile", "Vendor not found")

        amounts = [r[0] for r in rows]
        avg = sum(amounts) / len(amounts)

        return json.dumps({
            "vendor": vendor_name,
            "total_transactions": len(amounts),
            "average_spend": round(avg, 2)
        })

    except Exception as e:
        raise_tool_error("get_vendor_risk_profile", str(e))



async def enrich_transaction_context(payload: VendorRequest) -> str:
    """
    Cross-references vendor with risk intelligence database.
    """
    vendor_name = payload.vendor_name
    try:
        

        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT past_issues, conflict_of_interest, regulatory_flag, risk_score
            FROM vendor_risk
            WHERE vendor = ?
        """, (vendor_name,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise_tool_error("enrich_transaction_context", "Vendor not found")

        return json.dumps({
            "vendor": vendor_name,
            "past_issues": bool(row[0]),
            "conflict_of_interest": bool(row[1]),
            "regulatory_flag": bool(row[2]),
            "risk_score": row[3]
        })

    except Exception as e:
        raise_tool_error("enrich_transaction_context", str(e))

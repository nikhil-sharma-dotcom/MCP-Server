import json
import sqlite3
from db import get_read_only_connection
from utils import raise_tool_error
from models.schemas import HighValueRequest
async def validate_transaction_policies() -> str:
    """
    Executes multi-layer policy validation:
    - Blacklisted vendors
    - Category spending limits
    - Aggregated pending exposure
    """

    try:
        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT vendor, amount, category, status FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        blacklisted = {"Fraudulent Corp", "Shadow Holdings"}
        limits = {"Legal": 25000, "IT": 40000, "Travel": 20000}
        pending_limit = 50000

        findings = []
        pending_totals = {}

        for vendor, amount, category, status in rows:

            if vendor in blacklisted:
                findings.append({
                    "severity": "HIGH",
                    "issue": "Blacklisted Vendor",
                    "vendor": vendor,
                    "category":category,
                    "amount": amount

                })

            if category in limits and amount > limits[category]:
                findings.append({
                    "severity": "MEDIUM",
                    "issue": f"{category} limit exceeded",
                    "vendor": vendor,
                    "category":category,
                    "amount": amount
                })

            if status == "Pending":
                pending_totals[vendor] = pending_totals.get(vendor, 0) + amount

        for vendor, total in pending_totals.items():
            if total > pending_limit:
                findings.append({
                    "severity": "HIGH",
                    "issue": "Excessive Pending Aggregate",
                    "vendor": vendor,
                    "category":"PendingAggregate",
                    "amount": total
                })

        return json.dumps({
            "findings": findings,
            "count": len(findings),
            "status": "success"})

    except Exception as e:
        raise_tool_error("validate_transaction_policies", str(e))



async def flag_high_value_transactions(payload: HighValueRequest) -> str:
    """
    Flags transactions exceeding specified monetary threshold.
    """
    min_amount = payload.min_amount
    try:
        

        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT vendor, amount, category FROM transactions WHERE amount >= ?",
            (min_amount,)
        )

        rows = cursor.fetchall()
        conn.close()

        results = [
            {"vendor": r[0], "amount": r[1], "category": r[2]}
            for r in rows
        ]

        return json.dumps({"findings":results,"count":len(results)})

    except Exception as e:
        raise_tool_error("flag_high_value_transactions", str(e))

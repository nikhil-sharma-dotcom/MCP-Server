import json
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime, UTC
from fastmcp import FastMCP

mcp = FastMCP("Enterprise_Audit_Framework", version="2024-11-05")


# ==============================
# Validation Utilities
# ==============================

def validate_string(value: str, field_name: str, max_length: int = 100):
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length.")


def validate_positive_float(value: float, field_name: str):
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric.")
    if value < 0:
        raise ValueError(f"{field_name} must be positive.")


def log_error(tool_name: str, error: str):
    with open("server_error.log", "a") as f:
        f.write(f"{datetime.now(UTC)} | {tool_name} | {error}\n")


def error_response(tool_name: str, message: str):
    log_error(tool_name, message)
    return json.dumps({
        "error": True,
        "tool": tool_name,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat()
    })


def get_read_only_connection():
    return sqlite3.connect("file:audit.db?mode=ro", uri=True)


# ==============================
# TOOLS
# ==============================

@mcp.tool()
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
                    "category":category,
                    "amount": total
                })

        return json.dumps(findings)

    except Exception as e:
        return error_response("validate_transaction_policies", str(e))


@mcp.tool()
async def flag_high_value_transactions(min_amount: float = 10000.0) -> str:
    """
    Flags transactions exceeding specified monetary threshold.
    """

    try:
        validate_positive_float(min_amount, "min_amount")

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

        return json.dumps(results)

    except Exception as e:
        return error_response("flag_high_value_transactions", str(e))


@mcp.tool()
async def get_vendor_risk_profile(vendor_name: str) -> str:
    """
    Retrieves historical transaction statistics for vendor.
    """

    try:
        validate_string(vendor_name, "vendor_name")

        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT amount FROM transactions WHERE LOWER(vendor) LIKE LOWER(?)",
            (f"%{vendor_name}%",)
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return error_response("get_vendor_risk_profile", "Vendor not found")

        amounts = [r[0] for r in rows]
        avg = sum(amounts) / len(amounts)

        return json.dumps({
            "vendor": vendor_name,
            "total_transactions": len(amounts),
            "average_spend": round(avg, 2)
        })

    except Exception as e:
        return error_response("get_vendor_risk_profile", str(e))


@mcp.tool()
async def enrich_transaction_context(vendor_name: str) -> str:
    """
    Cross-references vendor with risk intelligence database.
    """

    try:
        validate_string(vendor_name, "vendor_name")

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
            return error_response("enrich_transaction_context", "Vendor not found")

        return json.dumps({
            "vendor": vendor_name,
            "past_issues": bool(row[0]),
            "conflict_of_interest": bool(row[1]),
            "regulatory_flag": bool(row[2]),
            "risk_score": row[3]
        })

    except Exception as e:
        return error_response("enrich_transaction_context", str(e))


@mcp.tool()
async def generate_audit_markdown_report(findings_json: str, flow_id: str, user_id: str,role: str) -> str:
    """
    Generates executive-level compliance report with charts and PDF export.
    """

    try:
        findings = json.loads(findings_json)

        severity_counts = defaultdict(int)
        vendor_exposure = defaultdict(float)
        total_exposure = 0

        for item in findings:
            severity_counts[item["severity"]] += 1
            vendor_exposure[item["vendor"]] += float(item["amount"])
            total_exposure += float(item["amount"])

        high = severity_counts.get("HIGH", 0)
        medium = severity_counts.get("MEDIUM", 0)
        low = severity_counts.get("LOW", 0)


        styles = getSampleStyleSheet()

        normal_style = styles["Normal"]
        heading_style = styles["Heading1"]

        alert_style = ParagraphStyle(
            "AlertStyle",
            parent=styles["Normal"],
            textColor=colors.red
            )

        risk_db = {}

        try:
            with open("risk_db.json", "r") as f:
                risk_db = json.load(f)
        except FileNotFoundError:
            risk_db = {}


        conn = sqlite3.connect("audit.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO audit_history 
        (flow_id, user_id, role, timestamp, total_findings, high_risk, medium_risk, low_risk, total_exposure)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            flow_id,
            user_id,
            role,
            datetime.now(UTC).isoformat(),
            len(findings),
            high,
            medium,
            low,
            total_exposure
            ))

        conn.commit()
        conn.close()

        conn = sqlite3.connect("audit.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT timestamp, total_exposure 
        FROM audit_history
        WHERE user_id=?               
        ORDER BY id
        """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        timestamps = [r[0] for r in rows]
        exposures = [r[1] for r in rows]
        anomaly_detected = False
        root_cause= None


        z_score= None
        if len(exposures) > 1:
            df = pd.DataFrame({"exposure": exposures})
            findings_json_parsed = json.loads(findings_json)
            df_transactions = pd.DataFrame(findings_json_parsed)
            # Rolling Average (3-run window)
            df["rolling_avg"] = df["exposure"].rolling(window=3).mean()

            # Anomaly Detection (20% spike over average)
            mean_exposure = np.mean(exposures[:-1]) if len(exposures) > 1 else exposures[-1]
            std_exposure = np.std(exposures[:-1])
            upper_bound = mean_exposure + 2 * std_exposure
            lower_bound = mean_exposure - 2 * std_exposure
            current_exposure = exposures[-1]

            top_vendor="N/A"
            top_value=0
            if std_exposure > 0 and current_exposure > 1.2 * mean_exposure:
                z_score=(current_exposure - mean_exposure) / std_exposure
                
                if z_score>2:
                    anomaly_detected = True

            
                
               
            if  vendor_exposure:
                top_vendor = max(vendor_exposure, key=vendor_exposure.get)
                top_value = vendor_exposure[top_vendor]

            root_cause = f"Primary driver: {top_vendor} contributed ${top_value:,.0f}"

            plt.figure(figsize=(8, 5))
            plt.plot(range(len(exposures)), exposures, marker='o', label="Exposure")
            plt.plot(range(len(exposures)), df["rolling_avg"], linestyle="--", label="3-Run Avg")

            plt.xticks(range(len(timestamps)), timestamps, rotation=45)
            plt.title("Total Risk Exposure Over Time")
            plt.ylabel("Exposure ($)")
            plt.axhline(upper_bound, linestyle=":", label="+2σ Threshold")
            plt.axhline(lower_bound, linestyle=":", label="-2σ Threshold")

            plt.fill_between(
                range(len(exposures)),
                lower_bound,
                upper_bound,
                alpha=0.1
                )

            
            plt.legend()
            plt.grid(True, linestyle="--", alpha=0.4)
            plt.tight_layout()

            trend_chart_path = "risk_trend.png"
            plt.savefig(trend_chart_path, dpi=300)
            plt.close()
        else:
            trend_chart_path = None

        df_findings = pd.DataFrame(findings)

        if "category" in df_findings.columns:
            heatmap_df = df_findings.groupby(
                ["vendor", "category"]
                )["amount"].sum().unstack(fill_value=0)
        else:
            heatmap_df = None
        heatmap_path = None

        if heatmap_df is not None and not heatmap_df.empty:

            plt.figure(figsize=(8, 6))
            plt.imshow(heatmap_df, aspect='auto')
            plt.colorbar(label="Exposure ($)")

            plt.xticks(range(len(heatmap_df.columns)), heatmap_df.columns)
            plt.yticks(range(len(heatmap_df.index)), heatmap_df.index)

            plt.title("Vendor × Category Risk Heatmap")

            plt.tight_layout()

            heatmap_path = "vendor_category_heatmap.png"
            plt.savefig(heatmap_path, dpi=300)
            plt.close()
        # ---- Chart 1: Severity Distribution ----
        plt.figure(figsize=(8, 5))

        severity_colors = []
        for s in ["HIGH", "MEDIUM", "LOW"]:
            if s == "HIGH":
                severity_colors.append("#d62728")  # red
            elif s == "MEDIUM":
                severity_colors.append("#ff7f0e")  # orange
            else:
                severity_colors.append("#2ca02c")  # green

        bars = plt.bar(["HIGH", "MEDIUM", "LOW"], [high, medium, low], color=severity_colors)

        plt.title("Severity Distribution", fontsize=14, fontweight="bold")
        plt.xlabel("Severity")
        plt.ylabel("Number of Findings")
        plt.grid(axis="y", linestyle="--", alpha=0.5)

        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{int(height)}',
                ha='center', 
                va='bottom')

        severity_chart_path = "severity_distribution.png"
        plt.tight_layout()
        plt.savefig(severity_chart_path, dpi=300)
        plt.close()

        # ---- Chart 2: Vendor Exposure ----
        vendors = []
        exposures = []
        if vendor_exposure:
            sorted_vendors = sorted(vendor_exposure.items(), key=lambda x: x[1], reverse=True)
        
            vendors = [v[0] for v in sorted_vendors]
            exposures = [v[1] for v in sorted_vendors]

        plt.figure(figsize=(10, 6))

        vendor_colors = []
        for value in exposures:
            if value > 150000:
                vendor_colors.append("#d62728")  # red (critical exposure)
            elif value > 100000:
                vendor_colors.append("#ff7f0e")  # orange (moderate risk)
            else:
                vendor_colors.append("#2ca02c")  # green (lower exposure)

        vendor_scores = {}

        for vendor in vendor_exposure.keys():
            if total_exposure>0:
                exposure_score = vendor_exposure[vendor] / total_exposure
            else:
                exposure_score=0
            history_score = risk_db.get(vendor, {}).get("risk_score", 0) / 100

            composite_score = round((0.7 * exposure_score) + (0.3 * history_score), 3)
            vendor_scores[vendor] = composite_score
        
        
        top_vendor = None
        top_vendor_exposure = 0
        high_risk_vendors = 0

        if vendor_exposure:
            top_vendor = max(vendor_exposure, key=vendor_exposure.get)
            top_vendor_exposure = vendor_exposure[top_vendor]

        high_risk_vendors = high  # since HIGH severity is vendor-level in your model

        exposure_trend = "Stable"

        if len(exposures) > 1:
            if exposures[-1] > exposures[-2]:
                exposure_trend = "Increasing"
        elif exposures[-1] < exposures[-2]:
            exposure_trend = "Decreasing"
        
        bars = plt.bar(vendors, exposures, color=vendor_colors)

        plt.title("Vendor Risk Exposure (Sorted by Financial Impact)", 
          fontsize=14, fontweight="bold")
        plt.xlabel("Vendor")
        plt.ylabel("Total Exposure ($)")
        plt.xticks(rotation=45, ha="right")
        plt.grid(axis="y", linestyle="--", alpha=0.4)

        
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f"${height:,.0f}",
                ha='center',
                va='bottom',
                fontsize=9)

        plt.tight_layout()
        exposure_chart_path = "vendor_exposure.png"
        plt.savefig(exposure_chart_path, dpi=300)
        plt.close()


        

  # ---- PDF Generation ----
        pdf_path = "Enterprise_Compliance_Report.pdf"
        doc = SimpleDocTemplate(pdf_path)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("<b>Enterprise Financial Compliance Report</b>", styles["Title"]))
        elements.append(Spacer(1, 0.3 * inch))

        summary_data = [
            ["Total Findings", len(findings)],
            ["High Risk", high],
            ["Medium Risk", medium],
            ["Low Risk", low],
            ["Total Exposure", f"${total_exposure:,.2f}"]
        ]

        table = Table(summary_data)
        table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.5 * inch))

        if severity_chart_path and os.path.exists(severity_chart_path):
            elements.append(Image(severity_chart_path, width=6*inch, height=4*inch))
            elements.append(Spacer(1, 0.5 * inch))

        if exposure_chart_path and os.path.exists(exposure_chart_path):

            elements.append(Image(exposure_chart_path, width=6*inch, height=4*inch))
            elements.append(Spacer(1, 0.5 * inch))
        if trend_chart_path and os.path.exists(trend_chart_path):

            elements.append(Image(trend_chart_path, width=6*inch, height=4*inch))
            elements.append(Spacer(1, 0.5 * inch))

        if heatmap_path and os.path.exists(heatmap_path):
                elements.append(Spacer(1, 0.5 * inch))
                elements.append(Image(heatmap_path, width=6*inch, height=4*inch))

        
        if anomaly_detected:
            alert_style = ParagraphStyle(
                name='AlertStyle',
                fontSize=12,
                textColor=colors.red
            )

            elements.append(Spacer(1, 0.3 * inch))
            elements.append(
                Paragraph(
                    f"<b>⚠ Statistical Anomaly Detected:</b> "
                    f"Exposure Z-Score = {round(z_score,2)} (Threshold > 2.0)",
                    
                    alert_style
                )
            )
        if root_cause:
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(
                Paragraph(f"<b>Root Cause Attribution:</b> {root_cause}", normal_style)
            )

        doc.build(elements) 
        return f"""
        # Enterprise Financial Compliance Report
        ## Executive KPIs

        - **Total Risk Exposure:** ${total_exposure:,.2f}
        - **Total Findings:** {len(findings)}
        - **High Severity Vendors:** {high}
        - **Top Exposure Vendor:** {top_vendor} (${top_vendor_exposure:,.0f})
        - **Exposure Trend:** {exposure_trend}

        ---

        ## Report Summary

        Severity Breakdown:
        - HIGH: {high}
        - MEDIUM: {medium}
        - LOW: {low}
        PDF generated: {pdf_path}

        Charts included:
        - Severity Distribution
        - Vendor Risk Exposure

        Total Exposure: ${total_exposure:,.2f}
        """
    except Exception as e:
        return error_response("generate_audit_markdown_report", str(e))


# ==============================
# RESOURCE
# ==============================

@mcp.resource("db://schema")
async def database_schema_resource():
    try:
        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema = {}
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name});")
            cols = cursor.fetchall()
            schema[table_name] = [
                {"column": c[1], "type": c[2]}
                for c in cols
            ]

        conn.close()
        return json.dumps(schema, indent=2)

    except Exception as e:
        return error_response("database_schema_resource", str(e))


# ==============================
# PROMPT PRIMITIVE
# ==============================

@mcp.prompt()
async def compliance_audit_prompt():
    """
    Instruction template for structured compliance review.
    """

    return """
You are a Senior Financial Compliance Analyst.

- Group findings by severity.
- Provide recommended actions for HIGH severity.
- Maintain professional tone.
- Use only supplied data.
"""


# ==============================
# RUN (SSE)
# ==============================

if __name__ == "__main__":
    mcp.run(transport="http",host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
            )
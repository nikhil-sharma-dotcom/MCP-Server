import json
import asyncio
import os
import re
from fastmcp import Context
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime, UTC
from db import get_write_connection
from utils import raise_tool_error
from models.schemas import AuditReportRequest

matplotlib.use("Agg")
def _generate_report_sync(payload):
    findings = payload.findings
    flow_id = re.sub(r"[^a-zA-Z0-9_\-]","_",payload.flow_id)
    user_id = payload.user_id
    role = payload.role
    top_vendor = "N/A"
    top_vendor_exposure = 0
    
    REPORT_DIR = "reports"
    os.makedirs(REPORT_DIR, exist_ok=True)

    severity_counts = defaultdict(int)
    vendor_exposure = defaultdict(float)
    total_exposure = 0

    for item in findings:
        severity_counts[item.severity] += 1
        vendor_exposure[item.vendor] += float(item.amount)
        total_exposure += float(item.amount)

    high = severity_counts.get("HIGH", 0)
    medium = severity_counts.get("MEDIUM", 0)
    low = severity_counts.get("LOW", 0)


    styles = getSampleStyleSheet()

    normal_style = styles["Normal"]
        

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


    with get_write_connection() as conn:
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

        

    
        cursor.execute("""
        SELECT timestamp, total_exposure 
        FROM audit_history
        WHERE user_id=?               
        ORDER BY id
        """, (user_id,))

        rows = cursor.fetchall()
        
    df_findings = pd.DataFrame([f.model_dump() for f in findings])
    timestamps = [r[0] for r in rows]
    exposures = [r[1] for r in rows]
    anomaly_detected = False
    root_cause= None


    


    z_score= None
    if len(exposures) > 1:
        df = pd.DataFrame({"exposure": exposures})
            
        
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


            
       

        trend_chart_path = os.path.join(REPORT_DIR,f"{flow_id}_trend.png")
        plt.savefig(trend_chart_path, dpi=300)
        plt.close()
    else:
        trend_chart_path = None

    

    


    heatmap_path = None
    if "category" in df_findings.columns:
        heatmap_df = df_findings.groupby(
            ["vendor", "category"]
            )["amount"].sum().unstack(fill_value=0)
    else:
        heatmap_df = None
        

    if heatmap_df is not None and not heatmap_df.empty:

        plt.figure(figsize=(8, 6))
        plt.imshow(heatmap_df, aspect='auto')
        plt.colorbar(label="Exposure ($)")

        plt.xticks(range(len(heatmap_df.columns)), heatmap_df.columns)
        plt.yticks(range(len(heatmap_df.index)), heatmap_df.index)

        plt.title("Vendor × Category Risk Heatmap")

        plt.tight_layout()

        heatmap_path = os.path.join(REPORT_DIR, f"{flow_id}_heatmap.png")
        plt.savefig(heatmap_path, dpi=300)
        plt.close()
    # ---- Chart 1: Severity Distribution ----
    plt.figure(figsize=(8, 5))

    severity_colors = ["#d62728","#ff7f0e","#2ca02c"]
        
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

    severity_chart_path = os.path.join(REPORT_DIR, f"{flow_id}_severity_distribution.png")
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
        else:
            exposure_trend = "Stable"
        
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
    exposure_chart_path = os.path.join(REPORT_DIR, f"{flow_id}_vendor_exposure.png")
    plt.savefig(exposure_chart_path, dpi=300)
    plt.close()

        
        

    

  # ---- PDF Generation ----
    pdf_path = os.path.join(REPORT_DIR, f"{flow_id}_report.pdf")
    doc = SimpleDocTemplate(pdf_path)
    elements = []
        

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
        
    


async def generate_audit_markdown_report(payload: AuditReportRequest, ctx: Context) -> str:
    """
    Generates executive-level compliance report with charts and PDF export.
    """
    
    await ctx.report_progress(
        progress=5,
        message="Initializing compliance report generation"
    )


    try:
        await ctx.report_progress(
            progress=20,
            message="Analyzing transaction findings"
        )  

        await ctx.report_progress(
            progress=60,
            message="Generating analytics and charts"
        )
        result = await asyncio.to_thread(
            _generate_report_sync,
            payload
        )

        
        await ctx.report_progress(
            progress=100,
            message="Report generation completed"
        )
        return result
    except Exception as e:
        raise_tool_error("generate_audit_markdown_report", str(e))
    
    

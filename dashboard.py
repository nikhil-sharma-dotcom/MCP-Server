from fastapi import FastAPI
import sqlite3
from fastapi.responses import HTMLResponse
from jose import jwt
from datetime import datetime, timedelta, UTC
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from fastapi.templating import Jinja2Templates
from fastapi import Request
import pandas as pd
import plotly.express as px
import json
app = FastAPI()
templates = Jinja2Templates(directory="templates")
@app.get("/audit-history")
def get_audit_history():
    conn = sqlite3.connect("audit.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
def get_audit_data():
    conn = sqlite3.connect("audit.db")
    df = pd.read_sql_query("SELECT * FROM audit_history", conn)
    conn.close()
    return df

SECRET_KEY = "your_secret"
ALGORITHM = "HS256"

def create_token(username):
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


security = HTTPBearer()

@app.get("/secure-history")
def secure_history(token=Depends(security)):
    try:
        jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(status_code=403)
    return get_audit_history()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    df = get_audit_data()

    if df.empty:
        return HTMLResponse("<h2>No Audit Data Available</h2>")

    # Severity Distribution
    severity_fig = px.bar(
        x=["High", "Medium", "Low"],
        y=[
            df["high_risk"].sum(),
            df["medium_risk"].sum(),
            df["low_risk"].sum(),
        ],
        title="Severity Distribution"
    )
    severity_fig.update_layout(template="plotly_dark",
                               height=400,
                               margin=dict(l=40, r=40, t=60, b=40))

    # Exposure Trend
    trend_fig = px.line(
        df,
        x="timestamp",
        y="total_exposure",
        title="Exposure Over Time"
    )
    trend_fig.update_layout(template="plotly_dark",
                            height=400,
                            margin=dict(l=40, r=40, t=60, b=40))
    latest = df.iloc[-1]
    exposure_delta = None
    if len(df) > 1:
        previous = df.iloc[-2]["total_exposure"]
        exposure_delta = latest["total_exposure"] - previous


    kpis = {
            "total_findings": int(latest["total_findings"]),
            "high_risk": int(latest["high_risk"]),
            "medium_risk": int(latest["medium_risk"]),
            "low_risk": int(latest["low_risk"]),
            "total_exposure": latest["total_exposure"],
            "exposure_delta": exposure_delta,
            "last_run": latest["timestamp"]
            }



    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "severity_chart": severity_fig.to_json(),
            "trend_chart": trend_fig.to_json(),
            "kpis": kpis
        }
    )
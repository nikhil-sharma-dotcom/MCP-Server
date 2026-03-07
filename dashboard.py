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

import os
from jose.exceptions import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


app = FastAPI()

templates = Jinja2Templates(directory="templates")
if os.getenv("ENVIRONMENT")== "production":
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware    
    app.add_middleware(HTTPSRedirectMiddleware)
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response

app.add_middleware(SecurityHeadersMiddleware)

def get_client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host


limiter = Limiter(key_func=get_remote_address,
                  default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda r, e: JSONResponse(
    status_code=429,
    content={"error": "Rate limit exceeded"}
))
@app.get("/health")
def health():
    return {"status": "ok"}

DB_PATH = os.getenv("DB_PATH", "audit.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)
def fetch_audit_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT  flow_id, user_id, role,timestamp,
                   total_findings, high_risk, medium_risk, low_risk, total_exposure
                   FROM audit_history ORDER BY timestamp DESC""")
    columns = [c[0] for c in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows
def get_audit_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM audit_history", conn)
    conn.close()
    return df

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set")
ALGORITHM = "HS256"

def create_token(username: str, role: str):
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode({"sub": username,"role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    
security = HTTPBearer()

@app.get("/secure-history")
@limiter.limit("20/minute")
def secure_history(request: Request,token=Depends(security)):

    payload= verify_token(token.credentials)
    role= payload["role"]
    if role not in ["partner", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return fetch_audit_history()



@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, token=Depends(security)):
    verify_token(token.credentials)
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
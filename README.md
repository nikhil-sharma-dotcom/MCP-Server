# Enterprise Financial Compliance Audit Framework

[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-blue)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.0+-green)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/Python-3.12+-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-orange)](LICENSE)

> **AI-Native Compliance Infrastructure** — A production-grade MCP server that combines Large Language Models with structured financial analysis to automate enterprise compliance workflows.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Features](#features)
- [MCP Tools Reference](#mcp-tools-reference)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [API Usage](#api-usage)
- [Security Considerations](#security-considerations)
- [Technical Highlights](#technical-highlights)

---

## Overview

This project implements a **modular compliance audit system** built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). It enables AI agents to perform sophisticated financial compliance analysis through a standardized tool interface.

### Key Capabilities

- **Policy Validation Engine**: Multi-layer transaction analysis against configurable business rules
- **Risk Profiling**: Vendor risk assessment with external data enrichment
- **Automated Reporting**: Executive-grade PDF reports with statistical anomaly detection
- **LLM-Driven Orchestration**: Groq LLM integration for intelligent tool selection
- **Real-time Dashboard**: Interactive web visualization with role-based access control

### Use Case

Enterprise finance teams need to audit thousands of transactions across multiple vendors, checking for:
- Blacklisted vendor exposure
- Category spending limit violations
- Pending transaction aggregation risks
- Historical vendor risk patterns

This system automates that analysis pipeline end-to-end.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Host Client (host.py)                        │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │    │
│  │  │  Rate Limiter│  │  RBAC Engine │  │   Audit Logger           │  │    │
│  │  │  (1 req/sec) │  │(Role-based)  │  │   (RotatingFileHandler)  │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │              Groq LLM Integration (llama-3.3-70b)            │   │    │
│  │  │         • Tool Selection    • Argument Generation           │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTP/MCP Protocol
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP SERVER LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FastMCP Server (server.py)                        │    │
│  │                        Port: 8000                                    │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                     TOOLS (5)                                │   │    │
│  │  │  ┌─────────────────┐ ┌─────────────────┐ ┌────────────────┐ │   │    │
│  │  │  │validate_policy  │ │flag_high_value  │ │get_vendor_risk │ │   │    │
│  │  │  │    _tools()     │ │  _transactions()│ │    _profile()  │ │   │    │
│  │  │  └─────────────────┘ └─────────────────┘ └────────────────┘ │   │    │
│  │  │  ┌─────────────────┐ ┌─────────────────┐                     │   │    │
│  │  │  │enrich_transaction│ │generate_audit_  │                     │   │    │
│  │  │  │    _context()   │ │  _report()      │                     │   │    │
│  │  │  └─────────────────┘ └─────────────────┘                     │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                   RESOURCES (1)                              │   │    │
│  │  │              db://schema (Database Introspection)           │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                    PROMPTS (1)                               │   │    │
│  │  │           compliance_audit_prompt (System Template)         │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ SQL/JSON/Filesystem
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   SQLite     │  │  Static JSON │  │  Log Files   │  │  Generated      │  │
│  │  (audit.db)  │  │ (risk_db.json)│  │(JSONL format)│  │  Reports        │  │
│  │              │  │              │  │              │  │  (PDF/PNG)      │  │
│  │ • transactions│ │ • vendor_risk│  │ • audit_trace│  │                 │  │
│  │ • audit_hist │  │   _scores    │  │              │  │                 │  │
│  │ • vendor_risk│  │              │  │              │  │                 │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTP
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VISUALIZATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Dashboard (dashboard.py)                  │    │
│  │                        Port: 8000 (shared)                           │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │    │
│  │  │  JWT Auth       │  │  Plotly Charts  │  │   KPI Metrics       │  │    │
│  │  │  (Bearer Token) │  │  (Interactive)  │  │   (Real-time)       │  │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  Security Middleware: Rate Limiting, HSTS, X-Frame-Options  │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
MCP-Server/
├── server.py                 # MCP server entry point (73 lines)
├── host.py                   # LLM orchestrator with audit loop
├── dashboard.py              # FastAPI web dashboard with security
├── db/
│   ├── __init__.py
│   └── connection.py         # SQLite with WAL mode, connection pooling
├── models/                   # Pydantic schemas for validation
├── prompts/
│   └── compliance_audit.py   # MCP prompt templates
├── resources/
│   └── schema.py             # db://schema resource implementation
├── tools/                    # Modular MCP tools
│   ├── __init__.py
│   ├── validation_tools.py   # Policy validation, high-value flagging
│   ├── enrichment.py         # Vendor risk enrichment
│   └── reporting.py          # PDF report generation
├── utils/                    # Utility functions
├── templates/
│   └── dashboard.html        # Jinja2 dashboard template
├── requirements.txt
├── Dockerfile
└── .gitignore                # Properly excludes .env, *.db, etc.
```



## Features

### 1. Multi-Layer Policy Validation

```python
# Validates against:
- Blacklisted vendors (configurable set)
- Category spending limits (Legal: $25K, IT: $40K, Travel: $20K)
- Pending transaction aggregation ($50K threshold)
```

### 2. LLM-Driven Tool Selection

The host client uses Groq's Llama 3.3 70B model to:
- Select appropriate audit tools based on natural language queries
- Generate structured arguments for tool execution
- Reason about compliance findings

### 3. Statistical Anomaly Detection

```python
# Z-score based anomaly detection
if z_score > 2.0:
    flag_statistical_anomaly()
    perform_root_cause_analysis()
```

### 4. Risk Enrichment Pipeline

```
Raw Finding → Vendor Lookup → Risk Score Calculation → Enriched Output
     │              │                    │                    │
     ▼              ▼                    ▼                    ▼
  Transaction   risk_db.json    Weighted Algorithm    Final Report
```

### 5. Executive Reporting

- **PDF Generation**: ReportLab-based professional reports
- **Visualizations**: Matplotlib charts (severity distribution, exposure trends, heatmaps)
- **Markdown Export**: Structured text for further processing

### 6. Security Features

- **JWT Authentication**: Role-based tokens with expiration
- **Rate Limiting**: 60 requests/minute default, 20/minute for sensitive endpoints
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **HTTPS Enforcement**: Automatic redirect in production mode

---

## MCP Tools Reference

### Tool: `validate_transaction_policies`

Validates transactions against enterprise policies.

**Input:** None (queries all transactions)

**Output:**
```json
[
  {
    "severity": "HIGH",
    "issue": "Blacklisted Vendor",
    "vendor": "Fraudulent Corp",
    "category": "IT",
    "amount": 50000.00
  }
]
```

---

### Tool: `flag_high_value_transactions`

Flags transactions exceeding monetary threshold.

**Input:**
```json
{
  "min_amount": 10000.0
}
```

**Output:**
```json
[
  {
    "vendor": "LegalEdge LLP",
    "amount": 25000.00,
    "category": "Legal"
  }
]
```

---

### Tool: `get_vendor_risk_profile`

Retrieves historical transaction statistics for a vendor.

**Input:**
```json
{
  "vendor_name": "OfficeSupply Co"
}
```

**Output:**
```json
{
  "vendor": "OfficeSupply Co",
  "transaction_count": 45,
  "total_spend": 125000.00,
  "avg_transaction": 2777.78,
  "max_transaction": 15000.00
}
```

---

### Tool: `enrich_transaction_context`

Adds external risk context to vendor data.

**Input:**
```json
{
  "vendor_name": "OfficeSupply Co"
}
```

**Output:**
```json
{
  "vendor": "OfficeSupply Co",
  "past_issues": true,
  "conflict_of_interest": true,
  "regulatory_flag": false,
  "risk_score": 82
}
```

---

### Tool: `generate_audit_markdown_report`

Generates comprehensive compliance report.

**Input:**
```json
{
  "findings": [...],
  "flow_id": "AUDIT_a1b2c3d4",
  "user_id": "auditor_01",
  "role": "partner"
}
```

**Output:** Markdown string with embedded KPIs and chart references

---

### Resource: `db://schema`

Returns database schema for introspection.

**Output:**
```json
{
  "transactions": [
    {"column": "vendor", "type": "TEXT"},
    {"column": "amount", "type": "REAL"},
    {"column": "category", "type": "TEXT"},
    {"column": "status", "type": "TEXT"}
  ]
}
```

---

### Prompt: `compliance_audit_prompt`

System prompt for LLM-based compliance analysis.

**Content:**
```
You are a Senior Financial Compliance Analyst.
- Group findings by severity.
- Provide recommended actions for HIGH severity.
- Maintain professional tone.
- Use only supplied data.
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Groq API key

### Installation

```bash
# Clone repository
git clone https://github.com/nikhil-sharma-dotcom/MCP-Server.git
cd MCP-Server

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_API_KEY="your_groq_api_key"
export SECRET_KEY="your_jwt_secret_key"
export PORT=8000
export ENVIRONMENT=development  # or 'production' for HTTPS enforcement
```

### Running Locally

```bash
# Terminal 1: Start MCP Server
python server.py

# Terminal 2: Start Dashboard
uvicorn dashboard:app --host 0.0.0.0 --port 8000

# Terminal 3: Run Audit Workflow
python host.py
```

### Expected Output

```
MCP ready.
--- Enriched Audit Report ---

[LLM-generated compliance analysis]

--- Final Audit Markdown Report ---

# Enterprise Financial Compliance Report
## Executive KPIs
- **Total Risk Exposure:** $1,250,000.00
- **Total Findings:** 15
...
```

---

## Deployment

### Docker (Single Container)

```bash
# Build image
docker build -t mcp-audit-server .

# Run container
docker run -p 8000:8000 \
  -e GROQ_API_KEY="your_key" \
  -e SECRET_KEY="your_secret" \
  -e PORT=8000 \
  -e ENVIRONMENT=production \
  mcp-audit-server
```

### Docker Compose (Recommended)

```yaml
# docker-compose.yml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - PORT=8000
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
```

### Cloud Deployment (AWS)

```bash
# ECR Push
docker build -t mcp-audit-server .
docker tag mcp-audit-server:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mcp-audit-server:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mcp-audit-server:latest

# ECS/Fargate Deployment
# Use AWS Console or Terraform for production deployment
```

---

## API Usage

### MCP Server HTTP Endpoint

```bash
# List available tools
curl http://localhost:8000/mcp/tools

# Call a tool
curl -X POST http://localhost:8000/mcp/tools/flag_high_value_transactions \
  -H "Content-Type: application/json" \
  -d '{"min_amount": 10000}'
```

### Dashboard Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get audit history (with JWT)
curl http://localhost:8000/secure-history \
  -H "Authorization: Bearer <token>"

# View dashboard
curl http://localhost:8000/ \
  -H "Authorization: Bearer <token>"
```

### Programmatic Client

```python
from fastmcp import Client
import asyncio

async def audit_client():
    async with Client("http://localhost:8000/mcp") as session:
        # List tools
        tools = await session.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Call tool
        result = await session.call_tool(
            "flag_high_value_transactions",
            {"min_amount": 5000}
        )
        print(result)

asyncio.run(audit_client())
```

---

## Security Considerations

### Implemented Security Measures

| Feature | Implementation |
|---------|----------------|
| **Authentication** | JWT with role-based claims |
| **Rate Limiting** | slowapi (60/min default, 20/min sensitive) |
| **HTTPS** | Automatic redirect in production |
| **Security Headers** | HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection |
| **Secrets Management** | Environment variables only |
| **Logging** | RotatingFileHandler with 5MB rotation |

### Environment Variables

```bash
# Required
export GROQ_API_KEY="your_groq_api_key"
export SECRET_KEY="your_jwt_secret_min_32_chars"

# Optional
export PORT=8000                    # Server port
export ENVIRONMENT=development      # or 'production'
export DB_PATH="audit.db"           # Database path
```

### Known Limitations

1. **SQLite**: File-based database limits horizontal scaling
2. **SQL Injection**: Table name validation needed for schema resource
3. **No CSRF Protection**: Stateless JWT doesn't require CSRF, but cookie-based auth would



### The Refactoring Story

> "I took a 665-line monolithic MCP server and refactored it into a modular architecture with:
> - 73-line clean entry point
> - Proper package separation (tools/, db/, models/)
> - Environment-based configuration
> - Comprehensive security middleware
> - Professional logging with rotation"

This demonstrates **technical debt management** and **continuous improvement** — key senior-engineer traits.

---

## Technical Highlights

### 1. Modular MCP Server

```python
# server.py - Clean entry point (73 lines)
from fastmcp import FastMCP
from tools import ALL_TOOLS
from resources import database_schema_resource
from prompts import compliance_audit_prompt

mcp = FastMCP("Enterprise_Audit_Framework", version="2024-11-05")

# Register all tools with descriptions
for tool in ALL_TOOLS:
    mcp.tool(
        name=tool.__name__,
        description=TOOL_DESCRIPTIONS.get(tool.__name__)
    )(tool)

mcp.resource("db://schema")(database_schema_resource)
mcp.prompt()(compliance_audit_prompt)
```

### 2. Database Connection Management

```python
# db/connection.py - WAL mode for better concurrency
def get_write_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")  # Write-Ahead Logging
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn
```

### 3. Security Middleware

```python
# dashboard.py - Production-ready security
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
```

### 4. LLM-Driven Orchestration

```python
# host.py - Intelligent tool selection
response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Run full policy validation audit."}],
    tools=groq_tools,  # Dynamically generated from MCP tools
    tool_choice="auto"
)
```

### 5. Professional Logging

```python
# RotatingFileHandler for production
logger = logging.getLogger("audit")
handler = RotatingFileHandler(
    "audit_trace.log",
    maxBytes=5_000_000,  # 5MB rotation
    backupCount=5
)
logger.addHandler(handler)
```

---

## Contributing

This is a personal portfolio project. While not actively seeking contributions, feedback and suggestions are welcome via GitHub issues.

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) for the excellent MCP framework
- [Model Context Protocol](https://modelcontextprotocol.io/) for the protocol specification
- [Groq](https://groq.com/) for LLM inference

---

## Contact

**Nikhil Sharma**  
GitHub: [@nikhil-sharma-dotcom](https://github.com/nikhil-sharma-dotcom)


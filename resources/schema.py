import json
from db import get_read_only_connection
from utils import raise_tool_error

allowed_tables = {"transcations", "vendor_risk", "audit_history"}
async def database_schema_resource():
    try:
        conn = get_read_only_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema = {}
        
        for (table_name,) in tables:
            if table_name not in allowed_tables:
                continue
            cursor.execute(f"PRAGMA table_info({table_name});")
            cols = cursor.fetchall()
            schema[table_name] = [
                {"column": c[1], "type": c[2]}
                for c in cols
            ]

        conn.close()
        return json.dumps(schema, indent=2)

    except Exception as e:
        raise_tool_error("database_schema_resource", str(e))

import pytest
import sqlite3
import json
import os
from tools.validation_tools import validate_transaction_policies

@pytest.mark.asyncio
async def test_db_integration():
    
    os.makedirs("data", exist_ok=True)
    db_path = "data/test_audit.db"
    
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("CREATE TABLE transactions (vendor TEXT, amount REAL, category TEXT, status TEXT)")
    
    cursor.execute("INSERT INTO transactions VALUES ('Fraudulent Corp', 5000, 'Legal', 'Pending')")
    conn.commit()
    conn.close()

    
    result = await validate_transaction_policies()
    
    if isinstance(result, str):
        result = json.loads(result)

    
    assert result is not None
    assert isinstance(result, dict)
    assert result["count"] > 0
    assert any(f["issue"] == "Blacklisted Vendor" for f in result["findings"])
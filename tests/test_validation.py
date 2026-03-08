import pytest
import json
from unittest.mock import patch , MagicMock
from tools.validation_tools import validate_transaction_policies
@pytest.mark.asyncio
async def test_validate_transactions_runs():
    fake_conn = MagicMock()
    fake_cursor = MagicMock()

    fake_conn.cursor.return_value= fake_cursor
    fake_cursor.fetchall.return_value = [("Safe vendor",1000,"IT","completed"),
                                         ("Fradulent corp", 5000,"Legal", "pending")]

    
    with patch("tools.validation_tools.sqlite3.connect", return_value=fake_conn):
            result =  await validate_transaction_policies()
            print(f"DEBUG RESULT: {result}")
            if isinstance(result, str):
                  result = json.loads(result)

    assert result is not None
    assert isinstance(result, dict)
    assert "findings" in result
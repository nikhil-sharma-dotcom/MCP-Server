import asyncio
from unittest.mock import patch
from host import run_audit

def test_full_audit_pipeline(mocker):
    """
    Runs the full audit pipeline and 
    ensures it completes without errors.
    
    """
    with patch("host.wait_for_mcp",return_value=None),\
         patch("host.safe_call_tool",return_value={"findings":[]}), \
         patch("host.Client"):
        asyncio.run(run_audit())

    assert True
    

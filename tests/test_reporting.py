import pytest
from unittest.mock import patch, MagicMock

from tools.reporting import generate_audit_markdown_report

class MockPayLoad:
    findings= []
    flow_id="TEST_AUDIT"
    user_id= "auditor_01"
    role= "partner"
    total_findings= 0
    high_risk= 0
    medium_risk= 0
    low_risk= 0
    total_exposure= 0

class MockContext:
    async def report_progress(self, progress, message):
        pass
    
@pytest.mark.asyncio
async def test_generate_audit_report():
    fake_conn = MagicMock()

    payload = MockPayLoad()
    ctx= MockContext()
    
    with patch("tools.reporting.sqlite3.connect",return_value=fake_conn):
        report= await generate_audit_markdown_report(payload,ctx)

    assert report is not None
    assert isinstance(report, str)
    assert "Enterprise Financial Compliance Report" in report
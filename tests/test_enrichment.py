import pytest

from tools.enrichment import enrich_transaction_context


class MockPayload:
    vendor_name = "LegalEdge LLP"


@pytest.mark.asyncio
async def test_enrichment_tool_runs():



    payload = MockPayload()
    

    
    result = await enrich_transaction_context(payload)

    assert result is not None
    
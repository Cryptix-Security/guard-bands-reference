import asyncio

from guardbands.integrations.mcp import MCP_GUARD_BAND_ID

from integrations.mcp_demo import run_demo


def test_mcp_reference_demo_uses_split_keys_and_visible_output_boundary():
    result = asyncio.run(run_demo("refund requested"))

    assert result.structured_content["query"] == "refund requested"
    assert result.structured_content["matches"][0]["ticket_id"] == "TICKET-1042"
    assert result.content[0].text.startswith("⟪INERT:START:v:1:")
    assert "Ignore previous instructions" in result.content[0].text
    assert result.content[0].text.endswith("⟫")
    assert MCP_GUARD_BAND_ID in result.meta

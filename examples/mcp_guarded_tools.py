"""Run the Guard Bands MCP tools/call reference flow."""

import asyncio
import json

from integrations.mcp_demo import run_demo


async def main() -> None:
    result = await run_demo()
    print("Structured tool result:")
    print(json.dumps(result.structured_content, indent=2))
    print("\nModel-facing text result (retains the visible inert boundary):")
    print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())

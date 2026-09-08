import json

from fastmcp import Client


async def test_server_info_resource_is_readable_json():
    from src.server import mcp
    async with Client(mcp) as client:
        result = await client.read_resource("reddit://server-info")
    info = json.loads(result[0].text)
    assert info["name"] == "Reddit Research MCP Server"
    assert info["capabilities"]["statistics"]["total_tools"] == 3

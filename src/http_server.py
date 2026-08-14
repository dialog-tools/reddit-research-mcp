"""HTTP entrypoint for hosted deployments (Render).

The stdio entrypoint (`src.server:main`) remains the interface for local and
uvx-installed clients. This module serves the same FastMCP instance over
streamable HTTP, binding to the host/port the platform provides. The public
`/health` route used by the platform's health checks is defined in
`src.server` alongside the other custom routes.
"""

import os

from src.server import mcp


def main() -> None:
    mcp.run(
        transport="http",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )


if __name__ == "__main__":
    main()

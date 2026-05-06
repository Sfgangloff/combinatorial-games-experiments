"""
Experiment condition definitions and MCP-server config builders.

A Condition picks one cell of the 2x2 (toolset on/off) x (meta on/off) matrix,
where toolset-on subdivides into fine/medium/coarse. The 'judge' server is
always present.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO / ".venv" / "bin" / "python"


Toolset = Literal["none", "fine", "medium", "coarse"]


@dataclass(frozen=True)
class Condition:
    toolset: Toolset
    meta: bool
    meta_tools_config: dict | None = None  # explicit McpStdioServerConfig if meta=True

    @property
    def name(self) -> str:
        return f"toolset-{self.toolset}_meta-{'on' if self.meta else 'off'}"


def _stdio(server_dir: str) -> dict:
    """McpStdioServerConfig for one of our local servers."""
    return {
        "type": "stdio",
        "command": str(VENV_PYTHON),
        "args": [str(REPO / "servers" / server_dir / "server.py")],
    }


def mcp_servers_for(condition: Condition) -> dict[str, dict]:
    """Build the mcp_servers dict for a given Condition. Judge is always included."""
    servers: dict[str, dict] = {
        "slitherlink-judge": _stdio("slitherlink-judge"),
    }
    if condition.toolset != "none":
        servers[f"slitherlink-{condition.toolset}"] = _stdio(
            f"slitherlink-{condition.toolset}"
        )
    if condition.meta and condition.meta_tools_config is not None:
        servers["meta-tools"] = condition.meta_tools_config
    return servers


def allowed_tool_globs_for(condition: Condition) -> list[str]:
    """Allowed-tool patterns covering every server we expose."""
    return [f"mcp__{name}__*" for name in mcp_servers_for(condition).keys()]


ALL_CONDITIONS: list[Condition] = [
    Condition(toolset="none", meta=False),
    Condition(toolset="none", meta=True),
    Condition(toolset="fine", meta=False),
    Condition(toolset="fine", meta=True),
    Condition(toolset="medium", meta=False),
    Condition(toolset="medium", meta=True),
    Condition(toolset="coarse", meta=False),
    Condition(toolset="coarse", meta=True),
]

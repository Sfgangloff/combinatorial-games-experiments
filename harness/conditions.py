"""
Experiment condition definitions and MCP-server config builders.

A Condition picks one cell of the 2x2 (toolset on/off) x (meta on/off) matrix,
where toolset-on subdivides into fine/medium/coarse. The 'judge' server is
always present.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO / ".venv" / "bin" / "python"


Toolset = Literal["none", "fine", "medium", "coarse", "scratchpad"]


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


def discover_meta_tools_config() -> dict | None:
    """
    Look up the meta-tools MCP server from `claude mcp get meta-tools` and
    return an McpStdioServerConfig for it. Returns None if the CLI isn't
    available or meta-tools isn't configured.
    """
    if shutil.which("claude") is None:
        return None
    try:
        out = subprocess.run(
            ["claude", "mcp", "get", "meta-tools"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if out.returncode != 0:
        return None
    text = out.stdout
    type_match = re.search(r"Type:\s*(\S+)", text)
    cmd_match = re.search(r"Command:\s*(.+)", text)
    args_match = re.search(r"Args:\s*(.*)", text)
    if not (type_match and cmd_match and args_match):
        return None
    if type_match.group(1).strip().lower() != "stdio":
        return None
    args_str = args_match.group(1).strip()
    args = args_str.split() if args_str else []
    return {
        "type": "stdio",
        "command": cmd_match.group(1).strip(),
        "args": args,
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
    if condition.meta:
        cfg = condition.meta_tools_config or discover_meta_tools_config()
        if cfg is not None:
            servers["meta-tools"] = cfg
    return servers


def allowed_tool_globs_for(condition: Condition) -> list[str]:
    """Allowed-tool patterns covering every server we expose."""
    return [f"mcp__{name}__*" for name in mcp_servers_for(condition).keys()]


ALL_CONDITIONS: list[Condition] = [
    Condition(toolset="none", meta=False),
    Condition(toolset="fine", meta=False),
    Condition(toolset="medium", meta=False),
    Condition(toolset="coarse", meta=False),
]
# meta=True cells removed 2026-05-21: see memory
# meta-axis-dropped-cost-infeasible (two fair-test attempts burned
# $39.18 on subscription compute without completing). The meta axis
# is footnote/appendix only; --meta-probe still works for isolated runs.

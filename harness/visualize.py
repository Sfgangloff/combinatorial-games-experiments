"""
Render a results JSON (or a directory of them) as standalone HTML.

CLI:
    python -m harness.visualize harness/results/<file>.json
    python -m harness.visualize harness/results/        # all JSONs + index.html
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


CSS = """
:root {
  --bg: #fafafa; --panel: #fff; --border: #e1e4e8; --muted: #6a737d;
  --think: #f6f8fa; --think-fg: #586069;
  --text-fg: #24292e;
  --tool-call: #eef6ff; --tool-call-bd: #bcd9ff;
  --tool-result: #f0fff4; --tool-result-bd: #b8e6c5;
  --tool-result-err: #fff5f5; --tool-result-err-bd: #ffc1c1;
  --system: #fffaf0; --system-bd: #f0d999;
  --warn: #fff8e1; --warn-bd: #ffd54f;
}
* { box-sizing: border-box; }
body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, sans-serif;
       background: var(--bg); color: var(--text-fg); margin: 0; padding: 24px; }
.wrap { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 18px; margin: 0 0 4px; }
.meta { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
.meta b { color: var(--text-fg); }
.turn { background: var(--panel); border: 1px solid var(--border);
        border-radius: 6px; margin-bottom: 12px; padding: 10px 14px; }
.turn-h { font-weight: 600; font-size: 12px; color: var(--muted);
          text-transform: uppercase; letter-spacing: 0.04em; cursor: pointer;
          user-select: none; }
.turn-h::before { content: "▾ "; display: inline-block; width: 14px; }
.turn.collapsed .turn-h::before { content: "▸ "; }
.turn.collapsed .turn-body { display: none; }
.turn-body { margin-top: 8px; }
.block { padding: 8px 12px; border-radius: 4px; margin: 6px 0;
         border: 1px solid transparent; }
.block-h { font-size: 11px; font-weight: 600; text-transform: uppercase;
           letter-spacing: 0.05em; opacity: 0.7; margin-bottom: 4px; }
.thinking { background: var(--think); color: var(--think-fg);
            font-style: italic; white-space: pre-wrap; }
.text { white-space: pre-wrap; }
.tool-block { background: var(--tool-call); border: 1px solid var(--tool-call-bd);
              border-radius: 4px; padding: 8px 12px; margin: 6px 0; }
.tool-block.err { background: var(--tool-result-err); border-color: var(--tool-result-err-bd); }
.tool-line { display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
             font-size: 13px; line-height: 1.6; }
.tool-name { font-family: SF Mono, Monaco, monospace; font-weight: 600;
             font-size: 13px; color: #1f4d8a; }
.call-args { font-family: SF Mono, Monaco, monospace; color: #444;
             background: rgba(255,255,255,0.6); padding: 1px 6px;
             border-radius: 3px; }
.result-arrow { color: var(--muted); font-weight: 600; }
.result-summary { font-family: SF Mono, Monaco, monospace; color: #1a7f37;
                  background: rgba(208, 244, 221, 0.6); padding: 1px 6px;
                  border-radius: 3px; }
.result-summary.err { color: #b42318; background: rgba(255, 209, 209, 0.6); }
.grid-wrap { margin: 8px 0 4px; display: flex; align-items: center; gap: 12px; }
.grid-label { font-size: 11px; text-transform: uppercase; color: var(--muted);
              letter-spacing: 0.05em; }
.sl-grid { background: white; border: 1px solid var(--border); border-radius: 3px; }
.tool-raw { margin-top: 6px; }
.tool-raw summary { font-size: 11px; color: var(--muted); cursor: pointer;
                    user-select: none; padding: 2px 0; }
.tool-raw summary:hover { color: var(--text-fg); }
.raw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px; }
pre { font: 12px/1.45 SF Mono, Monaco, monospace; margin: 4px 0;
      white-space: pre-wrap; word-break: break-word; max-height: 320px;
      overflow: auto; background: rgba(0,0,0,0.03); padding: 6px 8px;
      border-radius: 3px; }
.system { background: var(--system); border-color: var(--system-bd); }
.warn { background: var(--warn); border-color: var(--warn-bd); }
.result-final { background: #f6f8fa; border-color: var(--border);
                font-family: SF Mono, Monaco, monospace; font-size: 13px; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 10px;
         font-size: 11px; font-weight: 600; margin-left: 6px; }
.badge.ok { background: #d4f4dd; color: #1a7f37; }
.badge.no { background: #ffd6d6; color: #b42318; }
.tool-num { color: var(--muted); font-size: 11px; margin-right: 6px; }
a { color: #0366d6; }
table.idx { border-collapse: collapse; width: 100%; margin-top: 14px; }
table.idx th, table.idx td { padding: 6px 10px; border-bottom: 1px solid var(--border);
                              text-align: left; font-size: 13px; }
table.idx th { background: var(--panel); font-weight: 600; }
"""

JS = """
document.querySelectorAll('.turn-h').forEach(h => {
  h.addEventListener('click', () => h.parentElement.classList.toggle('collapsed'));
});
document.getElementById('collapse-all')?.addEventListener('click', () => {
  document.querySelectorAll('.turn').forEach(t => t.classList.add('collapsed'));
});
document.getElementById('expand-all')?.addEventListener('click', () => {
  document.querySelectorAll('.turn').forEach(t => t.classList.remove('collapsed'));
});
"""


def esc(s: Any) -> str:
    return html.escape(str(s))


def fmt_json(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def short_tool(name: str) -> str:
    # mcp__slitherlink-medium__apply_edge → slitherlink-medium · apply_edge
    m = re.match(r"mcp__([^_]+(?:-[^_]+)*)__(.+)", name)
    if m:
        return f"{m.group(1)} · {m.group(2)}"
    return name


def short_name(name: str) -> str:
    return name.rsplit("__", 1)[-1]


# --- slitherlink ASCII parser + SVG renderer --------------------------------

def parse_slitherlink_ascii(ascii_str: str) -> dict | None:
    """Parse the slitherlink ASCII format used by the MCP servers.

    Format: 2*n_rows + 1 lines. Even lines are dot rows
    (`+---+   + x +`), odd lines are cell rows (`| 3   . x 2 |`).
    """
    if not isinstance(ascii_str, str):
        return None
    lines = ascii_str.rstrip("\n").split("\n")
    if len(lines) < 3 or len(lines) % 2 == 0:
        return None
    if not lines[0].strip().startswith("+"):
        return None
    n_rows = (len(lines) - 1) // 2
    n_cols = (len(lines[0].rstrip()) - 1) // 4
    if n_cols < 1:
        return None

    h_edges = [["unknown"] * n_cols for _ in range(n_rows + 1)]
    v_edges = [["unknown"] * (n_cols + 1) for _ in range(n_rows)]
    cells = [["."] * n_cols for _ in range(n_rows)]

    def edge_state(seg: str, vertical: bool) -> str:
        if vertical:
            ch = seg[:1]
            if ch == "|":
                return "line"
            if ch == "x":
                return "blocked"
            return "unknown"
        if "---" in seg:
            return "line"
        if "x" in seg:
            return "blocked"
        return "unknown"

    for i, line in enumerate(lines):
        if i % 2 == 0:  # dot row
            r = i // 2
            for c in range(n_cols):
                seg = line[1 + 4 * c : 4 + 4 * c]
                h_edges[r][c] = edge_state(seg, vertical=False)
        else:  # cell row
            r = i // 2
            for c in range(n_cols + 1):
                ch = line[4 * c : 4 * c + 1] if 4 * c < len(line) else " "
                v_edges[r][c] = edge_state(ch, vertical=True)
            for c in range(n_cols):
                seg = line[1 + 4 * c : 4 + 4 * c]
                if len(seg) >= 2:
                    val = seg[1].strip()
                    if val and val != ".":
                        cells[r][c] = val
    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "cells": cells,
        "h_edges": h_edges,
        "v_edges": v_edges,
    }


def slitherlink_svg(
    grid: dict,
    cell: int = 32,
    highlights: set[tuple[str, int, int]] | None = None,
) -> str:
    n_r, n_c = grid["n_rows"], grid["n_cols"]
    pad = 14
    w = n_c * cell + 2 * pad
    h = n_r * cell + 2 * pad
    hl = highlights or set()
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" class="sl-grid">'
        f'<rect width="{w}" height="{h}" fill="white"/>'
    ]
    # numbers in cells
    for r in range(n_r):
        for c in range(n_c):
            v = grid["cells"][r][c]
            if v != ".":
                cx = pad + c * cell + cell / 2
                cy = pad + r * cell + cell / 2
                out.append(
                    f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                    f'dominant-baseline="central" font-size="14" '
                    f'font-family="-apple-system,sans-serif" fill="#222">{v}</text>'
                )
    # horizontal edges
    for r in range(n_r + 1):
        for c in range(n_c):
            state = grid["h_edges"][r][c]
            is_hl = ("H", r, c) in hl
            x1 = pad + c * cell
            x2 = pad + (c + 1) * cell
            y = pad + r * cell
            if is_hl and state != "unknown":
                out.append(
                    f'<rect x="{x1}" y="{y - 6}" width="{cell}" height="12" '
                    f'fill="#fff3a8" rx="2"/>'
                )
            if state == "line":
                color = "#0b5ed7" if is_hl else "#1a73e8"
                out.append(
                    f'<line x1="{x1 + 3}" y1="{y}" x2="{x2 - 3}" y2="{y}" '
                    f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
                )
            elif state == "blocked":
                cx = (x1 + x2) / 2
                color = "#a51717" if is_hl else "#c33"
                out.append(
                    f'<g stroke="{color}" stroke-width="1.8">'
                    f'<line x1="{cx - 3}" y1="{y - 3}" x2="{cx + 3}" y2="{y + 3}"/>'
                    f'<line x1="{cx - 3}" y1="{y + 3}" x2="{cx + 3}" y2="{y - 3}"/></g>'
                )
    # vertical edges
    for r in range(n_r):
        for c in range(n_c + 1):
            state = grid["v_edges"][r][c]
            is_hl = ("V", r, c) in hl
            y1 = pad + r * cell
            y2 = pad + (r + 1) * cell
            x = pad + c * cell
            if is_hl and state != "unknown":
                out.append(
                    f'<rect x="{x - 6}" y="{y1}" width="12" height="{cell}" '
                    f'fill="#fff3a8" rx="2"/>'
                )
            if state == "line":
                color = "#0b5ed7" if is_hl else "#1a73e8"
                out.append(
                    f'<line x1="{x}" y1="{y1 + 3}" x2="{x}" y2="{y2 - 3}" '
                    f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
                )
            elif state == "blocked":
                cy = (y1 + y2) / 2
                color = "#a51717" if is_hl else "#c33"
                out.append(
                    f'<g stroke="{color}" stroke-width="1.8">'
                    f'<line x1="{x - 3}" y1="{cy - 3}" x2="{x + 3}" y2="{cy + 3}"/>'
                    f'<line x1="{x - 3}" y1="{cy + 3}" x2="{x + 3}" y2="{cy - 3}"/></g>'
                )
    # dots on top
    for r in range(n_r + 1):
        for c in range(n_c + 1):
            cx = pad + c * cell
            cy = pad + r * cell
            out.append(f'<circle cx="{cx}" cy="{cy}" r="1.8" fill="#666"/>')
    out.append("</svg>")
    return "".join(out)


# --- running grid state across a trajectory ---------------------------------


class GridState:
    """Shadow board updated turn-by-turn from tool calls/results.

    Initial state comes from a `get_puzzle.grid_text` or `render.ascii`.
    Mutations come from `apply_edge`/`apply_move`/`set_edge` (input + result
    `changes` list) or full re-syncs from `render`/`state` ascii.
    """

    def __init__(self) -> None:
        self.grid: dict | None = None
        self.last_changes: list[tuple[str, int, int]] = []

    def _set(self, et: str, r: int, c: int, new_state: str) -> None:
        if not self.grid:
            return
        try:
            r, c = int(r), int(c)
        except Exception:
            return
        if et == "H":
            if 0 <= r < len(self.grid["h_edges"]) and 0 <= c < len(self.grid["h_edges"][0]):
                self.grid["h_edges"][r][c] = new_state
                self.last_changes.append(("H", r, c))
        elif et == "V":
            if 0 <= r < len(self.grid["v_edges"]) and 0 <= c < len(self.grid["v_edges"][0]):
                self.grid["v_edges"][r][c] = new_state
                self.last_changes.append(("V", r, c))

    def update(self, name: str, inp: Any, parsed: Any) -> bool:
        """Apply this turn's tool call to the running state.

        Returns True if state was modified or initialized this turn.
        """
        self.last_changes = []
        short = short_name(name)

        # Full resync from any ascii field in the result.
        ascii_str = extract_grid_ascii(parsed) if parsed is not None else None
        if ascii_str:
            gp = parse_slitherlink_ascii(ascii_str)
            if gp:
                self.grid = gp
                return True

        # Initialize from get_puzzle even if we already have a grid (no-op if unchanged).
        if short == "get_puzzle" and isinstance(parsed, dict):
            gt = parsed.get("grid_text")
            if isinstance(gt, str):
                gp = parse_slitherlink_ascii(gt)
                if gp:
                    self.grid = gp
                    return True

        # changes-list mutators.
        if isinstance(parsed, dict) and short in ("apply_edge", "apply_move"):
            ch = parsed.get("changes") or []
            applied = False
            for c in ch:
                if isinstance(c, dict):
                    self._set(
                        c.get("edge_type", ""),
                        c.get("row", -1),
                        c.get("col", -1),
                        c.get("new_state", "unknown"),
                    )
                    applied = True
            # If the result had no changes (e.g. edge already at that state),
            # still apply the input as a no-op highlight.
            if not applied and isinstance(inp, dict):
                self._set(
                    inp.get("edge_type", ""),
                    inp.get("row", -1),
                    inp.get("col", -1),
                    inp.get("value", "unknown"),
                )
            return True

        if short == "set_edge" and isinstance(inp, dict):
            self._set(
                inp.get("edge_type", ""),
                inp.get("row", -1),
                inp.get("col", -1),
                inp.get("value", "unknown"),
            )
            return True

        # forced_moves is a query, not a mutation; the next apply_* call
        # will apply (and highlight) the same edges, so don't double-show.
        return False


# --- per-tool call/result one-line summarizers -----------------------------

def format_call_summary(name: str, inp: Any) -> str:
    if not isinstance(inp, dict):
        return ""
    short = short_name(name)
    if short in ("apply_edge", "set_edge", "apply_move"):
        return f"{inp.get('edge_type','?')}[{inp.get('row','?')}][{inp.get('col','?')}] = {inp.get('value','?')}"
    if short == "get_puzzle":
        return inp.get("puzzle_id", "")
    if short == "load":
        gt = inp.get("grid_text", "")
        return f"grid_text ({len(gt)} chars)"
    if short == "submit_solution":
        return inp.get("puzzle_id", "")
    if "handle" in inp and len(inp) == 1:
        return f"handle={str(inp['handle'])[:8]}"
    if "handle" in inp:
        rest = {k: v for k, v in inp.items() if k != "handle"}
        return ", ".join(f"{k}={v}" for k, v in rest.items())
    return ", ".join(f"{k}={v}" for k, v in inp.items())[:80]


def format_result_summary(name: str, parsed: Any) -> str:
    if not isinstance(parsed, dict):
        return ""
    short = short_name(name)
    if short in ("apply_edge", "apply_move"):
        ch = parsed.get("changes") or []
        contradiction = parsed.get("contradiction")
        user_moves = sum(1 for c in ch if c.get("reason") == "user move")
        forced = len(ch) - user_moves
        s = f"{len(ch)} edges changed"
        if forced:
            s += f" ({user_moves} user + {forced} forced)"
        if contradiction:
            s += f" — CONTRADICTION: {contradiction}"
        return s
    if short == "set_edge":
        return f"previous: {parsed.get('previous', '?')}"
    if short == "forced_moves":
        ch = parsed.get("changes") or []
        return f"{len(ch)} edges forced"
    if short == "suggest_next_move":
        m = parsed.get("move") or {}
        if m:
            return (
                f"→ {m.get('edge_type')}[{m.get('row')}][{m.get('col')}] = "
                f"{m.get('value')} ({parsed.get('method','')})"
            )
        return "(no move)"
    if short == "solved":
        return "✓ solved" if parsed.get("solved") else "✗ unsolved"
    if short == "submit_solution":
        return "✓ correct" if parsed.get("correct") else "✗ incorrect"
    if short == "load":
        sm = parsed.get("summary") or parsed
        return f"{sm.get('num_rows','?')}×{sm.get('num_cols','?')} grid · handle={str(parsed.get('handle',''))[:8]}"
    if short == "get_puzzle":
        return f"puzzle: {parsed.get('puzzle_id','')}"
    return ""


def extract_grid_ascii(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return None
    for key in ("ascii", "grid_text"):
        v = parsed.get(key)
        if isinstance(v, str) and v.strip().startswith("+"):
            return v
    return None


def parse_result_text(res: dict | None) -> tuple[Any, str, bool]:
    """Return (parsed_obj_or_None, raw_text, is_error)."""
    if not res:
        return None, "", False
    is_error = bool(res.get("is_error"))
    raw = res.get("content")
    text = ""
    if isinstance(raw, list) and raw:
        item = raw[0]
        if isinstance(item, dict):
            text = item.get("text", "") or ""
        else:
            text = str(item)
    elif isinstance(raw, str):
        text = raw
    elif raw is not None:
        text = str(raw)
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    return parsed, text, is_error


def collect_tool_results(messages: list[dict]) -> dict[str, dict]:
    """Map tool_use_id → {content, is_error} from user messages."""
    out: dict[str, dict] = {}
    for m in messages:
        if m.get("role") != "user":
            continue
        content = m.get("content", [])
        if not isinstance(content, list):
            continue
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_result":
                out[c.get("tool_use_id", "")] = {
                    "content": c.get("content"),
                    "is_error": bool(c.get("is_error")),
                }
    return out


def render_block_thinking(text: str) -> str:
    if not text.strip():
        return ""
    return f'<div class="block thinking"><div class="block-h">thinking</div>{esc(text)}</div>'


def render_block_text(text: str) -> str:
    if not text.strip():
        return ""
    return f'<div class="block text"><div class="block-h">assistant</div>{esc(text)}</div>'


def render_tool_pair(
    tool_use: dict,
    results: dict[str, dict],
    idx: int,
    state: GridState,
) -> str:
    tu_id = tool_use.get("id", "")
    name = tool_use.get("name", "")
    short = short_name(name)
    inp = tool_use.get("input", {}) or {}
    parsed, raw_text, is_error = parse_result_text(results.get(tu_id))

    call_args = format_call_summary(name, inp)
    result_summary = format_result_summary(name, parsed)
    if not result_summary and is_error:
        result_summary = "ERROR"

    # Update the shadow board for this turn.
    state.update(name, inp, parsed)

    # Decide whether/what grid to draw for this turn.
    svg_html = ""
    grid_label = ""

    # `submit_solution` shows the *submitted* solution, which may differ from
    # the running state (if the model reformatted it).
    if short == "submit_solution":
        gt = inp.get("grid_text") if isinstance(inp, dict) else None
        if isinstance(gt, str):
            gp = parse_slitherlink_ascii(gt)
            if gp:
                svg_html = slitherlink_svg(gp)
                grid_label = "submitted"
    # If the result itself contained a fresh ascii (render/state/get_puzzle),
    # state.grid was already replaced by it; just render state.
    # Otherwise, only draw if this turn touched state OR previewed forced moves.
    elif state.grid and (
        state.last_changes or short in ("get_puzzle", "render", "state")
    ):
        if short in ("render", "state"):
            grid_label = "current state"
        elif short == "get_puzzle":
            grid_label = "puzzle"
        else:
            grid_label = "after move"
        svg_html = slitherlink_svg(
            state.grid, highlights=set(state.last_changes)
        )

    head_parts = [
        f'<span class="tool-num">#{idx}</span>',
        f'<span class="tool-name">{esc(short_tool(name))}</span>',
    ]
    if call_args:
        head_parts.append(f'<span class="call-args">({esc(call_args)})</span>')
    if result_summary:
        head_parts.append('<span class="result-arrow">→</span>')
        cls = "result-summary err" if is_error else "result-summary"
        head_parts.append(f'<span class="{cls}">{esc(result_summary)}</span>')

    head = '<div class="tool-line">' + " ".join(head_parts) + "</div>"

    grid_block = ""
    if svg_html:
        grid_block = (
            f'<div class="grid-wrap">'
            f'<div class="grid-label">{esc(grid_label)}</div>{svg_html}</div>'
        )

    raw_call = fmt_json(inp) if inp else ""
    if parsed is not None:
        raw_result = fmt_json(parsed)
    else:
        raw_result = raw_text or "(no result captured)"
    raw_block = (
        '<details class="tool-raw"><summary>raw call + result</summary>'
        '<div class="raw-grid">'
        f'<div><div class="block-h">input</div><pre>{esc(raw_call)}</pre></div>'
        f'<div><div class="block-h">result{" · ERROR" if is_error else ""}</div>'
        f'<pre>{esc(raw_result)}</pre></div>'
        "</div></details>"
    )

    cls = "tool-block err" if is_error else "tool-block"
    return f'<div class="{cls}">{head}{grid_block}{raw_block}</div>'


def render_assistant(
    msg: dict,
    results: dict[str, dict],
    counter: list[int],
    state: GridState,
) -> str:
    parts: list[str] = []
    for c in msg.get("content", []):
        t = c.get("type")
        if t == "thinking":
            parts.append(render_block_thinking(c.get("thinking", "")))
        elif t == "text":
            parts.append(render_block_text(c.get("text", "")))
        elif t == "tool_use":
            counter[0] += 1
            parts.append(render_tool_pair(c, results, counter[0], state))
    body = "\n".join(p for p in parts if p)
    if not body:
        return ""
    return (
        '<div class="turn">'
        '<div class="turn-h">Assistant turn</div>'
        f'<div class="turn-body">{body}</div>'
        '</div>'
    )


def render_unknown(msg: dict) -> str:
    repr_str = msg.get("repr", "")
    return (
        '<div class="turn collapsed">'
        '<div class="turn-h">SDK event</div>'
        f'<div class="turn-body"><div class="block warn"><pre>{esc(repr_str)}</pre></div></div>'
        '</div>'
    )


def render_system(msg: dict) -> str:
    data = msg.get("data", {})
    tools = data.get("tools", [])
    servers = data.get("mcp_servers", [])
    summary = (
        f"<b>model:</b> {esc(data.get('model'))} · "
        f"<b>session:</b> {esc(data.get('session_id',''))[:12]} · "
        f"<b>{len(tools)} tools</b> from <b>{len(servers)} MCP servers</b>"
    )
    return (
        '<div class="turn collapsed">'
        '<div class="turn-h">System init</div>'
        f'<div class="turn-body"><div class="block system">{summary}'
        f'<pre>{esc(fmt_json({"tools": tools, "mcp_servers": servers}))}</pre>'
        '</div></div></div>'
    )


def render_result(msg: dict) -> str:
    cost = msg.get("total_cost_usd")
    cost_str = f"${cost:.4f}" if isinstance(cost, (int, float)) else str(cost)
    summary = (
        f"<b>turns:</b> {esc(msg.get('num_turns'))} · "
        f"<b>cost:</b> {esc(cost_str)} · "
        f"<b>duration:</b> {esc(msg.get('duration_ms'))}ms · "
        f"<b>api:</b> {esc(msg.get('duration_api_ms'))}ms · "
        f"<b>error:</b> {esc(msg.get('is_error'))}"
    )
    raw_result = msg.get("result", "")
    return (
        '<div class="turn">'
        '<div class="turn-h">Final result</div>'
        f'<div class="turn-body"><div class="block result-final">{summary}'
        + (f'<pre>{esc(raw_result)}</pre>' if raw_result else "")
        + '</div></div></div>'
    )


def render_record(record: dict, source_path: Path) -> str:
    cond = record.get("condition", {})
    outcome = record.get("outcome", {})
    err = record.get("error")
    cost = next(
        (m.get("total_cost_usd") for m in record.get("messages", []) if m.get("role") == "result"),
        None,
    )

    title = f"{record.get('puzzle_id','?')} · toolset={cond.get('toolset','?')} · meta={cond.get('meta')}"
    badge = (
        '<span class="badge ok">SOLVED</span>'
        if outcome.get("solved")
        else '<span class="badge no">UNSOLVED</span>'
    )
    cost_str = f"${cost:.4f}" if isinstance(cost, (int, float)) else "—"

    meta = (
        f"<b>tool calls:</b> {outcome.get('tool_call_count', 0)} · "
        f"<b>tool errors:</b> {outcome.get('tool_errors', 0)} · "
        f"<b>elapsed:</b> {record.get('elapsed_seconds', 0):.1f}s · "
        f"<b>cost:</b> {cost_str} · "
        f"<b>started:</b> {esc(record.get('timestamp',''))} · "
        f"<b>source:</b> {esc(source_path.name)}"
    )
    if err:
        meta += f'<div class="block warn" style="margin-top:8px"><b>Run error:</b><pre>{esc(err)}</pre></div>'

    by_name = outcome.get("tool_calls_by_name", {})
    if by_name:
        items = " ".join(
            f"<code>{esc(short_tool(k))}</code>×{v}"
            for k, v in sorted(by_name.items(), key=lambda kv: -kv[1])
        )
        meta += f'<div style="margin-top:6px"><b>by tool:</b> {items}</div>'

    messages = record.get("messages", [])
    results_map = collect_tool_results(messages)
    counter = [0]
    state = GridState()

    body_parts: list[str] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            body_parts.append(render_system(m))
        elif role == "assistant":
            body_parts.append(render_assistant(m, results_map, counter, state))
        elif role == "user":
            # Tool results are already paired with their calls; skip standalone user messages
            # unless they contain non-tool-result text (rare in this harness).
            content = m.get("content", [])
            if isinstance(content, str) and content.strip():
                body_parts.append(
                    '<div class="turn"><div class="turn-h">User</div>'
                    f'<div class="turn-body"><div class="block text">{esc(content)}</div></div></div>'
                )
        elif role == "result":
            body_parts.append(render_result(m))
        elif role == "unknown":
            body_parts.append(render_unknown(m))

    body_html = "\n".join(p for p in body_parts if p)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
  <h1>{esc(title)} {badge}</h1>
  <div class="meta">{meta}</div>
  <div style="margin: 8px 0 14px">
    <button id="expand-all">expand all</button>
    <button id="collapse-all">collapse all</button>
  </div>
  {body_html}
</div>
<script>{JS}</script>
</body></html>
"""


def render_index(items: list[tuple[Path, dict]]) -> str:
    rows: list[str] = []
    for html_path, rec in items:
        cond = rec.get("condition", {})
        out = rec.get("outcome", {})
        cost = next(
            (m.get("total_cost_usd") for m in rec.get("messages", []) if m.get("role") == "result"),
            None,
        )
        cost_str = f"${cost:.4f}" if isinstance(cost, (int, float)) else "—"
        solved = "✓" if out.get("solved") else ("✗" if rec.get("error") else "·")
        elapsed_str = f"{rec.get('elapsed_seconds', 0):.1f}s"
        rows.append(
            f"<tr>"
            f"<td>{esc(rec.get('timestamp',''))}</td>"
            f"<td>{esc(rec.get('puzzle_id',''))}</td>"
            f"<td>{esc(cond.get('toolset',''))}</td>"
            f"<td>{esc(cond.get('meta',''))}</td>"
            f"<td>{solved}</td>"
            f"<td>{esc(out.get('tool_call_count', 0))}</td>"
            f"<td>{esc(elapsed_str)}</td>"
            f"<td>{esc(cost_str)}</td>"
            f"<td><a href='{esc(html_path.name)}'>view</a></td>"
            f"</tr>"
        )
    body = "".join(rows)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>harness results</title>
<style>{CSS}</style></head>
<body><div class="wrap">
  <h1>Harness results</h1>
  <div class="meta">{len(items)} runs</div>
  <table class="idx">
    <thead><tr><th>started</th><th>puzzle</th><th>toolset</th><th>meta</th>
      <th>solved</th><th>calls</th><th>elapsed</th><th>cost</th><th></th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</div></body></html>
"""


def render_file(path: Path) -> Path:
    rec = json.loads(path.read_text())
    out = path.with_suffix(".html")
    out.write_text(render_record(rec, path))
    return out


def render_dir(path: Path) -> None:
    items: list[tuple[Path, dict]] = []
    for jp in sorted(path.glob("*.json")):
        rec = json.loads(jp.read_text())
        out = jp.with_suffix(".html")
        out.write_text(render_record(rec, jp))
        items.append((out, rec))
    # Sort index newest first by timestamp
    items.sort(key=lambda it: it[1].get("timestamp", ""), reverse=True)
    (path / "index.html").write_text(render_index(items))
    print(f"wrote {len(items)} HTML files + index.html in {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    args = ap.parse_args()
    if args.path.is_dir():
        render_dir(args.path)
    else:
        out = render_file(args.path)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()

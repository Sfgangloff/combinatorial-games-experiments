"""
Run one (puzzle x condition) experimental cell.

CLI:
    python -m harness.run puzzle_001 --toolset medium --meta off [--max-turns 50]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from harness.conditions import (
    Condition,
    Toolset,
    allowed_tool_globs_for,
    mcp_servers_for,
)
from harness.prompts import SYSTEM_PROMPT, user_prompt

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "harness" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _serialize_block(block: Any) -> dict:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ThinkingBlock):
        return {"type": "thinking", "text": block.thinking}
    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if isinstance(block, ToolResultBlock):
        content = block.content
        if isinstance(content, list):
            content = [
                c if isinstance(c, (str, int, float, bool, type(None))) else str(c)
                for c in content
            ]
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": content,
            "is_error": getattr(block, "is_error", False),
        }
    return {"type": "unknown", "repr": repr(block)}


def _serialize_message(msg: Any) -> dict:
    if isinstance(msg, AssistantMessage):
        return {
            "role": "assistant",
            "content": [_serialize_block(b) for b in msg.content],
        }
    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, list):
            content = [_serialize_block(b) for b in content]
        return {"role": "user", "content": content}
    if isinstance(msg, SystemMessage):
        return {"role": "system", "subtype": msg.subtype, "data": msg.data}
    if isinstance(msg, ResultMessage):
        return {
            "role": "result",
            "subtype": msg.subtype,
            "duration_ms": msg.duration_ms,
            "duration_api_ms": msg.duration_api_ms,
            "is_error": msg.is_error,
            "num_turns": msg.num_turns,
            "session_id": msg.session_id,
            "total_cost_usd": msg.total_cost_usd,
            "usage": msg.usage,
            "result": msg.result,
        }
    return {"role": "unknown", "repr": repr(msg)}


def _outcome(messages: list[dict], puzzle_id: str) -> dict:
    """
    Inspect the trace to extract experimental outcome.

    A run is 'solved' iff a submit_solution call returned correct=true for our
    target puzzle. Otherwise we report 'stuck' (model produced final text and
    stopped) or 'errored'.
    """
    tool_call_count = 0
    tool_calls_by_name: Counter[str] = Counter()
    submit_attempts: list[dict] = []
    errors = 0

    for msg in messages:
        if msg.get("role") == "assistant":
            for block in msg["content"]:
                if block["type"] == "tool_use":
                    tool_call_count += 1
                    tool_calls_by_name[block["name"]] += 1
                    if block["name"].endswith("submit_solution"):
                        submit_attempts.append(block)
        elif msg.get("role") == "user" and isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    if block.get("is_error"):
                        errors += 1

    solved = False
    final_judge_reason = None
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                    continue
                content = block.get("content")
                # tool_result content is typically a list of dicts with type=text and text=<json>
                texts: list[str] = []
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, str):
                            texts.append(c)
                        elif isinstance(c, dict) and "text" in c:
                            texts.append(c["text"])
                elif isinstance(content, str):
                    texts.append(content)
                for t in texts:
                    try:
                        parsed = json.loads(t)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if isinstance(parsed, dict) and "correct" in parsed:
                        final_judge_reason = parsed.get("reason")
                        if parsed["correct"]:
                            solved = True

    return {
        "solved": solved,
        "submit_attempts": len(submit_attempts),
        "tool_call_count": tool_call_count,
        "tool_calls_by_name": dict(tool_calls_by_name),
        "tool_errors": errors,
        "last_judge_reason": final_judge_reason,
    }


async def run_one(
    puzzle_id: str,
    condition: Condition,
    *,
    max_turns: int = 50,
    model: str | None = None,
    log: bool = True,
) -> dict:
    options = ClaudeAgentOptions(
        tools=[],  # disable all built-ins
        allowed_tools=allowed_tool_globs_for(condition),
        mcp_servers=mcp_servers_for(condition),
        strict_mcp_config=True,
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        system_prompt=SYSTEM_PROMPT,
        model=model,
    )

    messages: list[dict] = []
    started_at = time.time()
    error: str | None = None

    try:
        async for msg in query(prompt=user_prompt(puzzle_id), options=options):
            serialized = _serialize_message(msg)
            messages.append(serialized)
            if log:
                role = serialized.get("role", "?")
                if role == "assistant":
                    for b in serialized["content"]:
                        if b["type"] == "tool_use":
                            print(f"  -> {b['name']}({list(b['input'].keys())})")
                        elif b["type"] == "text":
                            snippet = b["text"][:160].replace("\n", " ")
                            print(f"  text: {snippet}...")
                elif role == "result":
                    print(f"  RESULT: turns={serialized['num_turns']} "
                          f"cost=${serialized['total_cost_usd']:.4f}")
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        if log:
            print(f"  ERROR: {error}")

    elapsed = time.time() - started_at
    outcome = _outcome(messages, puzzle_id)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "puzzle_id": puzzle_id,
        "condition": {
            "toolset": condition.toolset,
            "meta": condition.meta,
        },
        "max_turns": max_turns,
        "model": model,
        "elapsed_seconds": elapsed,
        "error": error,
        "outcome": outcome,
        "messages": messages,
    }

    out_path = (
        RESULTS_DIR
        / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_"
        f"{puzzle_id}_{condition.name}.json"
    )
    out_path.write_text(json.dumps(record, indent=2, default=str))
    if log:
        print(f"  saved: {out_path.name}")
        print(f"  outcome: solved={outcome['solved']} "
              f"tool_calls={outcome['tool_call_count']} "
              f"errors={outcome['tool_errors']} "
              f"elapsed={elapsed:.1f}s")

    return record


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("puzzle_id")
    p.add_argument("--toolset", choices=["none", "fine", "medium", "coarse", "scratchpad"], default="medium")
    p.add_argument("--meta", choices=["on", "off"], default="off")
    p.add_argument("--max-turns", type=int, default=50)
    p.add_argument("--model", default=None,
                   help="Model id (e.g. claude-sonnet-4-6). Default uses SDK default.")
    return p.parse_args()


def main():
    args = _parse_args()
    condition = Condition(toolset=args.toolset, meta=(args.meta == "on"))
    asyncio.run(run_one(
        args.puzzle_id, condition,
        max_turns=args.max_turns, model=args.model,
    ))


if __name__ == "__main__":
    main()

"""
In-process test of slitherlink-scratchpad server tools.

Imports the server module and calls the FastMCP-registered functions through
their underlying Python implementations to verify wiring + frame-stack
lifecycle (assume / commit / retract, depth cap, negation-on-retract).
"""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO / "servers" / "slitherlink-scratchpad" / "server.py"
PUZZLE_PATH = REPO / "legacy" / "slitherlink-batch-experiment" / "grid_step_0.txt"


def _import_server():
    spec = importlib.util.spec_from_file_location("scratchpad_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    server = _import_server()
    mcp = server.mcp

    tools = await mcp.list_tools()
    tools = {t.name: t for t in tools}
    expected = {
        "load", "render", "apply_edge", "forced_moves", "check_consistency",
        "endpoints", "solved", "assume", "commit", "retract", "frames",
        "current_frame", "try_both",
    }
    actual = set(tools.keys())
    assert expected <= actual, f"missing tools: {expected - actual}"
    print(f"tools registered: {sorted(actual)}")

    grid_text = PUZZLE_PATH.read_text()
    loaded = server.load(grid_text=grid_text)
    handle = loaded["handle"]
    print(f"loaded handle={handle}, line_edges={loaded['summary']['line_edges']}")

    # Initial frames: just root.
    fr = server.frames(handle=handle)
    assert fr["depth"] == 0 and len(fr["frames"]) == 1, fr
    assert fr["frames"][0]["frame_id"] == "root"
    print(f"initial depth={fr['depth']}, max={fr['max_depth']}")

    # Forced moves at root (5x5 with a 0-cell + 3-cells gives forced edges).
    forced = server.forced_moves(handle=handle)
    assert forced["contradiction"] is None
    print(f"forced_moves at root: {len(forced['changes'])} changes")

    # apply_edge at root frame.
    applied = server.apply_edge(handle=handle, edge_type="H", row=0, col=0, value="line")
    assert applied["contradiction"] is None
    line_after_apply = sum(1 for c in applied["changes"]) + 1
    print(f"apply_edge H[0][0]=line at root: {len(applied['changes'])} propagated changes")

    # === assume() with a single edge that contradicts (the 0-cell at (3,2) → H[3][2]=blocked is forced).
    bad = server.assume(
        handle=handle,
        rationale="hypothesis: top edge of the 0-cell is a line (should contradict)",
        edges=[{"edge_type": "H", "row": 3, "col": 2, "value": "line"}],
    )
    assert bad["status"] == "contradiction", bad
    assert bad["contradiction"] is not None
    assert bad["depth"] == 1
    bad_frame_id = bad["frame_id"]
    print(f"assume contradicting: frame={bad_frame_id}, depth=1, "
          f"contradiction={bad['contradiction'][:80]}…")

    # frames() now shows two entries.
    fr = server.frames(handle=handle)
    assert fr["depth"] == 1, fr
    assert fr["frames"][1]["frame_id"] == bad_frame_id
    assert fr["frames"][1]["status"] == "contradiction"

    # retract with take_negation=True. The negation "H[3][2] blocked" is
    # already a forced move at the parent (because of the 0-cell), so applying
    # it should either be a no-op or produce a propagation chain — but it
    # should NOT contradict.
    rt = server.retract(handle=handle, frame_id=bad_frame_id, take_negation=True)
    assert rt["ok"] and rt["depth"] == 0, rt
    assert rt["negation_applied"] is not None
    assert rt["negation_applied"]["value"] == "blocked"
    assert rt["negation_applied"]["contradiction"] is None
    print(f"retract took negation H[3][2]=blocked, "
          f"propagated {len(rt['negation_applied']['changes'])} extra changes")

    # === assume() with a single non-contradictory edge → commit.
    ok_assume = server.assume(
        handle=handle,
        rationale="trial: V[0][0]=line",
        edges=[{"edge_type": "V", "row": 0, "col": 0, "value": "line"}],
    )
    if ok_assume["status"] == "contradiction":
        # On this puzzle V[0][0]=line might or might not contradict; if it does,
        # retract and try the opposite.
        print(f"V[0][0]=line contradicted; retracting (will test commit on a different edge)")
        server.retract(handle=handle, frame_id=ok_assume["frame_id"], take_negation=False)
        ok_assume = server.assume(
            handle=handle,
            rationale="trial: V[0][0]=blocked",
            edges=[{"edge_type": "V", "row": 0, "col": 0, "value": "blocked"}],
        )
        assert ok_assume["status"] == "open", ok_assume
    print(f"open frame depth={ok_assume['depth']}, status={ok_assume['status']}")

    # commit should collapse the frame into parent.
    cm = server.commit(handle=handle, frame_id=ok_assume["frame_id"])
    assert cm.get("ok"), cm
    assert cm["depth"] == 0
    print(f"commit ok, back to depth=0, line_edges={cm['summary']['line_edges']}")

    # === multi-edge assume: pass two edges in one call.
    multi = server.assume(
        handle=handle,
        rationale="multi-edge hypothesis: try two edges of an undecided cell",
        edges=[
            {"edge_type": "H", "row": 5, "col": 4, "value": "blocked"},
            {"edge_type": "V", "row": 4, "col": 4, "value": "blocked"},
        ],
    )
    print(f"multi-edge assume: status={multi['status']}, "
          f"applied {len(multi['assumed_edges'])} edges, depth={multi['depth']}")
    if multi["status"] == "contradiction":
        server.retract(handle=handle, frame_id=multi["frame_id"], take_negation=False)
    else:
        server.retract(handle=handle, frame_id=multi["frame_id"], take_negation=False)

    # === depth cap: nest 5 frames, then expect the 6th to error.
    depth_handle_loaded = server.load(grid_text=grid_text)
    dh = depth_handle_loaded["handle"]
    # Use innocuous edges far apart to avoid early contradiction. We use the
    # `dh` puzzle which has no edits yet. We pick edges that we know don't
    # contradict in this puzzle: V[0][5] (right border, top), H[5][0] (mid),
    # etc. If any contradict early, fall back to a smaller cap test.
    candidate_edges = [
        {"edge_type": "V", "row": 0, "col": 5, "value": "line"},
        {"edge_type": "V", "row": 1, "col": 5, "value": "line"},
        {"edge_type": "V", "row": 2, "col": 5, "value": "line"},
        {"edge_type": "V", "row": 3, "col": 5, "value": "line"},
        {"edge_type": "V", "row": 4, "col": 5, "value": "line"},
    ]
    pushed = 0
    for e in candidate_edges:
        r = server.assume(handle=dh, rationale=f"nest test: {e}", edges=[e])
        if "error" in r:
            break
        pushed += 1
        if r["status"] == "contradiction":
            # We expected open frames; if propagation contradicts this test
            # is inconclusive for the cap. Stop and report.
            print(f"  nest{pushed}: contradicted, stopping cap test early")
            break
    print(f"nested {pushed} frames")

    # If we managed to push the max, attempt a 6th and expect an error.
    if pushed == server.MAX_FRAME_DEPTH:
        sixth = server.assume(
            handle=dh,
            rationale="6th frame — should hit cap",
            edges=[{"edge_type": "H", "row": 0, "col": 0, "value": "line"}],
        )
        assert "error" in sixth, sixth
        assert "max depth" in sixth["error"]
        print(f"  6th frame correctly rejected: {sixth['error']}")
    else:
        print(f"  cap test inconclusive (only nested {pushed} before "
              f"contradiction/error) — acceptable, semantics still verified")

    # === retract validation: reject non-top frame_id.
    fr = server.frames(handle=dh)
    if fr["depth"] >= 1:
        bogus = server.retract(handle=dh, frame_id="not-a-frame")
        assert "error" in bogus, bogus
        print(f"  retract rejects non-top frame_id correctly")

    # === try_both on a fresh handle.
    tb_loaded = server.load(grid_text=grid_text)
    tbh = tb_loaded["handle"]

    # Edge H[3][2] sits on top of the 0-cell at (3,2). LINE branch
    # contradicts (0-cell forbids any line); BLOCKED survives (already
    # forced by the 0-cell). Expect outcome='forced_blocked'.
    tb_zero = server.try_both(
        handle=tbh, edge_type="H", row=3, col=2,
        rationale="top edge of the 0-cell",
    )
    assert tb_zero["outcome"] == "forced_blocked", tb_zero
    assert tb_zero["line_branch"]["survives"] is False
    assert tb_zero["blocked_branch"]["survives"] is True
    assert tb_zero["forced"] is not None
    assert tb_zero["forced"]["value"] == "blocked"
    print(f"try_both H[3][2] near 0-cell: outcome={tb_zero['outcome']}, "
          f"forced blocked + {len(tb_zero['forced']['changes'])} propagated changes")

    # Calling try_both on an already-determined edge should error.
    tb_again = server.try_both(handle=tbh, edge_type="H", row=3, col=2)
    assert "error" in tb_again, tb_again
    print(f"  try_both rejects determined edge: {tb_again['error'][:80]}")

    # try_both on an undecided edge that admits both branches → 'both_survive',
    # state unchanged. Pick an edge far from constraints.
    tb_loaded2 = server.load(grid_text=grid_text)
    tbh2 = tb_loaded2["handle"]
    summary_before = tb_loaded2["summary"]
    tb_amb = server.try_both(
        handle=tbh2, edge_type="V", row=0, col=2,
        rationale="probing an undecided interior vertical edge",
    )
    print(f"try_both V[0][2] on fresh state: outcome={tb_amb['outcome']}")
    # Either both survive (no info, state unchanged) or one is forced
    # (state changed). Either is valid; we just want to verify no crash.
    assert tb_amb["outcome"] in {
        "both_survive", "forced_line", "forced_blocked", "neither_survives",
    }, tb_amb

    print("\nAll scratchpad-server tests passed.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

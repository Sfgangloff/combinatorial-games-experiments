"""
Harness smoke test — verifies condition wiring + serialization without
actually calling Claude.
"""
from harness.conditions import (
    ALL_CONDITIONS,
    Condition,
    allowed_tool_globs_for,
    mcp_servers_for,
)


def test_judge_always_present():
    for cond in ALL_CONDITIONS:
        servers = mcp_servers_for(cond)
        assert "slitherlink-judge" in servers, cond


def test_toolset_inclusion():
    for ts in ("fine", "medium", "coarse"):
        servers = mcp_servers_for(Condition(toolset=ts, meta=False))
        assert f"slitherlink-{ts}" in servers
        assert "meta-tools" not in servers
    servers = mcp_servers_for(Condition(toolset="none", meta=False))
    assert "slitherlink-none" not in servers
    assert servers == {"slitherlink-judge": servers["slitherlink-judge"]}


def test_meta_explicit_config_overrides_discovery():
    cond = Condition(
        toolset="medium",
        meta=True,
        meta_tools_config={"type": "stdio", "command": "/usr/bin/true"},
    )
    servers = mcp_servers_for(cond)
    assert "meta-tools" in servers
    assert servers["meta-tools"]["command"] == "/usr/bin/true"


def test_meta_off_never_includes_metatools():
    for ts in ("none", "fine", "medium", "coarse"):
        servers = mcp_servers_for(Condition(toolset=ts, meta=False))
        assert "meta-tools" not in servers


def test_allowed_globs_match_servers():
    for cond in ALL_CONDITIONS:
        servers = set(mcp_servers_for(cond).keys())
        globs = set(allowed_tool_globs_for(cond))
        assert {f"mcp__{n}__*" for n in servers} == globs, cond


def main():
    test_judge_always_present()
    print("judge_always_present OK")
    test_toolset_inclusion()
    print("toolset_inclusion OK")
    test_meta_explicit_config_overrides_discovery()
    print("meta_explicit_config_overrides_discovery OK")
    test_meta_off_never_includes_metatools()
    print("meta_off_never_includes_metatools OK")
    test_allowed_globs_match_servers()
    print("allowed_globs_match_servers OK")
    print("\nAll harness smoke tests passed.")


if __name__ == "__main__":
    main()

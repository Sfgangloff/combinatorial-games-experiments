# Related work — tool granularity for LLM agents (Phase 0)

**Date:** 2026-05-07
**Status:** Phase-0 deliverable. Decision: **proceed to Phase 1 with reframing**
(see §4).

## 1. Search method

Searched arXiv (cs.CL / cs.AI / cs.SE / cs.LG) on the following phrasings:
"tool granularity", "tool abstraction level", "API granularity",
"primitive vs composite tools", "tool selection action space", "tool
consolidation / merging", "tool design taxonomy", "tool ablation",
"action space shaping", "code interpreter vs primitive tools", "fewer/more
tools agent", and the canonical landmark names (ReAct, Toolformer, ToolLLM,
AgentBench, τ-bench, Voyager, Reflexion).

Specifically pulled last-3-months arXiv (2026-02 onward) to assess scoop
risk per the project's stated risk #1.

## 2. Reference list (~25 papers)

### Canonical agent / tool-use foundations
1. Yao et al., **ReAct: Synergizing Reasoning and Acting** (2210.03629)
2. Schick et al., **Toolformer** (2302.04761)
3. Qin et al., **ToolLLM** (2307.16789) — 16k+ APIs, scale axis
4. Liu et al., **AgentBench** (2308.03688) — 8 environments, evaluation
5. Wang et al., **Voyager** (2305.16291) — skill library construction
6. Shinn et al., **Reflexion** (2303.11366) — verbal RL
7. Yao et al., **τ-bench** (2406.12045) — tool-agent-user interaction
8. Barres et al., **τ²-bench** (2506.07982) — dual-control extension
9. Sumers et al., **Cognitive Architectures for Language Agents** (2309.02427)

### Tool design / efficiency / cost
10. Wu et al., **CATP-LLM: Cost-Aware Tool Planning** (2411.16313)
11. Wang et al., **Efficient Agents** (2508.02694) — first cost-effectiveness study
12. Ross et al., **When2Call** (2504.18851) — when *not* to call tools
13. Erol et al., **Cost-of-Pass: Economic Framework for LMs** (2504.13359)
14. Chen et al., **TUMIX: Tool-Use Mixture** (2510.01279) — mixing strategies

### Scale / retrieval over many tools
15. Du et al., **AnyTool** (2402.04253) — 16k APIs hierarchical
16. Lumer et al., **Toolshed** (2410.14594) — RAG-tool fusion
17. Lumer et al., **Tool-to-Agent Retrieval** (2511.01854)
18. Liu et al., **ToolScope: Tool Merging + Filtering** (2510.20036)
19. Esfandiarpoor et al., **TheMCPCompany** (2510.19286) — task-specific vs general
20. Guo et al., **MCP-AgentBench** (2509.09734)
21. Lei et al., **MCPVerse** (2508.16260)
22. Basu et al., **NESTFUL** (2409.03797) — nested API call benchmark

### Closest to our angle (granularity as variable)
23. **Lou et al., "The Tool Illusion: Rethinking Tool Use in Web Agents"
    (2604.03465, COLM 2026)** — see §3. Major overlap.
24. **Ray, "Agent Capsules: Quality-Gated Granularity Control" (2605.00410)**
    — granularity term used, but for multi-agent merging, not single-agent
    tool design. Orthogonal axis.

### CSP / puzzle / reasoning-effort context
25. Estermann & Wattenhofer, **Reasoning Effort and Problem Complexity**
    (2503.15113)
26. Maniparambil et al., **TopoBench** (2603.12133) — loop/connectivity puzzles
27. Miya, **Eidoku: Neuro-Symbolic Verification for Sudoku** (2512.20664)
28. Berthier, **Pattern-Based Constraint Satisfaction and Logic Puzzles**
    (1304.1628)

### Theoretical ancestors (for Phase 5)
29. Sutton, Precup, Singh (1999), **Between MDPs and semi-MDPs: options
    framework** (classical reference; not on arXiv)
30. Kanervisto et al., **Action Space Shaping in Deep RL** (2004.00980)

## 3. The scoop-risk paper: "The Tool Illusion" (COLM 2026)

Lou, Peng, Yao et al. (Microsoft / Penn State), April 2026, COLM 2026:
the most threatening prior work. Their findings include:

- **"Tools Should Not Be Overly Complex: Decoupling Agentic Reasoning
  from Tools"** — overly complex tools hurt agent performance.
- **"The Essence of Tool Design: Functional Coverage and Composition"**
- **"The Tax of Tools: Token Cost and Action Overhead"** — quantifies
  cost trade-offs.
- Appendix C: explicit **"Tool Complexity Levels"** classifier; tools
  scored by complexity, results stratified.
- Strong-to-weak transfer: tools synthesized by strong models help
  weaker models. (Resembles our Phase-3 hypothesis: smaller models
  benefit more from coarse tools.)
- Domain: **web/browser agents only** (WALT, SkillWeaver, hybrid REST).

What they have that we don't yet: extensive empirical scale, tested
across multiple frameworks and benchmarks, COLM 2026 acceptance.

What we have that they don't:
- **Domain:** CSP / logic puzzles with formal structure, no
  natural-language subjectivity; difficulty is precisely tunable.
- **Granularity controlled by the experimenter, not by skill synthesis.**
  Our four tiers (none / fine / medium / coarse) span a known spectrum
  from pure-LLM reasoning to a near-complete external solver — Tool
  Illusion's "complexity levels" are a post-hoc description of
  agent-synthesized skills.
- **Engine-side reasoning** is the variable: each tier reflects how
  much CSP propagation/search lives in the tool. This is a
  model-vs-engine division-of-labor question, not a wrapper-design one.
- **Phase-5 theoretical anchor** (information-theoretic / decision-
  theoretic granularity) — Tool Illusion is descriptive only.

## 4. Position statement (1 page)

### What's our angle?

We study **tool granularity as a controllable design axis at fixed task**,
on logic-puzzle CSPs (slitherlink → nonograms → ...), with the goal of
producing a *predictive* (not just descriptive) account of when a given
granularity is optimal for a given (model, task) pair.

Concretely, the contribution we are aiming for:

1. **A clean experimental design** that varies model-engine work
   partitioning at fixed task, on a domain where success is binary and
   verifiable (no LLM-judge artifacts).
2. **A granularity-by-model-capability interaction effect** — that
   weaker models benefit disproportionately from coarse tools and vice
   versa. (Phase 3.) This goes beyond Tool Illusion's strong-to-weak
   skill-transfer finding because we hold the *toolset* fixed and vary
   only the model, on the same instances.
3. **A predictive formal definition of granularity** (Phase 5) that
   forecasts the winning toolset out-of-sample. None of the prior work,
   including Tool Illusion, attempts this.

### What's already taken?

- **"Granularity is a real axis that affects cost and success"** — taken
  by Tool Illusion (web-agent domain) and partly by Agent Capsules
  (multi-agent merging). We can no longer claim discovery of this fact.
- **"Cost-aware tool planning"** — taken by CATP-LLM, Efficient Agents.
- **"Tools can hurt as well as help"** — taken by When2Call, Tool Illusion.
- **Tool retrieval at scale** — taken by AnyTool, Toolshed, ToolScope,
  TheMCPCompany.

### What is *not* yet taken?

- **A logic-puzzle / CSP testbed for tool granularity** with formal
  difficulty axis. Closest is TopoBench, but it studies LLMs without
  varying tools.
- **Granularity-by-model-capability interaction as a reportable
  effect, controlled at the toolset level.**
- **A predictive model of optimal granularity.**
- **Procedurally generated, contamination-free CSP instances** as a
  benchmark for the above.

### Risks made specific by this review

- **Scoop risk: HIGH for descriptive findings.** Tool Illusion has the
  field-level "tool granularity matters" claim. We must reframe ours
  as (a) puzzle-CSP-specific and (b) interaction + theory, not pure
  description.
- **Scoop risk: MEDIUM for cost-frontier.** Several recent papers
  (Efficient Agents, CATP-LLM, Cost-of-Pass) cover the cost framing.
  Our angle must be: cost is just one observable; the underlying
  variable is granularity.
- **Scoop risk: LOW for predictive theory.** No paper we found
  attempts an out-of-sample predictive model of granularity. Phase 5
  is therefore the most defensible novelty.
- **Domain risk.** A puzzle-only result will look narrow to
  agent-tool reviewers. Phase 4 (second task family) is now more
  load-bearing than originally framed.

## 5. Decision (Phase 0 gate)

**Proceed to Phase 1, with these reframings carried into all later phases:**

1. The headline is no longer "granularity is a controllable axis" —
   that's been demonstrated. The headline becomes
   **"granularity has a model-dependent optimum that admits a
   predictive theory, demonstrated on formal CSP tasks."**
2. **Phase 5 (theory) is promoted from "nice to have" to "core
   contribution."** Without it, we are a slower-moving Tool Illusion
   on a different domain.
3. Phase 1 (replication) is unchanged: cheap, fast, kills the
   project if pilot ratios are noise. The scoop risk doesn't change
   the value of replication.
4. **Cite Tool Illusion in every subsequent writeup as the closest
   prior work.** Anchor our differentiation to its limitations
   (single domain, descriptive, agent-synthesized skills).

If Phase 1 replicates the cost ratios, Phase 2 → Phase 5 with theory
as the centerpiece. If Phase 1 collapses to noise, stop — both because
the empirical kernel is fragile and because the descriptive lane is
already crowded.

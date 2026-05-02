# ChatGPT's Plan for Improving Rule Compliance

This document stores the improvement plan that was implemented.

## Key Changes Made

### 1. Convert prose into atomic MUST rules
- Rewrote CLAUDE.md to use explicit MUST/MUST NOT language
- Each rule is testable and unambiguous
- Strategy/heuristics moved to separate SHOULD file

### 2. Require pasting validator output
- Added `=== VALIDATOR OUTPUT ===` section requirement
- Forces actually running the validator (not "assuming" it passes)
- Model must condition on real feedback

### 3. Removed "active endpoints" ambiguity
- Changed from vague "active endpoints" to precise rule:
- "At all times there is at most ONE open path component"
- "Therefore there are either 0 endpoints (closed loop) or exactly 2 endpoints total"

### 4. Reduced duplication
- Hard rules stated ONCE in CLAUDE.md
- Strategy in separate slitherlink_strategy.md
- Failure logging in separate failure_playbook.md

## File Structure After Implementation

```
CLAUDE.md                  - HARD RULES only (compact, testable)
slitherlink_strategy.md    - SHOULD rules (heuristics, patterns)
failure_playbook.md        - Failure logging template
specific_solving_guide.md  - Past lessons learned
validate_grid.py           - Grid validation script
verify_batch.py            - Batch verification script (hard gate)
```

## Tools Implemented

### verify_batch.py (Hard Gate Script)
Checks ALL MUST rules after each batch:
- Exactly 2 files created with correct names
- Exactly 5 steps (or fewer if BACKTRACK)
- Each step contains a full grid
- Each grid differs from previous by exactly ONE edge change
- Validator output section present
- Final grid matches grid_step_N.txt
- Single path component (0 or 2 endpoints)
- No branching (no dot with 3+ edges)
- Runs validate_grid.py and checks it passes

Usage: `python3 verify_batch.py N`

## Original ChatGPT Recommendations

### 3) Convert prose into atomic MUST rules
Example: "perform 5 steps… create two files…" but there are many nearby instructions that sound equally important.
Rewrite as:
- MUST create exactly two files per batch, named …
- MUST do exactly 5 elementary steps unless BACKTRACK occurs
- MUST include the full grid after each step in reasoning file
- MUST run validator and paste its output at end of reasoning file
- MUST NOT edit earlier batch files

### 4) Require the agent to paste validator output
Agents often "run the command" in their head. If you require the raw output pasted:
- you know it actually ran
- the model is forced to condition on real feedback

### 5) Remove "active endpoints" ambiguity
The line "no dot is left with exactly 1 edge (except for the two active endpoints)" is a loophole.
If intent is single growing path, say mechanically:
"At all times there is at most one open path component. Therefore there are either 0 endpoints (closed loop) or exactly 2 endpoints total."

### 6) Reduce duplication
Models tend to "blend" duplicates and miss strictness. Keep each hard rule stated once.

## Benefits of New Structure

1. Short and testable contract
2. Single priority: produce batch artifacts that pass validation
3. Clear separation of MUST vs SHOULD
4. Forced real validation (not assumed)
5. Precise endpoint rules (no ambiguity)

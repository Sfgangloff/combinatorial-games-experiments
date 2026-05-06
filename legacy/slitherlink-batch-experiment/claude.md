# Slitherlink Batch Contract (HARD RULES)

For each batch N:

## Outputs (MUST)
- MUST create exactly 1 file: `reasoning_step_N.txt`
- MUST NOT modify any previous batch files.

## Batch size (MUST)
- MUST perform exactly 5 elementary steps per batch (adjustable parameter).
- EXCEPTION: If batch contains a BACKTRACK step, MUST stop immediately after BACKTRACK.

## Allowed elementary steps (MUST)
Each step is exactly one of:
- Add edge `H[row][col]` (horizontal) or `V[row][col]` (vertical)
- BACKTRACK to batch M

Note: Blocking deductions are mentioned in reasoning but don't count as steps.
Only adding edges to the loop counts as an elementary step.

## Path components (MUST)
- At all times there is at most ONE open path component.
- Therefore there are either 0 endpoints (closed loop) or exactly 2 endpoints total.
- MUST NOT create disconnected edge segments.

## Reasoning file format (MUST)
`reasoning_step_N.txt` MUST contain:
```
=== BATCH N (Steps X to Y) ===

--- Step X ---
Action: [Add edge H[row][col] / Add edge V[row][col] / Block edge H[row][col] / Block edge V[row][col] / BACKTRACK to batch M]
Reasoning: [Why this action is correct]
Grid after step X:
[full grid state]

--- Step X+1 ---
... (repeat for each step)

=== VALIDATOR OUTPUT ===
[paste full console output here]

=== END BATCH N ===
```

If BACKTRACK occurs:
```
--- Step X ---
Action: BACKTRACK to batch M
Reasoning: [Which constraint failed and why]

=== END BATCH N (incomplete due to backtrack) ===
```

## Validator (MUST)
After completing all steps, MUST run validator on the final grid:
```bash
python3 validate_grid.py <final_grid> --check-satisfiability
```

- MUST paste the full console output into reasoning file under `=== VALIDATOR OUTPUT ===`
- MUST NOT "assume" validation passes - always run and paste actual output.

If validator FAILS:
- MUST NOT continue this line.
- Next batch MUST be a BACKTRACK batch.
- MUST document failure in `failure_playbook.md`.

## Batch Verifier (MUST pass)
After completing a batch, MUST run:
```bash
python3 verify_batch.py N
```

This verifies ALL MUST rules. If it FAILS, MUST fix before proceeding.

## Grid Representation (MUST)
- `.` = dot (intersection point)
- `-` = horizontal edge (part of loop)
- `|` = vertical edge (part of loop)
- Numbers (0-3) = cell constraints
- Space = no edge

Note: Blocked edges are tracked in reasoning text, not shown in grid.
The grid only shows edges that ARE part of the loop.

## Slitherlink Rules (MUST enforce)
- One single continuous closed loop
- Loop follows grid edges between dots
- Numbers indicate how many sides of that cell are part of the loop
- At every dot: either 0 or exactly 2 edges touch it (never 1, never 3+)

---

Strategy and heuristics: see `slitherlink_strategy.md`
Failure logging: see `failure_playbook.md`
Past lessons: see `specific_solving_guide.md`

# Slitherlink Solving Guide: Lessons from Failed Attempts

## Overview

This document analyzes failed solving attempts on a 5x5 Slitherlink puzzle and extracts lessons for future solving.

## Key Failures Analyzed

### Failure 1: The Bottom Row Blocking Problem (Steps 240-249)

**What happened:** The path went from (3,3) down through (4,3), (5,3), then traversed the entire bottom row: (5,3) → (5,2) → (5,1) → (5,0) → up to (4,0).

**Why it failed:** Cell (4,1)=3 needs 3 edges from {H[4][1], H[5][1], V[4][1], V[4][2]}. By traversing the bottom row:
- Dot (5,1) became full with H[5][0] + H[5][1] = 2 edges
- Dot (5,2) became full with H[5][1] + H[5][2] = 2 edges
- This blocked both V[4][1] and V[4][2] (would cause branching)
- Cell (4,1) could only get H[4][1] + H[5][1] = 2 edges, not enough!

**Lesson:** Before committing to a long path segment, check if it blocks required edges for nearby numbered cells.

### Failure 2: The (2,2)/(2,3)/(3,3) Constraint Triangle

**What happened:** Attempting to satisfy cells (2,2), (2,3), and (3,3) created an impossible conflict.

**The conflict:**
- Cell (2,3)=2 has V[2][4] from the path. Its only available 2nd edge is H[3][3] (other options blocked by full dots).
- Cell (3,3)=3 needs 3 edges. With H[3][3] required for (2,3), cell (3,3) needs H[3][3] + V[3][3] + H[4][3].
- Cell (2,2)=2 has H[2][2]. Its only available 2nd edge is H[3][2] (connects to dot (3,3)).
- But dot (3,3) becomes full with H[3][3] + V[3][3], so H[3][2] can't be added!

**Lesson:** Identify "constraint triangles" where multiple cells depend on the same bottleneck dot. Plan the path through these areas first.

### Failure 3: Dead End at (2,5)

**What happened:** Trying path (3,4) → V[3][4] → (4,4) → ... → (4,5) → V[3][5] → (3,5) → V[2][5] → (2,5) led to a dead end.

**Why it failed:** From (2,5):
- H[2][4] left leads to (2,4) which has 2 edges already (branching)
- V[1][5] up leads to (1,5) which has 2 edges already (branching)
- No valid continuation!

**Lesson:** Before committing to a path direction, trace ahead to verify it doesn't lead to a dead end.

### Failure 4: Ignoring Forced Edges at Step 203 (Steps 203-252)

**Step where detected:** 203+ (via enhanced validator with propagation)
**Unsatisfiable cells:** (1,2)=3, then later (3,0)=3 and (3,3)=3
**Last valid step:** 202
**Backtrack step:** 253

**What happened:** At step 202, the validator showed FORCED edges for cell (1,2)=3:
- FORCED ['top H', 'right V'] = H[1][2] and V[1][3]

Step 203 ignored these and added H[2][3] instead. This blocked cell (1,2)=3 from ever
getting its required edges, as the available edges became blocked by subsequent moves.

**Root cause:** Forced edges were ignored. The propagation-based validator now correctly
identifies that ignoring forced edges leads to unsatisfiable states downstream.

**Lesson:** The improved validator propagates forced edges and checks if adding them
creates cascade failures. ALWAYS add forced edges before exploring other options.
If the validator shows forced edges, add them in the NEXT step.

---

### Failure 5: Trapped Loose End - Connectivity Issue (Steps 253-261)

**Step where detected:** 261
**Problem:** Loose end at dot (4,2) is TRAPPED - all adjacent dots are full

**What happened:** After backtracking to step 202 and adding all forced edges correctly (steps 253-261), the grid passed satisfiability checks but had a fatal connectivity flaw:
- Dot (4,2) has only V[4][2] going down to (5,2)
- Adjacent dots are all full: (4,1) has 2 edges, (4,3) has 2 edges, (3,2) has 2 edges
- No way to add a second edge to (4,2)
- The loop cannot be closed

**Root cause:** The bottom-left corner structure inherited from step 202:
- V[4][1] from (4,1) to (5,1)
- V[4][2] from (4,2) to (5,2)
- H[5][1] connecting (5,1) to (5,2)
This created a "corner trap" that isolated (4,2).

**Why validator didn't catch it:** Satisfiability only checks if CELLS can get enough edges, not if LOOSE ENDS can connect to form a closed loop.

**Lesson:** Need connectivity checking - verify loose ends can connect before continuing.

---

### Failure 6: Previous Ignoring Forced Edges Analysis (Steps 236-250)

**Step where detected:** 249 (via enhanced validator with --check-satisfiability)
**Unsatisfiable cells:** (2,1)=2, (2,2)=2, (3,3)=3, (4,1)=3
**Last valid step:** 235
**Backtrack step:** 251

**What happened:** At step 235, the validator showed FORCED edges:
- Cell (2,1)=2: FORCED ['bottom H', 'left V']
- Cell (2,2)=2: FORCED ['bottom H']
- Cell (2,3)=2: FORCED ['bottom H']

Instead of adding these forced edges, steps 236+ went down through V[3][3] and along the bottom row. This blocked all the forced edges, making cells (2,1), (2,2), (3,3), and (4,1) unsatisfiable.

**Root cause:** Forced edges were ignored. When a cell has exactly N available edges and needs N more, ALL those edges must be added - there's no alternative.

**Lesson:** ALWAYS prioritize FORCED edges shown by the validator. These are not suggestions - they are requirements. Add all forced edges before exploring other path options.

---

### Failure 7: Central 3-Cell Constraint Conflict (Steps 276-289)

**Step where detected:** 289 (via validator with --check-satisfiability)
**Unsatisfiable cell:** (1,2)=3, then (0,1)=3
**Last valid step:** 275
**Backtrack step:** 290

**What happened:** After adding V[2][2] at step 276, the path continued through the area around cell (1,2)=3. When trying to satisfy (0,3)=2, dots (1,3) and (2,3) became full, blocking critical edges for cell (1,2)=3.

**The conflict:**
- Cell (1,2)=3 needs 3 edges from {H[1][2], H[2][2], V[1][2], V[1][3]}
- Dot (2,2) already had V[2][2], limiting its capacity
- When (1,3) became full (blocking H[1][2] and V[1][3])
- And (2,3) became full (blocking H[2][2])
- Only V[1][2] remained, but adding it would make (2,2) full, blocking H[2][2]
- Cell (1,2)=3 could only get 2 edges maximum

**Root cause:** The path through the top-right area (satisfying cells (0,3)=2 and (1,4)=2) filled dots that cell (1,2)=3 needed. The central 3-cell requires special planning because it competes with multiple neighboring constraints.

**Lesson:** When multiple cells share corner dots (like a 3-cell in the center), plan the ENTIRE neighborhood together before committing edges. Check which dots are shared and ensure all cells can still be satisfied.

---

### Failure 8: Diagonal 3s + Corner Chain + Cell Conflict (Batches 3-7)

**Step where detected:** Batch 7 (via validator - BRANCHING at dot (4,3))
**Unsatisfiable cells:** Cell (2,3)=2 and cell (3,3)=3 conflict
**Last valid step:** Batch 2
**Backtrack step:** Batch 5

**What happened:** Three independent constraint chains collided at dot (4,3):

1. **Diagonal 3s pattern for (0,1)-(1,2):** Forces H[2][2] and V[1][3] which must pair at dot (2,3), blocking H[2][3] and V[2][3]. Cell (2,3)=2 can ONLY use H[3][3] and V[2][4].

2. **Cell (2,3)=2 constraint:** Needs both H[3][3] and V[2][4] at dot (3,4). If both pair there, V[3][4] is blocked.

3. **Corner (5,5) chain:** Forces V[4][3] at dot (4,3) via the chain (5,5)→H[5][4]→(5,4)→H[5][3]→(5,3)→V[4][3]→(4,3).

4. **Cell (3,3)=3 constraint:** If V[3][4] is blocked (from item 2), cell (3,3) must use H[3][3], H[4][3], V[3][3]. But H[4][3] requires a partner at (4,4), which is only V[3][4] (blocked!). So H[4][3] forces V[3][3] at (4,3).

**The impossible conflict at (4,3):**
- V[4][3] (from corner chain)
- H[4][3] (from cell (3,3))
- V[3][3] (from cell (3,3))
= 3 edges at one dot (BRANCHING - invalid!)

**Root cause:** The diagonal 3s pattern blocks cell (2,3)'s options, which blocks V[3][4], which forces cell (3,3) to use edges that conflict with the corner chain.

**Lesson:** When multiple constraint patterns (diagonal 3s, corner chains, numbered cells) converge on the same region, analyze them TOGETHER before adding any edges. A valid-looking local move can create impossible conflicts elsewhere.

**Possible resolution:** Either:
1. The puzzle has an error in cell values
2. The diagonal 3s at (0,1)-(1,2) must NOT follow the standard pattern (use different edge at shared corner)
3. Corner (5,5) must NOT be used (but this makes cell (3,3) unsatisfiable separately)

---

## General Solving Principles

### 1. Constraint Analysis First
Before placing ANY edge, analyze all numbered cells:
- Which cells have forced edges? (e.g., corners with 3s)
- Which cells have limited options?
- Are there constraint conflicts?

### 2. Handle "3" Cells Carefully
Cells with value 3 are the most constrained:
- They need 3 of 4 possible edges
- The loop must "wrap around" 3 sides
- Corner 3s are especially restrictive

### 3. Check Dot Capacities
Every dot can have 0 or 2 edges (never 1 or 3+). Before adding an edge:
- Check both endpoint dots have capacity
- Check if this blocks required future edges at nearby cells
- Count edges at adjacent dots to detect imminent branching

### 4. Identify Bottleneck Dots
Some dots serve multiple cells. For example, dot (3,3) in this puzzle:
- Needed by cell (2,2) for H[3][2]
- Needed by cell (2,3) for V[2][3]
- Needed by cell (3,3) for H[3][3] and V[3][3]

Plan these bottleneck dots carefully - often only one configuration works.

### 5. Work from Both Ends
Don't just extend one loose end. Trace from both loose ends to understand where they must meet and what constraints exist along both paths.

### 6. Avoid Long Segment Commits
Long path segments (like traversing an entire row) should be avoided until you've verified they don't block required edges. Instead:
- Add edges incrementally
- Verify cell constraints after each edge
- Be willing to "turn up" early if needed

### 7. Use Elimination
For each cell, list all possible edge combinations that give the required count. Eliminate combinations that:
- Would cause branching at any dot
- Would leave another cell unsatisfiable
- Would create a premature closed loop

### 8. Analyze Constraint Chains Globally
When diagonal 3s, corner constraints, and numbered cells interact:
- Trace ALL implications before adding edges
- Check if independent constraints can coexist
- If they conflict, the puzzle may have no solution OR a different pattern is needed

### Failure 9: The (3,5) Boundary Trap - Fundamental Unsolvability

**Step where detected:** Step 21 onwards (via constraint analysis)
**Problem:** Dot (3,5) on the right boundary cannot get 2 edges without violating constraints

**The conflict chain:**
1. Corner (5,5) MUST be used for cell (4,4)=2 → H[5][4] + V[4][5] forced
2. Cell (4,4)=2 is satisfied → H[4][4] and V[4][4] are blocked
3. Dot (4,5) has V[4][5]=1, needs 1 more → only V[3][5] works (H[4][4] blocked)
4. After V[3][5], dot (3,5) has 1 edge, needs 1 more
5. Options for (3,5):
   - H[3][4]: blocked (dot (3,4) full from H[3][3] + V[2][4])
   - V[2][5]: violates cell (2,4)=1 (already has V[2][4]=1)
6. NO VALID OPTION EXISTS → (3,5) is trapped

**Why this happens:**
- Diagonal 3s at (0,1)-(1,2) force H[2][2] + V[1][3], filling dot (2,3)
- Cell (2,3)=2 then MUST use H[3][3] + V[2][4], filling dot (3,4) and satisfying cell (2,4)=1
- This creates a constraint chain that blocks all paths to (3,5)

**Conclusion:** This puzzle appears UNSOLVABLE as given. The combination of:
- Two diagonal 3s pairs
- Cell (2,4)=1
- Cell (4,4)=2 corner constraint
creates an inescapable conflict at the right boundary.

**Possible resolutions:**
1. The puzzle has an error in one of the cell values
2. A different puzzle configuration is needed

---

## Recommended Solving Order

1. **Mark all 0s and 3s in corners** - these have forced patterns
2. **Identify all "3" cells** and note their edge requirements
3. **Find constraint triangles** - groups of cells sharing bottleneck dots
4. **Check for diagonal 3s** - apply pattern carefully, verify compatibility
5. **Start with forced edges** - edges that must exist regardless of path
6. **Extend from loose ends carefully** - always checking constraints
7. **Validate after every edge** - use the validator script

## Validation Checklist

After adding each edge:
- [ ] No dot has more than 2 edges
- [ ] No cell exceeds its number constraint
- [ ] The new edge connects to the existing partial loop
- [ ] Required future edges for nearby cells are still possible
- [ ] Neither loose end is trapped (has valid continuations)

## Common Patterns to Recognize

### Corner 3
A 3 in a corner forces 3 of its 4 edges. The 4th edge is definitely NOT part of the loop.

### Adjacent 3s
Two adjacent 3s share an edge. This edge is part of both cells' requirements.

### Diagonal 3s
Two diagonally adjacent 3s share a corner. Each uses exactly 1 edge at the shared corner, forcing both edges NOT at the shared corner to be used.

### 0 Cell
All 4 edges of a 0 cell are NOT part of the loop. This blocks paths through that area.

### 2 in Corner
A 2 in a corner has two possible configurations - often one is eliminated by adjacent cells.

## Debugging Failed Paths

When stuck:
1. Identify which cell(s) can't be satisfied
2. List what edges that cell needs
3. For each needed edge, identify why it's blocked
4. Backtrack to BEFORE the blocking edge was added
5. Try the alternative path from that point

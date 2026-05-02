# Slitherlink Strategy Guide (SHOULD rules - heuristics)

This file contains recommended strategies and heuristics. These are SHOULD rules, not MUST rules.

## Pre-Solving Analysis (SHOULD do first)

Before adding ANY edge:

1. **Identify all "0" cells** - Block all 4 edges around them immediately
2. **Identify all "3" cells** - These are the most constrained
3. **Find diagonal 3s pairs** - These have forced edge patterns
4. **Find corner 3s** - These have 3 of 4 edges forced
5. **Find bottleneck dots** - Dots that multiple cells depend on
6. **Check for constraint conflicts** - Can all cells be simultaneously satisfied?

## Common Patterns (SHOULD recognize)

### Corner 3
A 3 in a grid corner forces 3 of its 4 edges. The edge pointing into the corner is NOT used.

### Diagonal 3s
Two diagonally adjacent 3s share a corner dot. Each uses exactly 1 edge at the shared corner, forcing both edges NOT at the shared corner to be used for each cell.

### Adjacent 3s
Two adjacent 3s share an edge. That shared edge is part of the loop.

### Cell with 0
All 4 edges around a 0 cell are NOT part of the loop. Block them immediately with `X`.

### 2 in Corner
A 2 in a corner of the grid has two possible configurations. Often one is eliminated by adjacent cells.

## Pre-Move Analysis (SHOULD do before each edge)

Before adding ANY edge:

1. **Identify affected dots**: Which dots does this edge connect?
2. **Check dot capacity**: Will either dot become full (2 edges)?
3. **List blocked edges**: If a dot becomes full, which other edges are blocked?
4. **Check cascade effects**: For each blocked edge, will any cell become unsatisfiable?
5. **Verify path connectivity**: Does this edge connect to the existing partial loop?

## Recommended Solving Order (SHOULD follow)

1. Block all edges around 0-cells
2. Add forced patterns (corner 3s, diagonal 3s)
3. Add edges where only one option remains (forced by dot fullness)
4. Extend from path endpoints
5. When multiple options exist, try the one that satisfies more constraints

## When to Consider Backtracking (SHOULD evaluate)

- A cell cannot reach its required edge count
- A path endpoint has no valid continuation
- The validator reports unsatisfiable cells
- Two endpoints cannot connect without creating branches

## Efficiency Tips (SHOULD consider)

- Add forced edges first (no decision needed)
- Use blocked edge markers to track impossible moves
- When stuck, look for cells with only one valid configuration
- Track path endpoints and plan how they will connect

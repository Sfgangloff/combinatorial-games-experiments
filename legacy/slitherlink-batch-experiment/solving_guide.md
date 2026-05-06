# General Puzzle Solving Guide

This guide contains game-agnostic lessons learned from solving constraint-based puzzles. These principles apply to Slitherlink, Sudoku, and similar logic puzzles.

## Core Principles

### 1. Constraint Propagation
When a constraint has only one way to be satisfied, that solution is FORCED.
- **Always prioritize forced moves** - they have no alternatives
- Ignoring forced moves guarantees failure downstream
- After each move, re-check for new forced constraints

### 2. Satisfiability Checking
Before making a move, verify that all constraints CAN still be satisfied:
- Count current progress toward each constraint
- Count remaining options to reach the constraint
- If (current + available options) < required → UNSOLVABLE

### 3. Cascade Analysis
A single move can have ripple effects:
- Adding an element may block other elements
- Blocked elements may make other constraints unsatisfiable
- **Simulate forced moves** to detect cascade failures early

### 4. Connectivity Matters
For puzzles requiring connected structures (loops, paths):
- Satisfying individual constraints is NOT enough
- The overall structure must be achievable
- Loose ends must be able to connect
- Isolated segments indicate problems

### 5. Early Detection Saves Time
The earlier you detect an unsolvable state, the less backtracking needed:
- Validate after EVERY move
- Use the strongest validation available
- Don't proceed on invalid states

## Backtracking Strategy

### When to Backtrack
- Validator detects unsatisfiable constraints
- A required element becomes blocked
- Loose ends cannot connect (for connectivity puzzles)

### How to Backtrack Effectively
1. **Analyze the failure** - understand WHY it failed
2. **Find root cause** - which decision led to this?
3. **Document the lesson** - update guides for future reference
4. **Find last valid state** - use validator to verify
5. **Try alternative** - avoid the identified problem

### Lesson Documentation
After each failure:
1. Update specific guide with game-specific details
2. Update this general guide if lesson is broadly applicable
3. Consider enhancing validator if pattern is detectable

## Validator Enhancement Opportunities

When a failure reveals a detectable pattern:
- **Add the check to the validator**
- Better to catch problems automatically than manually
- Each failure is an opportunity to improve tooling

Common enhancements:
- Constraint satisfiability (can each constraint still be met?)
- Forced move detection (which moves have no alternative?)
- Cascade simulation (what happens if forced moves are applied?)
- Connectivity checking (can isolated parts connect?)

## Anti-Patterns to Avoid

### 1. Ignoring Forced Moves
If something MUST happen, do it immediately. Exploring other options first wastes time.

### 2. Shallow Validation
Checking only immediate constraints misses cascade failures. Always propagate.

### 3. Continuing on Invalid States
Never build on a broken foundation. Backtrack immediately when problems are detected.

### 4. Losing Lessons
Every failure teaches something. Document it or you'll repeat it.

### 5. Solving Constraints in Isolation
When multiple constraints share resources (shared variables, edges, cells), solving them independently leads to conflicts. Plan related constraints together before committing.

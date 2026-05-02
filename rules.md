# Slitherlink – Rules and Tutorial

## Goal

Draw **one single continuous closed loop** on the grid.

The loop must:
- Follow the grid edges between dots.
- Never cross itself.
- Never branch.
- Have no loose ends.
- Form exactly **one** loop (no smaller isolated loops).

---

## Numbers Inside Cells

Some cells contain numbers (usually 0–3).

A number indicates **exactly how many of the four sides of that cell are part of the loop**.

- **0** → no sides of the cell have a line.
- **1** → exactly one side has a line.
- **2** → exactly two sides have lines.
- **3** → exactly three sides have lines.
- Cells **without numbers** place no restriction on how many sides are used.

---

## Dot Rules (Global Loop Constraint)

At every dot:
- Either **no line** touches the dot, or
- **exactly two** line segments touch the dot.

This ensures the line passes through dots and forms a continuous loop.

Forbidden at a dot:
- Degree 1 (loose end)
- Degree 3 or 4 (branching or crossing)

---

## What Is Not Allowed

The following configurations are forbidden:
- A line ending at a dot.
- A crossing (four lines meeting at one dot).
- Multiple disconnected loops.
- A small closed loop that is separate from the main loop.

---

## Basic Logical Deductions

### Cell with 0
If a cell contains **0**, none of its four sides may contain a line.

All four surrounding edges can be marked as **forbidden**.

---

### Cell with 3
A cell has four sides.  
If it contains **3**, then three sides must contain a line.

If one side is already forbidden, the other three sides are **forced**.

---

### Propagation
Once lines are forced:
- Dot constraints often force continuation in specific directions.
- Some edges become impossible to use.
- These effects propagate to neighboring cells.

Repeated application of these deductions eventually determines the full loop.

---

## Solving Philosophy

- Slitherlink is intended to be solved **purely by logic**.
- Guessing is not required in a well-constructed puzzle.
- Work locally (cell constraints), then propagate globally (dot constraints).

---

## Name of the Puzzle

This puzzle is known as **Slitherlink**  
(also called *Fences* or *Loop the Loop*).

Formally, the solution is a **simple cycle** in the grid graph satisfying all numbered face constraints.
# Project context

This repo is an experiment in **MCP tools for Slitherlink solving**. We're comparing tool sets at different granularities (fine / medium / coarse) to see which best supports an LLM's reasoning. See `README.md` for the layout and goals.

- Slitherlink rules: `rules.md`
- Grid parser/validator: `validate_grid.py`
- Prior experiments (file-based batch protocol): `legacy/` — read-only reference

There is **no prescribed solving protocol** in this repo. When solving a puzzle, use the MCP tools that are available; when extending tools, follow the design notes in `README.md`.

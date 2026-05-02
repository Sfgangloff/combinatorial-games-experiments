# Failure Playbook

This file logs validation failures and backtrack decisions. Each failure MUST be documented here.

## Template for New Failures

```markdown
### Failure [N]: [Short description]
**Batch:** [batch number]
**Validator output:**
[paste the exact validator error message]

**Root cause:** [What edge/decision caused the failure]
**Cells affected:** [Which cells became unsatisfiable]
**Backtrack to:** Batch [M]
**Alternative to try:** [What different approach to take]
```

---

## Logged Failures

(Add new failures below this line)

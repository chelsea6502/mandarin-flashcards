---
name: Skip lengthy plan/spec review loops
description: User prefers not to run multiple rounds of automated spec/plan review agents
type: feedback
---

Don't run multi-iteration plan or spec review loops with subagents. Write the plan, present it to the user, and proceed.

**Why:** User interrupted a lengthy automated review loop mid-execution.

**How to apply:** Skip the plan-document-reviewer and spec-document-reviewer dispatch loops. Write the document, do a single quick sanity check internally if needed, then hand off to the user.

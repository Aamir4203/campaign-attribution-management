# CAM Project — Claude Code Instructions

## Model Workflow (REQUIRED)

**Planning Phase → Use Opus**
- For any non-trivial task, use `EnterPlanMode` before writing code.
- When spawning a Plan subagent, always set `model: "opus"` in the Task tool call.
- Opus handles architecture decisions, multi-file changes, and design trade-offs.

**Execution Phase → Use Sonnet**
- After the plan is approved, execute it in the current session (Sonnet).
- Sonnet handles file edits, bash commands, and implementation.

**Example Task tool call for planning:**
```json
{
  "subagent_type": "Plan",
  "model": "opus",
  "description": "Plan the implementation",
  "prompt": "..."
}
```

Keep plans focused: Opus designs, Sonnet builds.

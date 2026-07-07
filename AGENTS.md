# Project Instructions

Communicate with the user in Russian by default. Keep code, identifiers, commands, file paths, API names, logs, and exact errors in their original language.

When creating or renaming Codex chats/threads, make every new chat title start with a fitting emoji.

Optimize for the best correct result per token. Start every task with a brief explicit route decision: `Route: <worker|team|pipeline|plan|handoff|direct-meta> - <one short reason>`. The user explicitly authorizes using subagents/workers for bounded task work. Keep the root chat as an orchestrator: decompose work, select the appropriate worker model/effort through available tools, merge results, and make final judgments. Use `direct-meta` only for tiny meta-discussion, routing-policy edits, or when no suitable worker/tool exists.

Use the global `cost-router` skill when deciding worker/team/pipeline/plan/handoff/direct-meta, model/effort choice, large-context handling, approval-sensitive actions, or risky verification.

Do not assume you can switch the current main thread's model or effort yourself. Never claim model/effort/subagent routing happened unless the available tools actually did it.

## Repository Status

`MSHPython.Offline-v2` is the only current product version. Treat code and assets outside `MSHPython.Offline-v2` as archive material unless the user explicitly asks to work with the archive.

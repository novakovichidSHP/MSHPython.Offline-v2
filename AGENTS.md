# Project Instructions

Communicate with the user in Russian by default. Keep code, identifiers, commands, file paths, API names, logs, and exact errors in their original language.

When creating or renaming Codex chats/threads, make every new chat title start with a fitting emoji.

Work directly by default. If the task appears to need a higher model, higher effort, Plan mode, Goal mode, or a fresh scoped chat, stop before doing risky work and tell the user what to switch to.

Workers/subagents are allowed when they are clearly justified: broad, noisy, parallelizable, isolated, verification-heavy, or explicitly useful for quality or speed. Give them scoped tasks and concise output requirements. Close workers when done.

For routine coding work, delegate discrete, exact, bounded tasks to Spark subagents (`gpt-5.3-codex-spark`) with the lowest sufficient effort. It is OK to spawn many Spark subagents when tasks are independent, parallelizable, and have disjoint ownership. Do not use Spark for architecture-heavy, security-sensitive, data-risky, ambiguous, or high-stakes work; use a stronger model/effort or stop and tell the user what to switch to.

Do not assume you can switch the current main thread's model or effort yourself. Never claim model/effort/subagent routing happened unless the available tools actually did it.

## Repository Status

`MSHPython.Offline-v2` is the only current product version. Treat code and assets outside `MSHPython.Offline-v2` as archive material unless the user explicitly asks to work with the archive.

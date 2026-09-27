# Autonomous Agent Workspace (EvilMine)

A local, multipurpose AI agent framework. A FastAPI backend drives a local LLM (via Ollama) through a multi-step tool-calling loop, with a React + Electron desktop interface for managing sessions and watching the agent work in real time.

## What it does

- Runs an autonomous agent loop that can call tools, read/write files, and  as a core feature write, sandbox-test, and permanently integrate new tools for itself at runtime, without a restart.
- Includes a structured, phase-gated security-audit mode (SQLi/XSS) that requires the model to re-verify each patch against the file itself, rather than trusting a tool's own success message.
- Streams the agent's thinking, tool calls, and results live to a desktop UI.
- Saves and reloads conversation sessions as JSON files, so you can pick up a project where you left off.
- Includes file read/write/edit tools, a regex-based code search tool (grep, with a pure-Python fallback), and a directory index for navigating a project.

## Tech stack

**Frontend**
- React:  UI and state (chat history, streaming tokens, tool trace)
- Vite: dev server / build tool
- Electron:  wraps the UI as a desktop app, and provides native folder-picker access via IPC

**Backend**
- FastAPI: HTTP + WebSocket API in front of the agent manager
- Uvicorn: ASGI server
- Pydantic: request validation
- asyncio: non-blocking turn execution, plus a lock that serializes generations against the local model

**Model runtime**
- Ollama, served through an OpenAI-compatible endpoint. Defaults to a local Qwen model; a compatibility flag adjusts message-role handling and tool-call parsing for models that don't follow the same conventions.

**Dev tooling**
- `concurrently`  runs the frontend, Electron, and backend together via `npm run dev:desktop`

## How it works

1. You load or create a save file (a JSON conversation log) from the sidebar, optionally pointing the agent at a local project directory ("project mode").
2. Each message opens a WebSocket turn: the agent streams a response, and a custom parser scans that text for JSON tool-call blocks (rather than relying on the model's native function-calling format).
3. Detected tool calls run one at a time, with results fed back into the conversation so the agent can chain multiple tool calls across turns.
4. A loop guard watches for repeated text or repeated tool calls and nudges the model (via a temperature bump and a system warning) to break the pattern.
5. A read-file limiter tracks how many files and how many bytes get read per turn; past a threshold, the model is warned and older file contents are purged from context to control memory pressure.
6. Context is trimmed once the conversation approaches a token budget, dropping the oldest turns first while keeping tool call/response pairs intact.

Requires Ollama running locally with the target model pulled.

## Known limitations

This is an active work in progress. A few things worth knowing before extending it further:

- File read/write/edit/grep tools are contained to a sandboxed root directory (`get_safe_path`); tool execution and dynamic tool integration itself still aren't sandboxed a newly integrated tool runs with full process permissions.
- Dynamically generated/integrated tools aren't reviewed before being wired in treat `integrate_new_tool` output as trusted-local-use only.
- CORS, bind address, and auth are still permissive by default don't expose the server beyond localhost as-is.
- Sessions are single-user/single-connection; there's no per-session isolation yet.
- Directory indexing exists but isn't yet fully reconciled with the sandboxed workspace path treat it as a work in progress rather than a finished feature.

See `CHANGELOG.md` for what's shipped so far.

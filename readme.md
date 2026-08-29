# Autonomous Agent Workspace

A local, multipurpose AI agent framework. A FastAPI backend drives a local LLM (via Ollama) through a multi-step tool-calling loop, with a React + Electron desktop interface for managing sessions and watching the agent work in real time.

## What it does

- Runs an autonomous agent loop that can call tools, read/write files, and — as a core feature — write and integrate new tools for itself at runtime.
- Streams the agent's thinking, tool calls, and results live to a desktop UI.
- Saves and reloads conversation sessions as JSON files, so you can pick up a project where you left off.
- Indexes a local project directory so the agent can browse and search your codebase.

## Tech stack

**Frontend**
- React — UI and state (chat history, streaming tokens, tool trace)
- Vite — dev server / build tool
- Electron — wraps the UI as a desktop app, and provides native folder-picker access via IPC

**Backend**
- FastAPI — HTTP + WebSocket API in front of the agent manager
- Uvicorn — ASGI server
- Pydantic — request validation
- asyncio — non-blocking turn execution, plus a lock that serializes generations against the local model

**Model runtime**
- Ollama, served through an OpenAI-compatible endpoint (`qwen2.5-coder:14b` by default)

**Dev tooling**
- `concurrently` — runs the frontend, Electron, and backend together via `npm run dev:desktop`

## How it works

1. You load or create a save file (a JSON conversation log) from the sidebar.
2. Each message opens a WebSocket turn: the agent streams a response, and a custom parser scans that text for JSON tool-call blocks (rather than relying on the model's native function-calling format).
3. Detected tool calls run one at a time, with results fed back into the conversation so the agent can chain multiple tool calls across turns.
4. A loop guard watches for repeated text or repeated tool calls and nudges the model (via a temperature bump and a system warning) to break the pattern.
5. Context is trimmed once the conversation approaches a token budget, dropping the oldest turns first while keeping tool call/response pairs intact.


Requires Ollama running locally with the target model pulled (`qwen2.5-coder:14b` by default).



## Known limitations

This is an active work in progress. A few things worth knowing before extending it further:

- Tool execution and dynamic code integration aren't sandboxed — treat this as trusted-local-use only.
- File read/write tools aren't contained to a project root, so a misbehaving tool call can touch any file the process can reach.
- No authentication, and CORS defaults to permissive — don't expose the server beyond localhost as-is.
- Sessions are single-user/single-connection; there's no per-session isolation yet.

See `CHANGELOG.md` for what's shipped so far.
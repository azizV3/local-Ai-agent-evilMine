# Changelog



## [0.2.0] - 2026-08-07

### Added
- FastAPI backend wrapping the agent manager, with endpoints for listing, loading, creating, and summarizing save sessions, plus setting the active project directory.
- WebSocket endpoint (`/ws/agent`) streaming tokens, status updates, and tool results in real time.
- React dashboard: save-session picker, new-session creator, native folder browser (via Electron), live streaming chat view, and a tool-call trace panel.
- Directory indexing tool (`search_directory_index`) so the agent can browse and search the active project folder.
- Electron desktop shell with a native folder-picker IPC bridge.
- `concurrently`-based dev script (`npm run dev:desktop`) to run frontend, Electron, and backend together.

### Changed
- Refactored the agent's core execution loop into an `AsyncAgentManager` class.
- Added context-window trimming (16k token budget), dropping the oldest turns first while keeping tool call/response pairs together.
- Added a loop guard: detects repeated text or repeated tool calls, raises the sampling temperature temporarily to break the pattern, and warns the model via a system message.
- New save sessions now auto-initialize with the system prompt instead of starting blank.

### Fixed
- Tool execution is now wrapped in try/except, so a crashing tool returns a structured error to the model instead of taking down the server.
- Wrapped WebSocket turns in a single asyncio lock, so overlapping requests can no longer trigger concurrent generations against the local model.

### In progress
- A regex pass meant to strip tool-call JSON out of the model's visible text before saving it to history is implemented but not yet wired in the assistant message that actually gets stored still uses the raw, unstripped text.
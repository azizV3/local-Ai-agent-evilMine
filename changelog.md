# Changelog

## [0.1.9] - 2026-07-06

### Added
- Autonomous tool creation and testing pipeline (`extendedTools.py`): the agent can write a new tool, run it in an isolated subprocess to verify it works, and register it permanently without restarting the process (hot reload).
- Scratchpad module for short-term working notes separate from permanent file storage.
- File tools module (`fileManager.py`) for reading, writing, and editing files.
- Persistent file-writing capability so generated content can be saved to disk rather than only existing in-context.


## [0.2] - 2026-08-07

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
- Start working on the cybersecurity half of the agent

## [0.3] - 2026-09-27

### Added
- Project mode: lets the agent browse and operate on a user-selected local directory instead of a fixed workspace, with the selected folder sandboxed.
- Read-file context limiter (`READ_FILE_LIMITER`): caps how many files and how many bytes can be read per turn to protect the context budget.
- Mode switching between the default assistant mode and a dedicated web-security ("webmode") mode with its own system prompt.
- Compatibility mode for the Qwen 27B model (`QWEN27B_COMPATIBILITY`), adjusting message roles and autonomy behavior for that model's quirks.
- Grep-based code search tool (`scan_pattern`) with regex support and a pure-Python fallback for systems without system `grep`.
- Safer file editing: exact-match find-and-replace instead of full-file overwrites.
- Ability for the agent to run executable scripts/commands as part of its workflow.
- Logging of file edits, file reads, and grep queries to dedicated log files for traceability.

### Fixed
- Added `get_safe_path` to contain all file operations within a sandboxed root directory, closing a path-traversal gap in file read/write/edit tools.

### In progress
- Improving loop prevention so it generalizes across different models rather than being tuned to one.
- Expanding the cybersecurity audit modes beyond the initial SQLi/XSS pass.
- Re-integrating compatibility with cloud-hosted models alongside the local Ollama setup.
- Settings UI panel for adjusting agent constants at runtime.
- Fine-tuning a model for the agent's specific tasks.
- General optimization pass: imports, context usage, and prompt length.
- Streaming support for a mobile app client.

### Notes
- Spun off two related side projects from this codebase: a Minecraft-playing agent ("craftmine") and a desktop-vision/manipulation agent ("neuromine").
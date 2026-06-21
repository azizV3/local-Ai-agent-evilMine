# evilMine

A lightweight, local autonomous agent loop built to run models through Ollama. 

Most local 7B models struggle with multi-turn tasks because they drop out of character, break JSON formatting, or get stuck in repetitive loops. This framework adds a custom middleware layer to keep the agent structured, stable, and running completely locally.

>**Development Note:** This is an experimental v0.1 prototype. The core architecture is completely decoupled from the provider, meaning it can be easily adapted to run on any OpenAI-compatible API backend with minimal config changes.

Key Design Choices

* **Why Custom JSON Parsing Over Native Tool Calls?** This engine intentionally avoids relying on native LLM provider tool-calling structures. Many lightweight local models—as well as various local inference streaming setups—either lack native tool support or break format mid-stream. By using raw streaming text and intercepting it with our parser, the framework remains model-agnostic and incredibly resilient.
* **Balanced Bracket Parser:** To make the custom routing work, the loop uses a bracket-matching counter (`brace_count`). It isolates and extracts functional tool arguments directly from raw text stream buffers, even if the model surrounds the JSON block with casual conversational text.
* **Context Trimming Logic:** To stop long-running threads from overflowing the context window, `trim_context` dynamically drops old messages. It handles this turn-by-turn rather than slicing raw strings, ensuring it never leaves an orphaned assistant request or tool result that would crash the model.
* **Failsafe Circuit Breaker:** Local models love a phrase loop trap. The engine monitors consecutive turns for phrase matching or tool spam. If a loop is caught, it injects a harsh system prompt to redirect the model. If it fails to self-heal after 3 tries, a hard circuit breaker trips to prevent infinite loops and returns control back to the terminal prompt.
* **Persistent Sessions & Summarization:** Features a dynamic interactive startup menu to load or create clean session files (`.json`). It also includes a summarization feature that pipes historical conversation arrays back through the model to distill long sessions before saving.


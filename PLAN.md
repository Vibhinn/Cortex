# Cortex — build plan

A personal agent that chats with you, remembers you across chats, searches your documents (RAG), and uses tools through MCP.

Stack: Python 3.12+, `uv`, Anthropic SDK, MCP Python SDK, Postgres + pgvector (Docker), CLI first.
Models: `claude-sonnet-5-5` (main agent), `claude-haiku-5-5` (cheap background jobs).

Rule: do one step at a time, and don't move on until its **Done when** check passes.

---

## Phase 0 — Setup

- [ ] **0.1** Install `uv` and Python 3.12+. Run `uv init` in this folder, then `git init`.
  - Done when: `uv run python -c "print('ok')"` works.
- [ ] **0.2** Get an Anthropic API key and put it in `.env`. Load it with `python-dotenv`. Add `.env` to `.gitignore`.
  - Done when: `os.environ["ANTHROPIC_API_KEY"]` prints (the first few characters only).
- [ ] **0.3** Hello world: send "hi" to the model with the SDK and print the reply.
  - Done when: you see Claude's reply in the terminal.

## Phase 1 — Chat loop (the basics of short-term memory)
Learn: the model is **stateless**, so "memory" inside a chat is just you resending the whole history every turn.

- [ ] **1.1** Read user input in a `while True` loop with `input()`. Exit on `/quit`.
  - Done when: it echoes back whatever you type.
- [ ] **1.2** Send each input to the model and print the reply.
  - Done when: you can chat, but it forgets everything between turns.
- [ ] **1.3** Keep a `messages` list. Append each user message and assistant reply, and send the full list every time.
  - Done when: "my name is V" → "what's my name?" gets the right answer.
- [ ] **1.4** Add a system prompt (personality and rules).
  - Done when: changing the system prompt clearly changes how it behaves.
- [ ] **1.5** Stream the reply token by token instead of waiting for the full response.
  - Done when: text appears as it's generated.
- [ ] **1.6** Print token usage (input/output) and estimated cost after each turn.
  - Done when: you can watch input tokens grow as the chat gets longer (that's why later phases exist).
- [ ] **1.7** Handle API errors: retry with backoff on rate limits and overload errors.
  - Done when: a forced error (e.g. a bad model name) prints a clean message instead of crashing.

## Phase 2 — Tools and the agent loop
Learn: an **agent** is a loop: the model asks for a tool, you run it, you send the result back, and it repeats until the model is done.

- [ ] **2.1** Define one tool, `get_current_time`, with a JSON schema, and pass it in the API call.
  - Done when: asking "what time is it?" returns a `tool_use` block (print the raw response).
- [ ] **2.2** When `stop_reason == "tool_use"`, run the function and send back a `tool_result` message.
  - Done when: the model answers with the real time.
- [ ] **2.3** Turn that into a loop that runs until `stop_reason == "end_turn"`. Cap it at about 10 iterations.
  - Done when: a question that needs 2 tool calls in a row works.
- [ ] **2.4** Build a tool registry, `{name: (function, schema)}`, and add `read_file`, `list_dir`, and `calculator`.
  - Done when: adding a new tool takes one line in the registry.
- [ ] **2.5** Tool errors: catch exceptions and return `is_error: true` with the message.
  - Done when: reading a missing file makes the model say so and recover gracefully.
- [ ] **2.6** Human approval: mark tools as "dangerous" (e.g. `write_file`) and ask y/n before running them.
  - Done when: answering "n" makes the model get a "user denied" result and carry on.
- [ ] **2.7** Log every tool call (name, inputs, output, duration) to the console.

## Phase 3 — Saving conversation history
Learn: storing threads and messages so many chats survive restarts.

- [ ] **3.1** Run Postgres in Docker using the `pgvector/pgvector` image. Connect from Python (`psycopg`).
  - Done when: `SELECT 1` works from Python.
- [ ] **3.2** Create tables: `threads(id, title, created_at, updated_at)` and `messages(id, thread_id, role, content JSONB, created_at)`.
  - Store `content` as JSON, because messages can hold text, tool_use, and tool_result blocks.
- [ ] **3.3** Save every message as it happens.
  - Done when: you can see your chat in the database after quitting.
- [ ] **3.4** CLI commands: `/new`, `/list` (shows threads), and `/open <id>` (loads the messages back into `messages`).
  - Done when: you can restart the app, reopen an old chat, and it remembers the context.
- [ ] **3.5** Auto-title: after the first exchange, have the cheap model write a 5-word title for the thread.
- [ ] **3.6** `/search <words>`: keyword search across all past messages (Postgres full-text search: `tsvector`).
  - Done when: you can find a chat from last week by a word you used in it.

## Phase 4 — MCP
Learn: MCP is a standard way to plug tools into any agent. **Host** = your app, **client** = one connection, **server** = the tool provider. Servers expose tools, resources, and prompts.

- [ ] **4.1** Read the MCP intro docs. Run an existing server (e.g. `@modelcontextprotocol/server-filesystem`) in **MCP Inspector** and call a tool by hand.
  - Done when: you understand `initialize → tools/list → tools/call`.
- [ ] **4.2** Create `mcp.json`, which lists servers (`command`, `args`, `env`). Use the same shape as Claude Desktop's config.
- [ ] **4.3** Connect to **one** stdio server with the MCP Python SDK (`ClientSession`). Call `list_tools()` and print the results.
  - Done when: you see the server's tools printed from *your* code.
- [ ] **4.4** Convert MCP tool schemas into Anthropic tool format and merge them into your registry. Prefix the names: `filesystem__read_file`.
- [ ] **4.5** Route tool calls: if a name has a server prefix, call `session.call_tool()` on that server and return the result.
  - Done when: the agent uses an MCP tool to answer a question.
- [ ] **4.6** Connect to all servers in `mcp.json` at startup. If one fails, log it and continue without it.
- [ ] **4.7** Add a **remote** server over streamable HTTP (e.g. a GitHub MCP server).
- [ ] **4.8** **Build your own MCP server** with `FastMCP`: a "notes" server with `add_note` and `search_notes`. Connect your agent to it.
  - Done when: your agent saves and finds notes through your own server.
- [ ] **4.9** (Later) Support MCP **resources** and **prompts**, not just tools.

## Phase 5 — RAG (search your own documents)
Learn: **R**etrieve the relevant pieces → **A**ugment the prompt → **G**enerate. The core of it is "turn the question into a vector and find the closest matching chunks".

- [ ] **5.1** Pick a folder of your docs (markdown, txt, later PDFs). Write a loader that returns `(path, text)` for each file.
- [ ] **5.2** Chunking: split each document into roughly 500-token chunks with about 50 tokens of overlap. Keep `source` and `position`.
  - Done when: you can print the chunks for one file and they look sensible.
- [ ] **5.3** Embeddings: pick a model (Voyage `voyage-3.5`, or local `sentence-transformers`). Embed 3 sentences and compute cosine similarity by hand.
  - Done when: similar sentences score higher than unrelated ones. *This is the "closest match" idea.*
- [ ] **5.4** Table: `chunks(id, source, position, content, content_hash, embedding vector(N), tsv tsvector)`. Add a vector index (HNSW).
- [ ] **5.5** Ingest script: load → chunk → embed → insert. Skip files whose hash hasn't changed.
  - Done when: re-running ingest on unchanged files does nothing.
- [ ] **5.6** **Vector search**: embed the query and get the top-k chunks by cosine distance (`<=>`).
  - Done when: `python search.py "question"` prints relevant chunks.
- [ ] **5.7** **Keyword search**: the same, using Postgres full-text search (good for exact names, codes, and IDs).
- [ ] **5.8** **Hybrid search**: combine both result lists with Reciprocal Rank Fusion (RRF).
- [ ] **5.9** **Rerank**: take the top 20 from hybrid search, rerank them (Voyage rerank or a cross-encoder), and keep the top 5.
- [ ] **5.10** **Agentic RAG**: expose all this as a `search_knowledge(query)` tool. The agent decides when to search, can search again with a better query, and cites sources.
  - Done when: an answer includes `[source: file.md]` and is correct.
- [ ] **5.11** **Contextual retrieval**: before embedding, have the cheap model prepend 1–2 sentences of document context to each chunk.
- [ ] **5.12** Build a test set of about 15 questions with known answer sources. Measure **recall@5** (is the right chunk in the top 5?). Re-measure after 5.8, 5.9, and 5.11.
  - Done when: you have numbers showing which upgrades actually helped.

## Phase 6 — Long-term memory
Learn: the types of memory.
- **Working**: the current context window.
- **Episodic**: what happened ("last Tuesday we debugged auth").
- **Semantic**: facts ("V prefers Python", "V works at X").
- **Procedural**: how to behave ("always answer briefly").

- [ ] **6.1** Table: `memories(id, type, content, embedding, importance 1-10, created_at, last_accessed, source_thread_id)`.
- [ ] **6.2** `remember(content, type, importance)` tool: the agent saves facts itself when you tell it something worth keeping.
- [ ] **6.3** `recall(query)` tool: vector search over memories.
  - Done when: in a **new** chat, "what language do I prefer?" is answered from memory.
- [ ] **6.4** Auto-inject: before every turn, fetch the top 3–5 relevant memories and put them in the system prompt.
- [ ] **6.5** Extraction: when a chat ends (or every N turns), the cheap model reads the thread and outputs facts as structured JSON, which you save.
- [ ] **6.6** Dedup and conflicts: before saving a fact, find similar memories and have the LLM choose **ADD / UPDATE / DELETE / NOOP** (this is how Mem0 works).
  - Done when: "I moved to Bangalore" *updates* the old city instead of adding a contradicting memory.
- [ ] **6.7** Episodic memory: save an embedded summary of each thread.
  - Done when: "what did we talk about last week?" works.
- [ ] **6.8** Scoring: rank memories by `similarity + recency + importance` (from the "Generative Agents" paper).
- [ ] **6.9** `/memories` command: list, edit, and delete memories. The user stays in control.
- [ ] **6.10** Procedural memory: a `preferences.md` file that's always in the system prompt and that the agent can propose edits to.

## Phase 7 — Context engineering
Learn: deciding what goes into the context window each turn, and keeping it small, cheap, and relevant.

- [ ] **7.1** Print a per-request token breakdown: system / tools / memories / RAG / history.
- [ ] **7.2** **Prompt caching**: add `cache_control` to the system prompt and tools.
  - Done when: `cache_read_input_tokens` > 0 on the second turn and cost drops.
- [ ] **7.3** Trim old tool results: replace big outputs from more than N turns ago with `[trimmed]`.
- [ ] **7.4** **Compaction**: when history goes over X tokens, have the cheap model summarize the older turns and keep the last N turns word for word.
  - Done when: a very long chat keeps working and stays under budget.
- [ ] **7.5** **Tool search**: with many MCP tools, expose only a `search_tools` tool plus a few core tools, and load the others' schemas on demand.
- [ ] **7.6** A token budget per section, so RAG and memories can't crowd out the conversation.

## Phase 8 — Observability and evals
Learn: you can't improve what you can't measure. This is what separates real AI engineering from demos.

- [ ] **8.1** Tracing: self-host Langfuse (Docker) and trace each turn → LLM calls → tool calls → retrieval.
  - Done when: you can click into one turn and see everything that happened.
- [ ] **8.2** Eval set: about 30 tasks (memory recall, RAG questions, multi-step tool use), each with expected behavior.
- [ ] **8.3** **LLM-as-judge** script: run all tasks, have a model grade each answer against a rubric, and print a score.
- [ ] **8.4** Run the evals before and after every significant change. Keep a `results.md` log.

## Phase 9 — Advanced
- [ ] **9.1** **Subagent**: a `research(topic)` tool that starts a separate agent with its own context and returns only a summary.
- [ ] **9.2** Nightly **memory consolidation** job: merge duplicates, decay unused memories, delete stale ones.
- [ ] **9.3** Scheduled tasks (e.g. a morning brief built from calendar + notes + memories).
- [ ] **9.4** FastAPI backend with streaming (SSE) and a simple web UI.
- [ ] **9.5** Optional: GraphRAG / an entity knowledge graph, extended thinking for hard tasks, structured outputs everywhere.

---

## Suggested layout (grow into it, don't create it all on day 1)
```
cortex/
  main.py          # CLI loop
  agent.py         # agent loop
  llm.py           # API calls, retries, streaming
  tools/           # local tools + registry
  mcp_client.py    # MCP connections
  db.py            # Postgres
  rag/             # loader, chunker, embed, search
  memory/          # store, extract, recall
  context.py       # prompt assembly, compaction
evals/
mcp.json
```

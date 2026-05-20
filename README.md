# Memory Archive Agent

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)
[![LangGraph](https://img.shields.io/badge/built%20with-LangGraph-8A2BE2.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Electron](https://img.shields.io/badge/Desktop-Electron-47848F.svg)](https://www.electronjs.org/)

**English** | [中文文档](README_zh.md)

**Drop files, paste links, type naturally — AI understands, classifies, and archives into your personal knowledge base.**

Memory Archive Agent (MAA) is an AI-driven desktop knowledge management tool built on a ReAct agent architecture. It automatically parses, classifies, and stores your documents into a local Markdown + Git knowledge base — no database, no lock-in.

## 📸 Screenshot

![MAA Desktop App](asset/image.png)

---

## ✨ Features

- **Smart Archiving** — Drag in files or paste URLs; the AI agent parses, classifies, and writes structured Markdown archives with auto-generated tags and categories
- **Natural Language Search** — Ask questions in plain language; the agent searches your knowledge base and returns precise answers with file references
- **Batch Processing** — Drop multiple files at once for automatic sequential archiving
- **Streaming Responses** — Real-time SSE streaming shows progress ("parsing → classifying → archiving → done")
- **Clickable File Links** — Agent responses include `[file:path]` links; click to open, right-click for copy/reveal
- **Git Sync** — Automatic version control of your entire knowledge base with push/pull support
- **Cross-Platform** — Works on Windows, macOS, and Linux
- **Open Storage Format** — Pure Markdown + YAML frontmatter + Git, fully portable

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│            Desktop App (Electron)                │  ← Your workspace
├─────────────────────────────────────────────────┤
│            HTTP API (FastAPI + SSE)              │  ← Streaming + REST
├─────────────────────────────────────────────────┤
│     ReAct Agent (LangGraph) ── LLM decides       │  ← No hardcoded flows
├─────────────────────────────────────────────────┤
│  17+ Tools ─ parse / archive / search / sync    │  ← Pluggable, independent
├─────────────────────────────────────────────────┤
│     Local Storage ── Markdown + Git (Zero-DB)    │  ← Filesystem is truth
└─────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Meaning |
|-----------|---------|
| **Agent is the Core** | LLM autonomously selects tools; no preset archive/query modes |
| **Tools are Independent** | Plug-and-play; add a tool by extending `BaseTool` and registering |
| **Filesystem is Truth** | Markdown + Git, open format, zero database, fully migratable |
| **Fault Tolerance First** | Local write-first; network/LLM failures don't crash the system |

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (backend)
- Node.js 18+ (frontend / desktop app)
- An LLM API key (DashScope, OpenAI, Claude, or any OpenAI-compatible provider)

### Installation

#### Backend

```bash
git clone https://github.com/YOUR_USERNAME/Agent-Memory-Archive.git
cd Agent-Memory-Archive
pip install -e .
```

Dependencies installed automatically:

| Package | Purpose |
|---------|---------|
| `langgraph` + `langchain-*` | ReAct Agent engine |
| `fastapi` + `uvicorn` | HTTP API server |
| `markitdown` | Multi-format file parsing |
| `pydantic` | Data validation |
| `click` | CLI framework |

#### Frontend (Desktop App)

```bash
cd desktop
npm install
```

| Package | Purpose |
|---------|---------|
| `electron` | Desktop app framework |
| `react` + `react-dom` | UI framework |
| `vite` | Build tool + dev server |
| `concurrently` + `wait-on` | Dev workflow orchestration |

#### Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your API credentials:

```env
DASHSCOPE_API_KEY=sk-your-api-key
# FIRECRAWL_API_KEY=your-firecrawl-key   # optional, for web scraping
```

### Configuration

```bash
cp config.example.json config.json
```

Edit `config.json` with your LLM credentials:

```json
{
  "llm": {
    "provider": "dashscope",
    "api_key": "sk-your-api-key",
    "model": "qwen3.6-plus",
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"
  },
  "storage": {
    "root": "~/MemoryArchive"
  },
  "git": {
    "repo_url": "git@github.com:your-username/agent-memory.git",
    "branch": "main"
  }
}
```

### Launch

```bash
# Start the desktop app (auto-starts the backend server)
cd desktop && npm run electron:dev
```

Or use the CLI REPL without the desktop app:

```bash
python cli.py
```

The backend server starts automatically with the desktop app. If you need to start it manually:

```bash
python server.py
# Server running at http://127.0.0.1:8899
```

## 📖 Usage

### Desktop App

1. **Archive a file** — Drag any file (.md, .pdf, .docx, .xlsx, .pptx, .txt) into the input box
2. **Archive a webpage** — Paste a URL; the agent scrapes and extracts content via Firecrawl
3. **Search your knowledge** — Type a question like "What did I learn about vector databases?"
4. **Open archived files** — Click `[file:path]` links in agent responses

### CLI REPL

```
> ~/Downloads/paper.pdf
# Agent parses, classifies, and archives the PDF

> https://example.com/article
# Agent scrapes the webpage and archives the content

> What have I saved about machine learning?
# Agent searches the knowledge base and summarizes relevant files
```

### REST API

The server exposes these endpoints at `http://127.0.0.1:8899`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Streaming conversation via SSE (`{message, language}`) |
| `/archive` | POST | Archive content (`source_path`, `content`, or `url`) |
| `/search` | GET | Search the knowledge base (`?q=keyword`) |
| `/tree` | GET | Get knowledge base directory tree |
| `/projects` | GET | List project folders |
| `/files/{path}` | GET | Read an archived file by path |
| `/tools` | GET | List all available agent tools |
| `/open-file` | GET | Open file with system default app |
| `/reveal-file` | GET | Reveal file in file manager |

Interactive API docs available at `http://127.0.0.1:8899/docs`.

## 🛠️ Tools

The agent has access to 17+ independent tools:

| Category | Tools | Description |
|----------|-------|-------------|
| **Parsing** | `parse_file`, `extract_content` | Multi-format file parsing (MarkItDown) + web scraping (Firecrawl) |
| **Archiving** | `archive_file`, `update_index`, `sync_index` | Write archives with smart dedup + maintain dual indexes |
| **Search** | `search_index`, `read_file`, `list_projects` | Full-text search, file reading, project listing |
| **Navigation** | `list_tree`, `list_dir` | Directory tree scanning with folder-level summaries |
| **Classification** | `classify_content`, `scan_directory`, `batch_classify`, `batch_archive` | LLM-based auto-classification with batch processing |
| **Git** | `git_sync`, `git_status`, `git_remote_info` | Git operations with smart auto-repair |
| **Export** | `pull_to_local` | Copy files from knowledge base to any local directory |
| **System** | `code_run` | Safe read-only diagnostic commands (15-pattern blacklist) |

## 📁 Storage Structure

```
~/MemoryArchive/
├── .maa/
│   ├── index.json          # Global machine-readable index
│   └── project_map.json    # Cross-folder project mapping
├── projects/               # Engineering projects
│   └── my-project/
│       ├── .index.md       # Folder-level index (human + LLM readable)
│       └── notes.md        # Archived document with YAML frontmatter
├── research/               # Academic research, papers, tech surveys
├── personal/               # Personal background, preferences, essays
└── inbox/                  # Unsorted staging area
```

### Dual-Index Design

- **Global Index** (`.maa/index.json`) — JSON-based, for fast programmatic search
- **Folder Index** (`.index.md`) — Markdown with frontmatter, provides semantic context for LLM classification

### Archive File Format

Every archived file includes YAML frontmatter:

```yaml
---
type: memory_archive_agent
category: projects
project: my-project
tags: [tag1, tag2]
created_at: 2026-05-18
original_title: Original Filename.pdf
---

# Content goes here...
```

### Smart Deduplication

The `archive_file` tool uses content-overlap scoring to prevent data loss:

| Overlap | Action |
|---------|--------|
| ≥ 95% | Skipped (exact duplicate) |
| 85–95% | Delta appended (only new lines added) |
| 40–85% | Appended (full text with timestamp) |
| < 40% | Rejected with suggested alternative filename |

## 🔧 Development

### Project Structure

```
src/maa/
├── agent/        # ReAct agent core (engine, graph, prompt, tool adapter)
├── tools/        # 17+ pluggable tools (parse, archive, search, sync, etc.)
├── storage/      # Storage layer (repo manager, dual index, data models)
├── channels/     # I/O channels (CLI, future: MCP, Feishu, Telegram)
├── server/       # FastAPI HTTP API (routes, SSE streaming)
└── config.py     # Configuration management with .env support

desktop/          # Electron desktop app (React + TypeScript + Vite)
docs/             # Architecture and design documentation
openspec/         # Change proposals (planned features)
```

### Adding a New Tool

1. Create a file in `src/maa/tools/`
2. Extend `BaseTool` with `name`, `description`, `param_schema`, and `execute()`
3. Register in `src/maa/tools/__init__.py`

### Running Tests

```bash
pytest tests/
```

## 🗺️ Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| **Phase 1** | Core engine + toolset + CLI + API + Desktop app | ✅ Done |
| **Phase 2** | MCP Server (Claude Code / Cursor integration) | 📋 Planned |
| **Phase 3** | Feishu Bot + Telegram Bot | 📋 Planned |
| **Phase 4** | Browser extension + file watching + multi-model support | 📋 Planned |

## 📄 License

MIT

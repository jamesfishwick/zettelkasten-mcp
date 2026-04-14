# Contributing to slipbox-mcp

Thanks for your interest in contributing. This guide covers setup, standards, and how to submit changes.

## Getting Started

```bash
git clone https://github.com/jamesfishwick/slipbox-mcp.git
cd slipbox-mcp
uv venv --python 3.13 && uv sync --all-extras
```

Run the test suite to verify your setup:

```bash
uv run pytest tests/
```

## Project Structure

```text
src/slipbox_mcp/
  server/          # MCP server, tool registrations, prompts
    tools/         # Tool implementations (note, link, search, cluster)
    descriptions.py  # All tool/prompt text (single source of truth)
    prompts.py     # MCP prompt registrations
    resources.py   # MCP resource endpoints
  services/        # Business logic (zettel, search, cluster)
  storage/         # SQLite repository, note file I/O
  models/          # Pydantic schemas, DB models
  cli.py           # Terminal CLI (slipbox command)
tests/             # Unit + integration tests
evals/             # Tool contract tests + LLM evals
```

## Making Changes

1. **Create a branch** from `main`
1. **Write tests** for new functionality -- see `tests/` for patterns
1. **Run the full suite** before submitting: `uv run pytest tests/ evals/tool_contracts/` and `uv run ruff check src/ evals/`
1. **Open a PR** against `main`. CI runs unit tests and ruff automatically.

## What to Work On

- Issues labeled `good first issue` are scoped for new contributors
- Check the [ROADMAP.md](ROADMAP.md) for planned features
- Bug reports and documentation improvements are always welcome

## Coding Standards

- **Lint**: `ruff check` must pass
- **Tests**: new tools need both unit tests and tool contract tests
- **Prompts**: all tool descriptions and prompt templates live in `src/slipbox_mcp/server/descriptions.py` -- this is the single source of truth imported by both the server and the eval suite
- **Tool output**: tools return formatted strings, not raw data. The output must be useful to an LLM reading it. Tool contract tests in `evals/tool_contracts/` verify this.

## LLM Evals

If you change tool descriptions or prompt templates, run the LLM evals locally:

```bash
uv run pytest evals/llm/ -v
```

These send prompts to Claude via the `claude` CLI with the MCP server connected and grade the results. They require a Claude API key and cost ~$3-5 per run.

## Architecture Principles

- **Files are the source of truth.** The SQLite database is an index. Deleting it and running `slipbox_rebuild_index` must always recover the full state.
- **Claude processes content, not generates it.** The MCP tools help Claude format, link, and integrate the user's ideas -- not create ideas from nothing.
- **Search before create.** Every workflow that creates notes should search for existing related notes first to avoid duplication.
- **Typed links matter.** Seven link types enable purposeful graph navigation. Generic "related" links are a last resort.

## Questions?

Open an issue or start a discussion on the [GitHub repo](https://github.com/jamesfishwick/slipbox-mcp).

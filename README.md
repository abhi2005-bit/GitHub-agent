# DevPilot Agent

DevPilot is a read-only, AI-assisted engineering agent. It interprets a request, creates a deterministic plan, checks policy, retrieves evidence from a registered GitHub repository, and reports what it can support from that evidence.

## Current capabilities

- Inspect GitHub repository metadata and a recursive repository tree. Tree responses over 5,000 entries are marked and limited to the first 5,000 entries.
- Read UTF-8 text files from the configured repository branch, up to 1 MB per file.
- Review one or more explicitly named files. Python files are parsed with `ast` without execution. Review findings are structured and checked against retrieved paths, line ranges, and exact source excerpts. Invalid model findings are withheld with an explicit limitation.
- Inspect basic GitHub repository health signals from repository metadata.
- Search open GitHub issues, optionally using an explicitly stated topic.
- List recent GitHub Actions runs for the configured branch.
- Reject any plan containing a step marked as requiring approval. No write operations are currently registered.

Issue handling is read-only discovery and inspection. It does not create, edit, close, or comment on issues. CI investigation reports API run data; it does not fetch logs or rerun workflows.

## Architecture

```text
Request → Understander → Planner → PolicyEngine → Executor → GitHub tools
               │                                         │
               └──────────── intent and file paths ──────┘
                                                         ↓
                                               Analyzer → AgentRun
```

`app/bootstrap.py` wires the components. `AgentRunner` owns lifecycle state and passes the detected intent to `Analyzer`. Tools use `GitHubClient`; registered projects are held in an in-memory `ProjectRepository` for the duration of one CLI session.

## Technology

- Python 3.11+
- `uv` for environment and dependency management
- Pydantic models, pytest, HTTPX, Groq API client, and python-dotenv
- GitHub REST API for repository metadata, trees, files, issues, and Actions runs

## Setup

Install Python 3.11 and [uv](https://docs.astral.sh/uv/), then:

```powershell
uv sync
```

Create a `.env` file in the repository root or configure the variables in your shell:

```dotenv
GROQ_API_KEY=your_groq_api_key
# Optional. Public repository reads work without this token.
GITHUB_TOKEN=your_github_token
```

`GROQ_API_KEY` is needed for request understanding and analysis. `GITHUB_TOKEN` is optional and is sent only to GitHub API requests when set; use a token with the least access needed. Do not commit `.env` or paste credentials into requests. `.env` is ignored by Git.

## Register and run

Start the CLI:

```powershell
uv run python -m app.main
```

Enter a project display name, GitHub owner, repository name, and branch. Registration stores these values in memory and does not verify the repository until a request calls GitHub. Then enter a request such as:

- `Show me the structure of this repository.`
- `Read app/main.py.`
- `Review app/main.py for bugs.`
- `Review app/main.py and app/agent/planner.py for reliability issues.`
- `Investigate the latest GitHub Actions failures.`
- `Find open issues relating to authentication.`

The Actions request inspects recent workflow runs on the branch entered during registration. Issue search is read-only. If the API response is unavailable, the agent reports the failure rather than claiming the data was inspected.

## Tests

Run the deterministic unit suite:

```powershell
uv run pytest
```

Tests use fake LLM responses and mocked GitHub transports; the suite does not require a Groq key or live GitHub access.

## Security and limitations

- Retrieved repository content is treated as untrusted evidence. It cannot authorize tool calls or override the agent's instructions.
- DevPilot does not execute or modify repository code. It does not run tests, shell commands, or static security scanners.
- Code review is bounded to 20,000 characters per retrieved source file for model analysis; reports identify truncation. AST parsing uses the original, unmodified Python source.
- Findings are not proof of correctness or security. They are limited to the supplied source and model analysis. Invalid paths, locations, evidence, or schema output are not reported as validated findings.
- Repository registrations are not persisted. Only GitHub-backed projects are supported by the current CLI tools.
- Health signals are limited to GitHub repository metadata. CI details are limited to recent Actions run summaries, without logs or job-level analysis.
- GitHub API permissions and rate limits may restrict access. Private repositories generally require a suitable `GITHUB_TOKEN`.

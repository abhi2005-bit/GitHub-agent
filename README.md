# DevPilot Agent

**An LLM-powered engineering agent for understanding software development requests and retrieving real repository context.**

DevPilot Agent is a modular AI agent built in Python that combines large language models, structured planning, policy-controlled execution, and GitHub integration. It is designed to evolve beyond a generic chatbot into an engineering-focused agent that can inspect repositories and assist developers with understanding their projects.

The project follows a modular architecture that separates reasoning, planning, policy enforcement, tool execution, and external integrations.

> **Status:** Work in progress. GitHub repository metadata retrieval and file-tree listing are implemented. Source-code analysis, persistent project storage, and broader engineering workflows are under development.

## Features

- **LLM-powered goal understanding:** Uses Groq to interpret natural-language engineering requests and produce structured understanding data.
- **Structured project models:** Uses Pydantic to represent projects, agent plans, execution results, and tool responses.
- **Deterministic planning:** Converts supported engineering intents into execution plans.
- **Policy-controlled execution:** Evaluates plans before allowing the executor to run them.
- **Modular tool system:** Uses a tool registry to make engineering capabilities available to the agent.
- **GitHub REST API integration:** Retrieves live metadata for public repositories.
- **Repository exploration:** Lists repository files and directories using GitHub's Git Trees API.
- **Project context management:** Registers project metadata and resolves projects by their IDs.
- **Asynchronous execution:** Uses Python's asynchronous programming features and HTTPX for API requests.

## Architecture

DevPilot Agent separates the reasoning layer from the execution and integration layers.

```text
                        User Goal
                            |
                            v
                       AgentRunner
                            |
                            v
                        Understander
                       (Groq LLM)
                            |
                            v
                          Planner
                    (Deterministic)
                            |
                            v
                       PolicyEngine
                            |
                            v
                         Executor
                            |
                            v
                       ToolRegistry
                            |
                            v
                    ProjectContextTool
                            |
                  +---------+----------+
                  |                    |
                  v                    v
             ProjectContext       GitHubClient
                  |                    |
                  v                    v
          ProjectRepository       GitHub REST API
```

### Core components

| Component | Responsibility |
|---|---|
| `AgentRunner` | Coordinates the agent lifecycle and records messages, state, and execution results. |
| `Understander` | Interprets the user's request using an LLM. |
| `Planner` | Generates a structured plan for supported engineering intents. |
| `PolicyEngine` | Evaluates plans against execution policies. |
| `Executor` | Resolves registered tools and executes planned steps. |
| `ToolRegistry` | Stores and retrieves available tool instances. |
| `ProjectContext` | Resolves registered projects. |
| `ProjectRepository` | Stores projects in memory. |
| `ProjectService` | Validates and registers GitHub project metadata. |
| `ProjectContextTool` | Combines local project metadata with live GitHub repository information and file listings. |
| `GitHubClient` | Communicates with the GitHub REST API. |
| `GroqClient` | Implements the provider-independent LLM client interface using Groq. |
| `bootstrap.py` | Constructs components and injects their dependencies. |

## Technology Stack

- **Language:** Python 3.11+
- **Package and environment management:** uv
- **LLM provider:** Groq
- **Data validation:** Pydantic
- **HTTP requests:** HTTPX
- **Configuration:** python-dotenv
- **Testing:** pytest, pytest-asyncio
- **External integration:** GitHub REST API

## Getting Started

### Prerequisites

Install Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

You will also need a Groq API key to run the LLM-powered agent.

### 1. Clone the repository

```bash
git clone https://github.com/abhi2005-bit/policy-agent.git
cd policy-agent
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

Replace the placeholder with your own key. Never commit `.env` or expose API keys in source code, prompts, logs, or public repositories.

Ensure `.env` is included in `.gitignore`.

### 4. Run DevPilot Agent

```bash
uv run python -m app.main
```

The application prompts you to register a project using its name, GitHub owner, repository name, and branch. You can then enter a natural-language engineering request.

For example:

```text
Project name: DevPilot Agent
GitHub owner: abhi2005-bit
Repository name: policy-agent
Branch: main

What should DevPilot investigate?
Inspect this project's metadata and list its files.
```

The agent interprets the request, generates a plan, evaluates it against policy, executes the registered tool, and displays the resulting tool data.

## GitHub Integration

DevPilot uses the GitHub REST API to retrieve repository information.

Currently implemented capabilities include:

- Fetching repository metadata, including its full name, description, visibility, URL, default branch, and star count.
- Retrieving a recursive repository tree containing file and directory paths.
- Returning GitHub responses through structured tool results.

Public repositories can be read without authentication, subject to GitHub's API rate limits. Authentication for private repositories is not yet implemented.

Repository registration currently stores metadata in an in-memory repository. GitHub metadata and file listings are fetched from the remote API when the tool executes.

### Current limitations

- Project registrations are lost when the application restarts.
- GitHub OAuth and private repository authentication are not implemented.
- The agent can list repository paths but does not yet perform
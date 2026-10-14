from __future__ import annotations

from app.agent.analyzer import Analyzer
from app.agent.planner import Planner
from app.agent.understander import Understander
from app.core.executor import Executor
from app.core.policy import PolicyEngine
from app.core.project_context import ProjectContext
from app.core.runner import AgentRunner
from app.integrations.github_client import GitHubClient
from app.llm.groq_client import GroqClient
from app.repositories.project_repository import ProjectRepository
from app.tools.engineering import ProjectContextTool
from app.tools.investigation import (
    CIInvestigationTool,
    OpenIssueSearchTool,
    RepositoryHealthTool,
)
from app.tools.repository_file import ReadRepositoryFileTool
from app.tools.registry import ToolRegistry


def create_agent_runner(
    project_repository: ProjectRepository,
) -> AgentRunner:
    """
    Assemble and return a configured DevPilot agent.
    """

    # 1. Create shared project context.
    project_context = ProjectContext(project_repository)

    # 2. Create GitHub integration.
    github_client = GitHubClient()

    # 3. Create and populate the tool registry.
    tool_registry = ToolRegistry()

    project_context_tool = ProjectContextTool(
        project_context=project_context,
        github_client=github_client,
    )
    tool_registry.register(project_context_tool)

    for tool in (
        RepositoryHealthTool(project_context, github_client),
        OpenIssueSearchTool(project_context, github_client),
        CIInvestigationTool(project_context, github_client),
    ):
        tool_registry.register(tool)

    read_file_tool = ReadRepositoryFileTool(
        project_context=project_context,
        github_client=github_client,
    )
    tool_registry.register(read_file_tool)

    # 4. Create one LLM client and inject it into reasoning components.
    llm_client = GroqClient()

    understander = Understander(llm_client)
    analyzer = Analyzer(llm_client)

    # 5. Configure planning, policy, and execution.
    planner = Planner(tool_registry)
    policy_engine = PolicyEngine()
    executor = Executor(tool_registry)

    # 6. Assemble the agent.
    return AgentRunner(
        understander=understander,
        planner=planner,
        policy_engine=policy_engine,
        executor=executor,
        project_context=project_context,
        analyzer=analyzer,
    )

from __future__ import annotations

from app.agent.planner import Planner
from app.agent.understander import Understander
from app.core.executor import Executor
from app.core.policy import PolicyEngine
from app.core.project_context import ProjectContext
from app.core.runner import AgentRunner
from app.llm.groq_client import GroqClient
from app.repositories.project_repository import ProjectRepository
from app.tools.engineering import ProjectContextTool
from app.tools.registry import ToolRegistry


def create_agent_runner(
    project_repository: ProjectRepository,
) -> AgentRunner:
    """
    Assemble and return a configured DevPilot AgentRunner.
    """

    # Create one shared project context.
    project_context = ProjectContext(project_repository)

    # Register the project context tool.
    tool_registry = ToolRegistry()
    project_context_tool = ProjectContextTool(project_context)
    tool_registry.register(project_context_tool)

    # Configure the LLM and Understander.
    llm_client = GroqClient()
    understander = Understander(llm_client)

    # Configure planning, policy, and execution.
    planner = Planner(tool_registry)
    policy_engine = PolicyEngine()
    executor = Executor(tool_registry)

    # Assemble the agent.
    return AgentRunner(
        understander=understander,
        planner=planner,
        policy_engine=policy_engine,
        executor=executor,
        project_context=project_context,
    )
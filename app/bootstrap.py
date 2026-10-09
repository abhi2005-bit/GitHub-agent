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

def create_agent_runner()-> AgentRunner:
    """
    Create an AgentRunner instance with all required dependencies.
    """

    # Initialize the project repository and context.
    project_repository = ProjectRepository()
    project_context = ProjectContext(project_repository)

    # Initialize the tool registry and register tools.
    tool_registry = ToolRegistry()
    tool_registry.register(ProjectContextTool(project_context))

    # Initialize the LLM client, understander, planner, policy engine, and executor.
    llm_client = GroqClient()
    understander = Understander(llm_client)
    planner = Planner(tool_registry)
    policy_engine = PolicyEngine()
    executor = Executor(tool_registry)

    # Create and return the AgentRunner instance.
    return AgentRunner(
        understander=understander,
        planner=planner,
        policy_engine=policy_engine,
        executor=executor,
        project_context=project_context,
    )
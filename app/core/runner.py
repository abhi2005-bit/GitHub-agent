from __future__ import annotations

import json
from datetime import datetime, timezone

from app.agent.analyzer import Analyzer
from app.agent.planner import Planner
from app.agent.understander import Understander
from app.core.executor import Executor
from app.core.policy import PolicyEngine
from app.core.project_context import ProjectContext
from app.models.agent import AgentMessage, AgentRun, AgentState


class AgentRunner:
    """
    Coordinates the lifecycle of an agent run.
    """

    def __init__(
        self,
        understander: Understander,
        planner: Planner,
        policy_engine: PolicyEngine,
        executor: Executor,
        project_context: ProjectContext,
        analyzer: Analyzer,
    ) -> None:
        self.understander = understander
        self.planner = planner
        self.policy_engine = policy_engine
        self.executor = executor
        self.project_context = project_context
        self.analyzer = analyzer

    async def run(
        self,
        goal: str,
        project_id: int | None = None,
    ) -> AgentRun:
        run = AgentRun(
            goal=goal,
            project_id=project_id,
        )

        try:
            # 1. Resolve the selected project.
            project = None

            if project_id is not None:
                project = self.project_context.get_project(project_id)

            self._update_state(run, AgentState.THINKING)

            run.messages.append(
                AgentMessage(role="user", content=goal)
            )
            run.messages.append(
                AgentMessage(
                    role="system",
                    content="Agent run started.",
                )
            )

            # 2. Understand the user's goal.
            understanding = self.understander.understand(run.goal)

            run.messages.append(
                AgentMessage(
                    role="agent",
                    content=(
                        f"Goal understood as: "
                        f"{understanding.intent.value}."
                    ),
                )
            )

            # 3. Generate an execution plan.
            plan = self.planner.create_plan(
                understanding=understanding,
                project=project,
            )

            run.messages.append(
                AgentMessage(
                    role="agent",
                    content=f"Plan created with {len(plan.steps)} step(s).",
                )
            )

            # 4. Check policy before executing any tools.
            policy_decision = self.policy_engine.evaluate(plan)

            if not policy_decision.allowed:
                self._update_state(run, AgentState.FAILED)
                run.error = policy_decision.reason

                run.messages.append(
                    AgentMessage(
                        role="system",
                        content=(
                            "Agent execution blocked by policy: "
                            f"{policy_decision.reason}"
                        ),
                    )
                )

                return run

            # 5. Execute the plan.
            self._update_state(run, AgentState.ACTING)

            result = await self.executor.execute(plan)
            run.iterations += 1

            # 6. Record tool results in the agent conversation.
            for step_result in result.step_results:
                if step_result.tool_result is None:
                    continue

                tool_result_data = {
                    "success": step_result.tool_result.success,
                    "data": step_result.tool_result.data,
                    "error": step_result.tool_result.error,
                }

                formatted_result = json.dumps(
                    tool_result_data,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

                run.messages.append(
                    AgentMessage(
                        role="agent",
                        content=(
                            f"Tool result for step {step_result.step_id}:\n"
                            f"{formatted_result}"
                        ),
                    )
                )

            # 7. Analyze the execution evidence.
            report = self.analyzer.analyze(
                goal=run.goal,
                execution_result=result,
            )

            run.messages.append(
                AgentMessage(
                    role="agent",
                    content=f"Engineering Analysis Report:\n\n{report}",
                )
            )

            # 8. Set the final state based on execution outcome.
            if result.success:
                self._update_state(run, AgentState.COMPLETED)

                run.messages.append(
                    AgentMessage(
                        role="system",
                        content=(
                            "Agent execution and analysis completed "
                            "successfully."
                        ),
                    )
                )

            else:
                self._update_state(run, AgentState.FAILED)
                run.error = result.error

                run.messages.append(
                    AgentMessage(
                        role="system",
                        content=f"Agent execution failed: {result.error}",
                    )
                )

        except Exception as exc:
            self._update_state(run, AgentState.FAILED)
            run.error = str(exc)

            run.messages.append(
                AgentMessage(
                    role="system",
                    content=f"Agent run failed: {exc}",
                )
            )

        return run

    @staticmethod
    def _update_state(
        run: AgentRun,
        state: AgentState,
    ) -> None:
        run.state = state
        run.updated_at = datetime.now(timezone.utc)